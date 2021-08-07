""" JobDB class and associated functions and methods """
#pylint: disable=too-many-lines
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

import json
import os
import re
import socket
import sqlite3
import sys
import time
import warnings

from six import iteritems, string_types

import prisms_jobs
from prisms_jobs import config, misc

def trunc(data, maxlen):
    return (data[:maxlen-2] + '..') if len(data) > maxlen else data

class JobDBError(Exception):
    """ Custom error class for JobDB"""
    def __init__(self, msg):
        self.msg = msg
        super(JobDBError, self).__init__()

    def __str__(self):
        return self.msg


class EligibilityError(Exception):
    """ Custom error class for JobDB """  #pylint: disable=fixme
    def __init__(self, jobid, msg):
        self.jobid = jobid
        self.msg = msg
        super(EligibilityError, self).__init__()

    def __str__(self):
        return self.jobid + ": " + self.msg


# columns in database (see job_status_dict()):
# username, hostname, jobid, jobname, rundir, jobstatus, auto, taskstatus,
# continuation_jobid, qsubstr, qstatstr, nodes, proc, walltime, starttime,
# completiontime, elapsedtime

# allowed values (not checked at this time):
# taskstatus = ["Incomplete","Complete","Continued","Check","Error:.*","Aborted"]
# jobstatus = ["C","Q","R","E","W","H","M"]
# auto=[1,0]

def job_status_dict(username=misc.getlogin(),        #pylint: disable=too-many-arguments, too-many-locals
                    hostname=socket.gethostname(),
                    jobid="-",
                    jobname="-",
                    rundir="-",
                    jobstatus="-",
                    auto=0,
                    taskstatus="Incomplete",
                    continuation_jobid="-",
                    qsubstr="-",
                    qstatstr="-",
                    nodes=None,
                    procs=None,
                    walltime=None,
                    elapsedtime=None,
                    starttime=None,
                    completiontime=None):
    """Return a dict() with job_status fields.

       This is used to add records to the JobDB database through JobDB().add().
    """

    creationtime = int(time.time())
    modifytime = creationtime

    status = dict()
    status["username"] = username
    status["hostname"] = hostname
    status["jobid"] = jobid
    status["jobname"] = jobname
    status["rundir"] = rundir
    status["jobstatus"] = jobstatus
    status["auto"] = int(bool(auto))
    status["taskstatus"] = taskstatus
    status["continuation_jobid"] = continuation_jobid
    status["qsubstr"] = qsubstr
    status["qstatstr"] = qstatstr

    # integer:
    status["nodes"] = nodes
    status["procs"] = procs

    # integer s:
    status["walltime"] = walltime
    status["elapsedtime"] = elapsedtime

    # integer s since the epoch:
    status["creationtime"] = creationtime
    status["starttime"] = starttime
    status["completiontime"] = completiontime
    status["modifytime"] = modifytime

    return status


#def selector_rules():
#    rules = dict()
#    rules["username"] = lambda r: r["username"]
#    rules["hostname"] = lambda r: r["hostname"]
#    rules["jobid"] = lambda r: r["jobid"]
#    rules["rundir"] = lambda r: r["rundir"]
#    rules["jobstatus"] = lambda r: r["jobstatus"]
#    rules["auto"] = lambda r: r["auto"]
#    rules["taskstatus"] = lambda r: r["taskstatus"]
#    rules["continuation_jobid"] = lambda r: r["continuation_jobid"]
#    rules["qsubstr"] = lambda r: r["continuation_jobid"]
#    ...
#    return rules


def job_status_type_dict():
    """This specifies the SQL type for each field.
       It is used to create the JobDB SQL table.
    """
    status = job_status_dict()
    for k in status:
        status[k] = "text"
    status["auto"] = "integer"

    status["nodes"] = "integer"
    status["procs"] = "integer"

    status["walltime"] = "integer"
    status["elapsedtime"] = "integer"

    status["creationtime"] = "integer"
    status["starttime"] = "integer"
    status["completiontime"] = "integer"
    status["modifytime"] = "integer"

    return status


def sql_create_str():
    """Returns a string for SQL CREATE TABLE"""
    status_type = job_status_type_dict()
    s = "("    #pylint: disable=invalid-name
    for k in status_type:
        s += k + " " + status_type[k] + ", "  #pylint: disable=invalid-name
    return s[:-2] + ")"


def sql_insert_str(job_status):
    """ Accepts job_status dict, Returns strings and tuple used for SQL INSERT INTO."""
    job_status["auto"] = int(bool(job_status["auto"]))
    colstr = "("
    questionstr = "("
    val = []
    for k in job_status:
        colstr = colstr + k + ", "
        questionstr = questionstr + "?, "
        val.append(job_status[k])
    colstr = colstr[:-2] + ")"
    questionstr = questionstr[:-2] + ")"
    return colstr, questionstr, tuple(val)


class CompatibilityRow(object):
    """Python2/3 compatibility wrapper of sqlite3.Row"""
    def __init__(self, row):
        self._row = row

    def __getitem__(self, key):
        if sys.version_info < (3,) and isinstance(key, unicode):
            key = key.encode('utf-8')
        return self._row[key]

    def keys(self):
        return self._row.keys()

    def __str__(self):
        return str(self._row)

def sql_iter(curs, arraysize=1000):
    """ Iterate over the results of a SELECT statement """
    while True:
        records = curs.fetchmany(arraysize)
        if not records:
            break
        else:
            for r in records:       #pylint: disable=invalid-name
                yield CompatibilityRow(r)


def regexp(pattern, string):
    """ Regexp to bool wrapper"""
    return re.match(pattern, string) is not None

class JobDB(object):    #pylint: disable=too-many-instance-attributes, too-many-public-methods
    """A primsms_jobs Job Database object

    Usually this is called without arguments (prisms_jobs.JobDB()) to open or
    create a database in the default location.

    Args:
        dbpath (str, optional): Path to JobDB sqlite database. By default,
            uses ``prisms_jobs.config.dbpath()``.

    """

    def __init__(self, dbpath=None):

        self.conn = None
        self.curs = None
        self.connect(dbpath)

        # list of dict() from misc.job_status for jobs not tracked in database:
        # refreshed upon update()
        self.untracked = []


    def connect(self, dbpath=None):    #pylint: disable=too-many-branches, too-many-statements
        """Open a connection to the jobs database.

        Args:
            dbpath (str, optional): path to a JobDB database file. By default,
            uses ``prisms_jobs.config.dbpath()``.

        """

        if dbpath is None:
            dbpath = config.dbpath()

        if not os.path.isfile(dbpath):
            print("Creating Database:", dbpath)
            self.conn = sqlite3.connect(dbpath)
            self.conn.row_factory = sqlite3.Row
            self.conn.create_function("REGEXP", 2, regexp)
            self.curs = self.conn.cursor()
            self.curs.execute("CREATE TABLE jobs " + sql_create_str())
            self.conn.commit()
        else:
            self.conn = sqlite3.connect(dbpath)
            self.conn.row_factory = sqlite3.Row
            self.conn.create_function("REGEXP", 2, regexp)
            self.curs = self.conn.cursor()

            # check columns
            status_type = job_status_type_dict()
            self.curs.execute("SELECT * from jobs")
            cols = [desc[0] for desc in self.curs.description]

            for c in status_type:
                if c not in cols:
                    warnings.warn("Column '" + c + "' not in prisms_jobs jobs table.")


    def close(self):
        """Close the connection to the jobs database."""

        self.conn.close()


    def add(self, job_status):
        """Add a record to the jobs database.

        Args:
            job_status (dict):
                Accepts a dictionary of data comprising the record.
                Create ``job_status`` using prisms_jobs.jobdb.job_status_dict().

        """
        (colstr, questionstr, valtuple) = sql_insert_str(job_status)
        insertstr = "INSERT INTO jobs {0} VALUES {1}".format(colstr, questionstr)
        self.curs.execute(insertstr, valtuple)
        self.conn.commit()


    def update(self):
        """Update records using qstat.

        Any jobs found using qstat that are not in the jobs database are saved
        in 'self.untracked'.
        """

        # update jobstatus
        # * this method can be configured/customized via set_update_selection_method
        config.update_selection_method()(self.curs)

        # newstatus will contain the updated info
        newstatus = dict()

        # any jobs that we don't find with qstat should be marked as 'C'
        for f in sql_iter(self.curs):   #pylint: disable=invalid-name
            newstatus[f["jobid"]] = "C"

        # get job_status dict for all jobs found with qstat
        active_status = config.software().job_status()

        # reset untracked
        self.untracked = []

        # collect job status
        for k in active_status:
            if k in newstatus:
                newstatus[k] = active_status[k]
            else:
                self.curs.execute("SELECT jobid FROM jobs WHERE jobid=?", (k,))
                if self.curs.fetchone() is None:
                    self.untracked.append(active_status[k])

        # update database with latest job status
        for key, jobstatus in iteritems(newstatus):
            if jobstatus == "C":
                self.curs.execute(
                    "UPDATE jobs SET jobstatus=?, elapsedtime=?, modifytime=? WHERE jobid=?",
                    ("C", None, int(time.time()), key))
            #elif jobstatus["qstatstr"] is None:
            #    self.curs.execute(
            #    "UPDATE jobs SET jobstatus=?, elapsedtime=?, modifytime=? WHERE jobid=?",
            #    (jobstatus["jobstatus"], jobstatus["elapsedtime"], int(time.time()), key))
            else:
                self.curs.execute(
                    "UPDATE jobs SET jobstatus=?, elapsedtime=?, starttime=?,\
                     completiontime=?, qstatstr=?, modifytime=? WHERE jobid=?",
                    (
                        jobstatus["jobstatus"], jobstatus["elapsedtime"],
                        jobstatus["starttime"], jobstatus["completiontime"],
                        jobstatus["qstatstr"], int(time.time()), key))

        self.conn.commit()

        # update taskstatus for non-auto jobs
        self.curs.execute(
            "UPDATE jobs SET taskstatus='Check', modifytime=? \
            WHERE jobstatus='C' AND taskstatus='Incomplete' AND auto=0",
            (int(time.time()),))
        self.conn.commit()


    def select_job(self, jobid):
        """Return record (sqlite3.Row object) for one job with given jobid."""
        if not isinstance(jobid, string_types):
            print("Error in prisms_jobs.JobDB.select_job(). type(id):", type(jobid), "expected str.")
            sys.exit()

        self.curs.execute("SELECT * FROM jobs WHERE jobid=?", (jobid,))
        r = self.curs.fetchall()    #pylint: disable=invalid-name
        if len(r) == 0:
            raise JobDBError("Error in prisms_jobs.JobDB.select_job(). jobid: '"
                             + jobid + "' not found in jobs database.")
        elif len(r) > 1:
            raise JobDBError("Error in prisms_jobs.JobDB.select_job(). "
                             + str(len(r)) + " records with jobid: '"
                             + jobid + "' found.")
        return CompatibilityRow(r[0])


    def select_series(self, jobid):
        """Return records (sqlite3.Row objects) for a series of auto jobs"""
        r = self.select_job(jobid)  #pylint: disable=invalid-name
        series = [r]
        parent = self.select_parent(jobid)
        while parent is not None:
            series.insert(0, parent)
            parent = self.select_parent(parent["jobid"])
        child = self.select_child(jobid)
        while child is not None:
            series.append(child)
            child = self.select_child(child["jobid"])
        return series


    def select_parent(self, jobid):
        """Return record for the parent of a job

           The parent is the job with continuation_jobid = given jobid
        """
        if not isinstance(jobid, string_types):
            print("Error in prisms_jobs.JobDB.select_parent(). type(id):", type(jobid), "expected str.")
            sys.exit()

        self.curs.execute("SELECT * FROM jobs WHERE continuation_jobid=?", (jobid,))
        r = self.curs.fetchall()    #pylint: disable=invalid-name
        if len(r) == 0:
            return None
        elif len(r) > 1:
            print ("Error in prisms_jobs.JobDB.select_parent().",
                   len(r),
                   " records with continuation_jobid:",
                   jobid, " found.")
            sys.exit()
        return CompatibilityRow(r[0])


    def select_child(self, jobid):
        """Return record for the child of a job

           The child is the job whose jobid = continuation_jobid of job with given jobid
        """
        r = self.select_job(jobid)  #pylint: disable=invalid-name

        if r["continuation_jobid"] == "-":
            return None

        self.curs.execute("SELECT * FROM jobs WHERE jobid=?", (r["continuation_jobid"],))
        r = self.curs.fetchall()    #pylint: disable=invalid-name
        if len(r) == 0:
            print ("Error in prisms_jobs.JobDB.select_child(). jobid:",
                   jobid, " child:", r["continuation_jobid"],
                   "not found.")
            sys.exit()
        elif len(r) > 1:
            print ("Error in prisms_jobs.JobDB.select_child().",
                   len(r), " records with child jobid:",
                   r["continuation_jobid"], " found.")
            sys.exit()
        return CompatibilityRow(r[0])



    def select_all_id(self):
        """Return a list with all jobids."""
        job = []
        self.curs.execute("SELECT jobid FROM jobs")
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            job.append(r["jobid"])
        return job


    def select_all_active_id(self):
        """Return a list with all active jobids.

           "Active" jobs are those with taskstatus='Incomplete' or 'Check'
        """
        active_job = []
        self.curs.execute("SELECT jobid FROM jobs WHERE taskstatus!='Complete'\
                           AND taskstatus!='Aborted' AND taskstatus!='Continued'")
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            active_job.append(r["jobid"])
        return active_job


    def select_range_id(self, min_jobid, max_jobid):
        """ Return a list of all jobids which are between (and including)
                min_jobid and max_jobid. """
        job = []
        self.curs.execute("SELECT jobid FROM jobs")
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            if int(r["jobid"]) >= int(min_jobid) and int(r["jobid"]) <= int(max_jobid):
                job.append(r["jobid"])
        return job


    def select_recent_id(self, recent_time):
        """ Return a list of all jobids which were modified in the last 'recent_time' """
        mintime = int(time.time() - misc.seconds(recent_time))
        recent_job = []
        self.curs.execute("SELECT jobid FROM jobs WHERE modifytime>=?", (mintime, ))
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            recent_job.append(r["jobid"])
        return recent_job


    def select_regex_id(self, key, regex):
        """ Return a list of all jobids in which the column 'key' matches the
                regular expression 'regex' """
        job = []
        if key in job_status_dict():
            self.curs.execute("SELECT jobid FROM jobs WHERE " + key + " REGEXP ?", (regex, ))
            for r in sql_iter(self.curs):   #pylint: disable=invalid-name
                job.append(r["jobid"])
        else:
            raise JobDBError(key + " not a valid key")

        return job


    def select_series_id(self, jobid):
        """Return a list with all jobids for a series of auto jobs."""
        job = [jobid]
        r = self.select_job(jobid)  #pylint: disable=invalid-name, unused-variable
        parent = self.select_parent(jobid)
        while parent is not None:
            job.insert(0, parent["jobid"])
            parent = self.select_parent(parent["jobid"])
        child = self.select_child(jobid)
        while child is not None:
            job.append(child["jobid"])
            child = self.select_child(child["jobid"])
        return job


    def select_all_series_id(self):
        """Return a list of lists of jobids (one list for each series)."""
        all_series = []
        self.curs.execute("SELECT * FROM jobs")
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            if r["continuation_jobid"] == "-":
                all_series.append(self.select_series_id(r["jobid"]))
        return all_series


    def select_active_series_id(self):
        """Return a list of lists of jobids (one list for each active series).

           "Active" series of auto jobs are those with one job with
                taskstatus='Incomplete' or 'Check'
        """
        active_series = []
        self.curs.execute("SELECT jobid, continuation_jobid FROM jobs WHERE\
                           taskstatus!='Complete' AND taskstatus!='Aborted'\
                           AND taskstatus!='Continued'")
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            if r["continuation_jobid"] == "-":
                active_series.append(self.select_series_id(r["jobid"]))
        return active_series


    def select_range_series_id(self, min_jobid, max_jobid):
        """ Return a list of lists of all jobids for series (one list for each series)
            which have the last job between (and including) min_jobid and max_jobid.
        """
        job = []
        self.curs.execute("SELECT jobid, continuation_jobid FROM jobs")
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            if int(r["jobid"]) >= int(min_jobid) and int(r["jobid"]) <= int(max_jobid):
                if r["continuation_jobid"] == "-":
                    job.append(self.select_series_id(r["jobid"]))
        return job


    def select_recent_series_id(self, recent_time):
        """ Return a list of lists of jobids (one for each series) which were
                modified in the last 'recent_time' """
        mintime = int(time.time() - misc.seconds(recent_time))
        recent_job = []
        self.curs.execute("SELECT jobid FROM jobs WHERE modifytime>=?", (mintime, ))
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            if r["continuation_jobid"] == "-":
                recent_job.append(self.select_series_id(r["jobid"]))
        return recent_job


    def select_regex_series_id(self, key, regex):
        """ Return a list of lists of jobids (one for each series) in which the column
            'key' matches the regular expression 'regex'
        """

        job = []
        if  key in job_status_dict():
            self.curs.execute("SELECT jobid FROM jobs WHERE " + key + " REGEXP ?", (regex))
            for r in sql_iter(self.curs):   #pylint: disable=invalid-name
                if r["continuation_jobid"] == "-":
                    job.append(self.select_series_id(r["jobid"]))
        else:
            raise JobDBError(key + " not a valid key")

        return job



    def eligible_to_continue(self, job):    #pylint: disable=no-self-use
        """ Return True if job is eligible to be continued, else return False

        Job must have jobstatus="C" and taskstatus="Incomplete" and auto=1,
            or else the job can not be continued.

        Args:
            job: a sqlite3.Row, as obtained by self.select_job()

        Returns:
            (0, jobid, None) if eligible
            (1, jobid, msg) if not eligible
        """
        if job["jobstatus"] != "C":
            return (False, job["jobid"], "Job not eligible to continue. jobstatus = "
                    + job["jobstatus"])

        if job["taskstatus"] != "Incomplete":
            return (False, job["jobid"], "Job not eligible to continue. taskstatus = "
                    + job["taskstatus"])

        if job["auto"] != 1:
            return (False, job["jobid"], "Job not eligible to continue. auto = "
                    + str(bool(job["auto"])))

        return (True, job["jobid"], None)


    def continue_job(self, jobid=None, job=None):
        """ Resubmit one job with given jobid.

        Args:
            jobid: jobid of the job to continue
            job: (sqlite3.Row) If this is given, jobid is not necessary and is ignored if given

        Raises:
            EligibilityError if job not eligible to be continued
        """

        if job is None:
            job = self.select_job(jobid)

        eligible, id, msg = self.eligible_to_continue(job)  #pylint: disable=invalid-name, redefined-builtin
        if not eligible:
            raise EligibilityError(id, msg)

        wd = os.getcwd()    #pylint: disable=invalid-name
        os.chdir(job["rundir"])

        new_jobid = config.software().submit(substr=job["qsubstr"])

        self.curs.execute("UPDATE jobs SET taskstatus='Continued', modifytime=?,\
                           continuation_jobid=? WHERE jobid=?",
                          (int(time.time()), new_jobid, job["jobid"]))
        status = job_status_dict(jobid=new_jobid, jobname=job["jobname"], rundir=os.getcwd(),
                                 jobstatus="?", auto=job["auto"], qsubstr=job["qsubstr"],
                                 nodes=job["nodes"], procs=job["procs"], walltime=job["walltime"])
        self.add(status)

        os.chdir(wd)


    def continue_all(self):
        """Resubmit all jobs eligible to continue"""
        self.curs.execute("SELECT jobid FROM jobs WHERE auto=1 AND\
                           taskstatus='Incomplete' AND jobstatus='C'")
        for r in sql_iter(self.curs):   #pylint: disable=invalid-name
            self.continue_job(r["jobid"])


    def eligible_to_abort(self, job):   #pylint: disable=no-self-use
        """ Check if job is eligible to be aborted

        Jobs are eligible to be aborted if:
            jobstatus != "C"
            or
            (jobstatus == "C"
            and
            (taskstatus == "Incomplete" or taskstatus == "Check"))

        Args:
            job: a sqlite3.Row, as obtained by self.select_job()

        Returns:
            (0, jobid, None) if eligible
            (1, jobid, msg) if not eligible
        """
        if job["jobstatus"] != "C":
            return (True, job["jobid"], None)
        elif job["taskstatus"] == "Incomplete" or job["taskstatus"] == "Check":
            return (True, job["jobid"], None)
        return (False, job["jobid"], "Job not eligible to be aborted. jobstatus = "
                + job["jobstatus"] + " and taskstatus = " + job["taskstatus"])


    def abort_job(self, jobid=None, job=None):
        """ Delete a job and mark job taskstatus as Aborted

        Args:
            jobid: jobid of the job to continue
            job: (sqlite3.Row) If this is given, jobid is not necessary and is ignored if given

        Raises:
            EligibilityError if job not eligible to be aborted
        """

        if job is None:
            job = self.select_job(jobid)

        eligible, id, msg = self.eligible_to_abort(job) #pylint: disable=invalid-name, redefined-builtin
        if not eligible:
            raise EligibilityError(id, msg)

        config.software().delete(job["jobid"])
        self.curs.execute("UPDATE jobs SET taskstatus='Aborted', modifytime=?\
                           WHERE jobid=?", (int(time.time()), job["jobid"]))
        self.conn.commit()


    def eligible_to_delete(self, job):  #pylint: disable=no-self-use
        """ Check if job is eligible to be aborted

        All jobs are eligible to be deleted

        Args:
            job: a sqlite3.Row, as obtained by self.select_job()

        Returns:
            (0, jobid, None) if eligible
            (1, jobid, msg) if not eligible
        """
        return (True, job["jobid"], None)


    def delete_job(self, jobid=None, job=None, series=False):
        """ Delete job if running, and delete job from the database.

        Args:
            jobid (str): jobid of the job to continue
            job (sqlite3.Row): If this is given, jobid is not necessary and is ignored if given
            series (bool): If 'series'=True, deletes entire job series
        """
        if job is None:
            job = self.select_job(jobid)

        if series:
            jobseries = self.select_series_id(job["jobid"])
        else:
            jobseries = [job["jobid"]]

        for j in jobseries:
            config.software().delete(j)
            self.curs.execute("DELETE from jobs WHERE jobid=?", (j, ))
        self.conn.commit()


    def eligible_to_error(self, job):   #pylint: disable=no-self-use
        """ Check if job is eligible to be marked as error

        All jobs are eligible to be marked as error. (Should this exclude "Continued" jobs?)

        Args:
            job: a sqlite3.Row, as obtained by self.select_job()

        Returns:
            (0, jobid, None) if eligible
            (1, jobid, msg) if not eligible
        """
        return (True, job["jobid"], None)


    def error_job(self, message, jobid=None, job=None):
        """ Mark job taskstatus as 'Error: message'

        Any job can be marked as error.

        Args:
            jobid: jobid of the job to mark as error
            job: (sqlite3.Row) If this is given, jobid is not necessary and is ignored if given

        """
        message = "Error: " + message
        if job is None:
            job = self.select_job(jobid)
        self.curs.execute("UPDATE jobs SET taskstatus=?, modifytime=? WHERE\
                           jobid=?", (message, int(time.time()), job["jobid"]))
        self.conn.commit()


    def eligible_to_reset(self, job):   #pylint: disable=no-self-use
        """ Check if job is eligible to be reset

        Jobs are eligible to be reset if they are 'auto' jobs, and
            taskstatus == "Error:.*" or "Aborted"

        Args:
            job: a sqlite3.Row, as obtained by self.select_job()

        Returns:
            (0, jobid, None) if eligible
            (1, jobid, msg) if not eligible
        """
        if job["auto"] != 1:
            return (False, job["jobid"], "Job not eligible to be reset. auto = " + job["auto"])
        if job["taskstatus"] != "Aborted" and not re.match("Error:.*", job["taskstatus"]):
            return (False, job["jobid"], "Job not eligible to be reset. taskstatus = "
                    + job["taskstatus"])
        return (True, job["jobid"], None)


    def reset_job(self, jobid=None, job=None):
        """ Mark job taskstatus as 'Incomplete'

        Jobs are eligible to be reset if they are 'auto' jobs, and
            taskstatus == "Error:.*" or "Aborted"

        Args:
            jobid: jobid of the job to mark as error
            job: (sqlite3.Row) If this is given, jobid is not necessary and is ignored if given

        Raises:
            prisms_jobs.EligibilityError: If not job not eligible to be marked 'Complete'
        """
        if job is None:
            job = self.select_job(jobid)

        eligible, id, msg = self.eligible_to_reset(job) #pylint: disable=invalid-name, redefined-builtin
        if not eligible:
            raise EligibilityError(id, msg)

        self.curs.execute("UPDATE jobs SET taskstatus=?, modifytime=? WHERE jobid=?",
                          ("Incomplete", int(time.time()), job["jobid"]))
        self.conn.commit()


    def eligible_to_complete(self, job):    #pylint: disable=no-self-use
        """ Check if job is eligible to be completed

        Jobs are eligible to be completed if:
            taskstatus != "Complete" and taskstatus != "Continued"

        Args:
            job: a sqlite3.Row, as obtained by self.select_job()

        Returns:
            (0, jobid, None) if eligible
            (1, jobid, msg) if not eligible
        """
        if job["taskstatus"] == "Incomplete" or job["taskstatus"] == "Check":
            return (True, job["jobid"], None)
        return (False, job["jobid"], "Job not eligible to be completed. taskstatus = "
                + job["taskstatus"])


    def complete_job(self, jobid=None, job=None):
        """Mark job taskstatus as 'Complete'

        Args:
            jobid (str): ID of job
            job (sqlite3.Row object): Job record from database

        Raises:
            prisms_jobs.EligibilityError: If not job not eligible to be marked 'Complete'
        """

        if job is None:
            job = self.select_job(jobid)

        eligible, id, msg = self.eligible_to_complete(job)  #pylint: disable=invalid-name, redefined-builtin
        if not eligible:
            raise EligibilityError(id, msg)

        self.curs.execute("UPDATE jobs SET taskstatus='Complete', modifytime=?, elapsedtime=?\
                           WHERE jobid=?", (int(time.time()), None, job["jobid"]))
        self.conn.commit()




    def print_header(self): #pylint: disable=no-self-use
        """Print header rows for record summary"""
        print ("{0:<12} {1:<24} {2:^5} {3:^5} {4:>12} {5:^1} {6:>12} {7:<24} {8:^1} {9:<12}"
               .format("JobID", "JobName", "Nodes", "Procs", "Walltime", "S", "Runtime",
                       "Task", "A", "ContJobID"))
        print ("{0:-^12} {1:-^24} {2:-^5} {3:-^5} {4:->12} {5:-^1} {6:->12} {7:-<24} {8:-^1} {9:-^12}"
               .format("-", "-", "-", "-", "-", "-", "-", "-", "-", "-"))


    def _print_record(self, r):  #pylint: disable=invalid-name, no-self-use
        """Print record summary

        Args:
            r (dict): a dict-like object containing: "jobid", "jobname", "nodes",
                "procs",  "walltime", "jobstatus", "elapsedtime", "taskstatus",
                "auto", and "continuation_jobid"
        """

        d = dict(r) #pylint: disable=invalid-name

        for k in ["walltime", "elapsedtime"]:
            if d[k] is None:
                d[k] = "-"
            elif isinstance(d[k], int):
                d[k] = misc.strftimedelta(d[k])

        print ("{0:<12} {1:<24} {2:^5} {3:^5} {4:>12} {5:^1} {6:>12} {7:<24} {8:^1} {9:<12}"
               .format(d["jobid"], trunc(d["jobname"],24), d["nodes"], d["procs"], d["walltime"],
                       d["jobstatus"], d["elapsedtime"], trunc(d["taskstatus"],24), d["auto"],
                       d["continuation_jobid"]))


    def _print_full_record(self, r): #pylint: disable=invalid-name, no-self-use
        """Print record as list of key-val pairs.

        Args:
            r (dict): a dict-like object
        """
        print("#Record:")
        for key in r.keys():
            if isinstance(r[key], string_types):
                s = "\"" + r[key] + "\""    #pylint: disable=invalid-name
                if re.search("\n", s):
                    s = "\"\"" + s + "\"\"" #pylint: disable=invalid-name
                print(key, "=", s)
            else:
                print(key, "=", r[key])
        print("")


    def print_job(self, jobid=None, job=None, full=False, series=False):
        """Print job with given jobid

        Args:
            jobid (str): ID of job
            job (sqlite3.Row object): Job record from database
            full (bool): If True, print as key:val pair list, If (default) False,
                print single row summary in 'qstat' style.
            series (bool): If True, print records as groups of auto submitting job
                series. If (default) False, print in order found.
        """

        if series:
            if job is not None:
                jobid = job["jobid"]
            series = self.select_series(jobid)
            if full:
                for r in series:    #pylint: disable=invalid-name
                    self._print_full_record(r)
            else:
                for r in series:    #pylint: disable=invalid-name
                    self._print_record(r)
            print("")
        else:
            if job is None:
                job = self.select_job(jobid)

            if full:
                self._print_full_record(job)
            else:
                self._print_record(job)


    def print_selected(self, curs=None, full=False, series=False):
        """Fetch and print jobs selected with SQL SELECT statement using cursor 'curs'.


        Args:
            curs: Fetch selected jobs from sqlite3 cursor 'curs'. If no 'curs'
                given, use self.curs.
            full (bool): If True, print as key:val pair list, If (default) False,
                print single row summary in 'qstat' style.
            series (bool): If True, print records as groups of auto submitting job
                series. If (default) False, print in order found.
        """
        if curs is None:
            curs = self.curs
        if full:
            for r in sql_iter(self.curs):   #pylint: disable=invalid-name
                if series:
                    if r["continuation_jobid"] == "-":
                        self.print_job(r["jobid"], full=full, series=series)
                else:
                    self._print_full_record(r)
        else:
            for r in sql_iter(self.curs):   #pylint: disable=invalid-name
                if series:
                    if r["continuation_jobid"] == "-":
                        self.print_job(r["jobid"], full=full, series=series)
                else:
                    self._print_record(r)


    def print_untracked(self, full=False):
        """Print untracked jobs.

        Untracked jobs are stored in self.untracked after calling JobDB.update().

        Args:
            full (bool): If True, print as key:val pair list, If (default) False,
                print single row summary in 'qstat' style.
        """
        if len(self.untracked) == 0:
            return
        print("Untracked:")
        if not full:
            self.print_header()
        sort = sorted(self.untracked, key=lambda rec: rec["jobid"])
        for r in sort:  #pylint: disable=invalid-name
            tmp = dict(r)

            tmp["continuation_jobid"] = "-"
            tmp["auto"] = 0
            tmp["taskstatus"] = "Untracked"
            if full:
                self._print_full_record(tmp)
            else:
                self._print_record(tmp)


    def print_all(self, full=False, series=False):
        """Print all jobs

        Args:
            full (bool): If True, print as key:val pair list, If (default) False,
                print single row summary in 'qstat' style.
            series (bool): If True, print records as groups of auto submitting job
                series. If (default) False, print in order found.
        """
        print("Tracked:")
        self.curs.execute("SELECT * FROM jobs")
        if not full:
            self.print_header()
        self.print_selected(full=full, series=series)


    def print_active(self, full=False, series=False):
        """Print active jobs

        "Active" jobs are those with taskstatus='Incomplete' or 'Check'

        Args:
            full (bool): If True, print as key:val pair list. If (default) False,
                print single row summary in 'qstat' style.
            series (bool): If True, print records as groups of auto submitting job
                series. If (default) False, print in order found.
        """
        print("Tracked:")
        self.curs.execute("SELECT * FROM jobs WHERE taskstatus!='Complete'\
                           AND taskstatus!='Aborted' AND taskstatus!='Continued'")
        if not full:
            self.print_header()
        self.print_selected(full=full, series=series)

# end class JobDB


def complete_job(jobid=None, dbpath=None,):
    """Mark the job as 'Complete' if possible

    Args:
        dbpath (str): Path to JobDB database.

            If not given, use default database.

        jobid (str): ID of job to mark 'Complete'.

            If not given, uses current job ID determined from the environment.

    Raises:
        JobsError: If job ID could not be determined
    """
    db = JobDB(dbpath)  #pylint: disable=invalid-name

    if jobid is None:
        jobid = config.software().job_id()
        if jobid is None:
            raise prisms_jobs.JobsError(0, "Could not determine jobid")

    job = db.select_job(jobid)  #pylint: disable=unused-variable
    db.complete_job(jobid)
    db.close()


def error_job(message, jobid=None, dbpath=None):
    """Mark the job as 'Error: message' if possible

    Args:
        message (str): Error message to save in JobDB.

        dbpath (str, optional): Path to JobDB database.

            If not given, use default database.

        jobid (str, optional): ID of job to mark 'Error: message'.

            If not given, uses current job ID determined from the environment.

    Raises:
        JobsError: If job ID could not be determined
    """
    db = JobDB(dbpath)  #pylint: disable=invalid-name
    if jobid is None:
        jobid = config.software().job_id()
        if jobid is None:
            raise prisms_jobs.JobsError(0, "Could not determine jobid")

    job = db.select_job(jobid)
    db.error_job(message, job=job)
    db.close()
