""" Misc functions for interfacing between torque and the prisms_jobs module """
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

import datetime
import os
import re
import subprocess
import sys
import time

from distutils.spawn import find_executable
from io import StringIO
from six import iteritems, string_types

import prisms_jobs
from prisms_jobs import JobsError
from prisms_jobs.misc import getlogin, run, seconds

### Internal ###


def _getversion():
    """Returns the torque version as string or None if no ``qstat`` """
    if find_executable("qstat") is None:
        return None
    opt = ["qstat", "--version"]

    # call 'qstat' using subprocess
    stdout = run(opt)[0]

    # return the version number
    return stdout.rstrip("\n").lower().lstrip("version: ")

torque_version = _getversion()


def _qstat(jobid=None, username=getlogin(), full=False):
    """Return the stdout of ``qstat`` minus the header lines.

       By default, 'username' is set to the current user.
       'full' is the '-f' option
       'jobid' is a string or list of strings of job ids

    Returns:
        str: the text of qstat, minus the header lines
    """

    # -u and -f contradict in earlier versions of Torque
    if full and username is not None and int(torque_version.split(".")[0]) < 5 and jobid is None:
        # First get all jobs by the user
        qopt = ["qselect"]
        qopt += ["-u", username]

        # Call 'qselect' using subprocess
        stdout = run(qopt)[0]

        # Get the jobids
        jobid = []
        for line in StringIO(stdout):
            jobid += [line.rstrip("\n")]

    opt = ["qstat"]
    # If there are jobid(s), you don't need a username
    if username is not None and jobid is None:
        opt += ["-u", username]
    # But if there are jobid(s) and a username, you need -a to get full output
    elif username is not None and jobid is not None and not full:
        opt += ["-a"]
    # By this point we're guaranteed torque ver >= 5.0, so -u and -f are safe together
    if full:
        opt += ["-f"]
    if jobid is not None:
        if isinstance(jobid, string_types):
            jobid = [jobid]
        elif isinstance(jobid, list):
            pass
        else:
            print("Error in prisms_jobs.interface.torque.qstat(). type(jobid):", type(jobid))
            sys.exit()
        opt += jobid

    # call 'qstat' using subprocess
    stdout, stderr, returncode = run(opt)        #pylint: disable=unused-variable
    sout = StringIO(stdout)
    # strip the header lines
    if full is False:
        for line in sout:
            if line[0] == "-":
                break

    # return the remaining text
    return sout.read()

### Required ###

NAME = 'torque'

def sub_string(job):
    """Write Job as a string suitable for torque

    Args:
        job (prisms_jobs.Job instance): Job to be submitted
    """
    jobstr = "#!/bin/sh\n"
    jobstr += "#PBS -S /bin/sh\n"
    jobstr += "#PBS -N {0}\n".format(job.name)
    if job.exetime is not None:
        jobstr += "#PBS -a {0}\n".format(job.exetime)
    if job.account is not None:
        jobstr += "#PBS -A {0}\n".format(job.account)
    jobstr += "#PBS -l walltime={0}\n".format(job.walltime)
    jobstr += "#PBS -l nodes={0}:ppn={1}\n".format(job.nodes, job.ppn)
    if job.pmem is not None:
        jobstr += "#PBS -l pmem={0}\n".format(job.pmem)
    if job.qos is not None:
        jobstr += "#PBS -l qos={0}\n".format(job.qos)
    if job.queue is not None:
        jobstr += "#PBS -q {0}\n".format(job.queue)
    if job.email != None and job.message != None:
        jobstr += "#PBS -M {0}\n".format(job.email)
        jobstr += "#PBS -m {0}\n".format(job.message)
    jobstr += "#PBS -V\n"
    jobstr += "#PBS -p {0}\n\n".format(job.priority)
    jobstr += "#auto={0}\n\n".format(job.auto)
    jobstr += "echo \"I ran on:\"\n"
    jobstr += "cat $PBS_NODEFILE\n\n"
    jobstr += "cd $PBS_O_WORKDIR\n"
    jobstr += "{0}\n".format(job.command)

    return jobstr

def job_id(all=False, name=None):       #pylint: disable=redefined-builtin
    """Get job IDs

    Args:
        all (bool): If True, use ``qstat`` to query all user jobs. Else, check
        ``PBS_JOBID`` environment variable for ID of current job.

        name (str): If all==True, use name to filter results.

    Returns:
        One of str, List(str), or None:
            Returns a str if all==False and ``PBS_JOBID`` exists, a List(str)
            if all==True, else None.

    """
    if all or name is not None:
        jobid = []
        stdout = _qstat()
        for line in StringIO(stdout):
            if name is not None:
                if line.split()[3] == name:
                    jobid.append((line.split()[0]).split(".")[0])
            else:
                jobid.append((line.split()[0]).split(".")[0])
        return jobid
    else:
        if 'PBS_JOBID' in os.environ:
            return os.environ['PBS_JOBID'].split(".")[0]
        else:
            return None

def job_rundir(jobid):
    """Return the directory job was run in using ``qstat``.

    Args:
        jobid (str or List(str)):
            IDs of jobs to get the run directory

    Returns:
        dict:
            A dict, with id:rundir pairs.
    """
    rundir = dict()

    if isinstance(id, (list)):
        for i in jobid:
            stdout = _qstat(jobid=i, full=True)
            match = re.search(",PWD=(.*),", stdout)
            rundir[i] = match.group(1)
    else:
        stdout = _qstat(jobid=jobid, full=True)
        match = re.search(",PWD=(.*),", stdout)
        rundir[i] = match.group(1)
    return rundir

def job_status(jobid=None):
    """Return job status using ``qstat``

    Args:
        jobid (None, str, or List(str)):
            IDs of jobs to query for status. None for all user jobs.

    Returns:

        dict of dict:

            The outer dict uses jobid as key; the inner dict contains:

            ================    ======================================================
            "jobname"           Job name
            "nodes"             Number of nodes
            "procs"             Number of processors
            "walltime"          Walltime
            "jobstatus"         status ("Q","C","R", etc.)
            "qstatstr"          result of ``qstat -f jobid``, None if not found
            "elapsedtime"       None if not started, else seconds as int
            "starttime"         None if not started, else seconds since epoch as int
            "completiontime"    None if not completed, else seconds since epoch as int
            ================    ======================================================

    """
    status = dict()

    sout = _qstat(jobid=jobid, full=True)
    jobstatus = None

    for line in StringIO(sout):

        m = re.search(r"Job Id:\s*(.*)\s", line)      #pylint: disable=invalid-name
        if m:
            if jobstatus is not None:
                if jobstatus["jobstatus"] == "R":           #pylint: disable=unsubscriptable-object
                    jobstatus["elapsedtime"] = int(time.time()) - jobstatus["starttime"]    #pylint: disable=unsubscriptable-object
                status[jobstatus["jobid"]] = jobstatus #pylint: disable=unsubscriptable-object
            jobstatus = dict()
            jobstatus["jobid"] = m.group(1).split(".")[0]
            jobstatus["qstatstr"] = line
            jobstatus["elapsedtime"] = None
            jobstatus["starttime"] = None
            jobstatus["completiontime"] = None
            continue

        jobstatus["qstatstr"] += line

        #results = line.split()
        #jobid = results[0].split(".")[0]
        #jobstatus = dict()
        #jobstatus["jobid"] = jobid

        #jobstatus["jobname"] = results[3]
        m = re.match(r"\s*Job_Name\s*=\s*(.*)\s", line)       #pylint: disable=invalid-name
        if m:
            jobstatus["jobname"] = m.group(1)
            continue

        #jobstatus["nodes"] = int(results[5])
        #jobstatus["procs"] = int(results[6])
        m = re.match(r"\s*Resource_List\.nodes\s*=\s*(.*):ppn=(.*)\s", line)  #pylint: disable=invalid-name
        if m:
            jobstatus["nodes"] = m.group(1)
            jobstatus["procs"] = int(m.group(1))*int(m.group(2))
            continue

        #jobstatus["walltime"] = int(seconds(results[8]))
        m = re.match(r"\s*Resource_List\.walltime\s*=\s*(.*)\s", line)      #pylint: disable=invalid-name
        if m:
            jobstatus["walltime"] = int(seconds(m.group(1)))
            continue

        #jobstatus["jobstatus"] = results[9]
        m = re.match(r"\s*job_state\s*=\s*(.*)\s", line)        #pylint: disable=invalid-name
        if m:
            jobstatus["jobstatus"] = m.group(1)
            continue

        #elapsedtime = line.split()[10]
        #if elapsedtime == "--":
        #    jobstatus["elapsedtime"] = None
        #else:
        #    jobstatus["elapsedtime"] = int(seconds(elapsedtime))
        #
        #qstatstr = qstat(jobid, full=True)
        #if not re.match("^qstat: Unknown Job Id Error.*",qstatstr):
        #    jobstatus["qstatstr"] = qstatstr
        #    m = re.search("Job_Name = (.*)\n",qstatstr)
        #    if m:
        #        jobstatus["jobname"] = m.group(1)

        #m = re.match("\s*resources_used.walltime\s*=\s*(.*)\s",line)
        #if m:
        #    print line
        #    jobstatus["elapsedtime"] = int(seconds(m.group(1)))

        m = re.match(r"\s*start_time\s*=\s*(.*)\s", line)    #pylint: disable=invalid-name
        if m:
            jobstatus["starttime"] = int(time.mktime(datetime.datetime.strptime(
                m.group(1), "%a %b %d %H:%M:%S %Y").timetuple()))
            continue

        m = re.search(r"\s*comp_time\s*=\s*(.*)\s", line)   #pylint: disable=invalid-name
        if m:
            jobstatus["completiontime"] = int(time.mktime(datetime.datetime.strptime(
                m.group(1), "%a %b %d %H:%M:%S %Y").timetuple()))
            continue

    if jobstatus is not None:
        if jobstatus["jobstatus"] == "R":
            jobstatus["elapsedtime"] = int(time.time()) - jobstatus["starttime"]
        status[jobstatus["jobid"]] = jobstatus

    return status

def submit(substr, write_submit_script=None):
    """Submit a job using ``qsub``.

    Args:
        substr (str): The submit script string
        write_submit_script (bool, optional): If true, submit via file skipping
            lines containing '#PBS -N'; otherwise, submit via commandline. If
            not specified, uses ``prisms_jobs.config['write_submit_script']``.

    Returns:
        str: ID of submitted job

    Raises:
        JobsError: If a submission error occurs
    """

    m = re.search(r"#PBS\s+-N\s+(.*)\s", substr)       #pylint: disable=invalid-name
    if m:
        jobname = m.group(1)        #pylint: disable=unused-variable
    else:
        raise JobsError(
            None,
            r"""Error in pbs.misc.submit(). Jobname ("#PBS\s+-N\s+(.*)\s") not found in submit string.""")

    if write_submit_script is None:
        write_submit_script = prisms_jobs.config.write_submit_script()

    if write_submit_script:
        if os.path.exists(jobname):
            index = 0
            while os.path.exists(jobname + ".bak." + str(index)):
                index += 1
            print("Backing up existing submit script:", jobname, "->", jobname + ".bak." + str(index))
            os.rename(jobname, jobname + ".bak." + str(index))
        # write submit script, without -N line
        with open(jobname, 'w') as f:
            for line in substr.splitlines():
                if not re.search(r"#PBS\s+-N\s+(.*)", line):
                    f.write(line + '\n')
        stdout, stderr, returncode = run(["qsub", jobname])       #pylint: disable=unused-variable
    else:
        stdout, stderr, returncode = run(["qsub"], input=substr, stdin=subprocess.PIPE)  #pylint: disable=unused-variable
    print(stdout[:-1])
    if re.search("error", stdout):
        raise JobsError(0, "Submission error.\n" + stdout + "\n" + stderr)
    else:
        jobid = stdout.split(".")[0]
        return jobid

def delete(jobid):
    """``qdel`` a PBS job.

    Args:
        jobid (str): ID of job to delete

    Returns:
        int: ``qdel`` returncode

    """
    stdout, stderr, returncode = run(["qdel", jobid])        #pylint: disable=unused-variable
    return returncode

def hold(jobid):
    """``qhold`` a job.

    Args:
        jobid (str): ID of job to hold

    Returns:
        int: ``qhold`` returncode

    """
    stdout, stderr, returncode = run(["qhold", jobid])    #pylint: disable=unused-variable
    return returncode

def release(jobid):
    """``qrls`` a job.

    Args:
        jobid (str): ID of job to release

    Returns:
        int: ``qrls`` returncode

    """
    stdout, stderr, returncode = run(["qrls", jobid])    #pylint: disable=unused-variable
    return returncode

def alter(jobid, arg):
    """``qalter`` a job.

    Args:
        jobid (str): ID of job to alter
        arg (str): 'arg' is a scontrol command option string. For instance, "-a 201403152300.19"

    Returns:
        int: ``qalter`` returncode
    """
    stdout, stderr, returncode = run(["qalter"] + arg.split() + [jobid])    #pylint: disable=unused-variable
    return returncode

def read(job, qsubstr):    #pylint: disable=too-many-branches, too-many-statements
    """
    Set Job object from string representing a PBS submit script.

    * Will read many but not all valid PBS scripts.
    * Will ignore any arguments not included in prisms_jobs.Job()'s attributes.
    * Will add default optional arguments (i.e. ``-A``, ``-a``, ``-l pmem=(.*)``,
      ``-l qos=(.*)``, ``-M``, ``-m``, ``-p``, ``"Auto:"``) if not found.
    * Will ``exit()`` if required arguments (``-N``, ``-l walltime=(.*)``,
      ``-l nodes=(.*):ppn=(.*)``, ``-q``, ``cd $PBS_O_WORKDIR``) not found.
    * Will always include ``-V``

    Args:
        qsubstr (str): A submit script as a string

    """
    s = StringIO(qsubstr)  #pylint: disable=invalid-name

    job.pmem = None
    job.email = None
    job.message = "a"
    job.priority = "0"
    job.auto = False
    job.account = None
    job.exetime = None
    job.qos = None

    optional = dict()
    optional["account"] = "Default: None"
    optional["pmem"] = "Default: None"
    optional["email"] = "Default: None"
    optional["message"] = "Default: a"
    optional["priority"] = "Default: 0"
    optional["auto"] = "Default: False"
    optional["exetime"] = "Default: None"
    optional["qos"] = "Default: None"

    required = dict()
    required["jobname"] = "Not Found"
    required["walltime"] = "Not Found"
    required["nodes"] = "Not Found"
    required["ppn"] = "Not Found"
    required["queue"] = "Not Found"
    required["cd $PBS_O_WORKDIR"] = "Not Found"
    required["command"] = "Not Found"

    while True:
        line = s.readline()
        #print line,

        if re.search("#PBS", line):

            m = re.search(r"-N\s+(.*)\s", line) #pylint: disable=invalid-name
            if m:
                job.name = m.group(1)
                required["jobname"] = job.name

            m = re.search(r"-A\s+(.*)\s", line)  #pylint: disable=invalid-name
            if m:
                job.account = m.group(1)
                optional["account"] = job.account

            m = re.search(r"-a\s+(.*)\s", line)  #pylint: disable=invalid-name
            if m:
                job.exetime = m.group(1)
                optional["exetime"] = job.exetime

            m = re.search(r"\s-l\s", line)   #pylint: disable=invalid-name
            if m:
                m = re.search(r"walltime=([0-9:]+)", line)   #pylint: disable=invalid-name
                if m:
                    job.walltime = m.group(1)
                    required["walltime"] = job.walltime

                m = re.search(r"nodes=([0-9]+):ppn=([0-9]+)", line)   #pylint: disable=invalid-name
                if m:
                    job.nodes = int(m.group(1))
                    job.ppn = int(m.group(2))
                    required["nodes"] = job.nodes
                    required["ppn"] = job.ppn

                m = re.search(r"pmem=([^,\s]+)", line)    #pylint: disable=invalid-name
                if m:
                    job.pmem = m.group(1)
                    optional["pmem"] = job.pmem

                m = re.search(r"qos=([^,\s]+)", line) #pylint: disable=invalid-name
                if m:
                    job.qos = m.group(1)
                    optional["qos"] = job.qos
            #

            m = re.search(r"-q\s+(.*)\s", line)  #pylint: disable=invalid-name
            if m:
                job.queue = m.group(1)
                required["queue"] = job.queue

            m = re.match(r"-M\s+(.*)\s", line) #pylint: disable=invalid-name
            if m:
                job.email = m.group(1)
                optional["email"] = job.email

            m = re.match(r"-m\s+(.*)\s", line) #pylint: disable=invalid-name
            if m:
                job.message = m.group(1)
                optional["message"] = job.message

            m = re.match(r"-p\s+(.*)\s", line)   #pylint: disable=invalid-name
            if m:
                job.priority = m.group(1)
                optional["priority"] = job.priority
        #

        m = re.search(r"auto=\s*(.*)\s", line)   #pylint: disable=invalid-name
        if m:
            if re.match("[fF](alse)*|0", m.group(1)):
                job.auto = False
                optional["auto"] = job.auto
            elif re.match("[tT](rue)*|1", m.group(1)):
                job.auto = True
                optional["auto"] = job.auto
            else:
                print("Error in prisms_jobs.Job().read(). '#auto=' argument not understood:", line)
                sys.exit()

        m = re.search(r"cd\s+\$PBS_O_WORKDIR\s+", line)  #pylint: disable=invalid-name
        if m:
            required["cd $PBS_O_WORKDIR"] = "Found"
            job.command = s.read()
            required["command"] = job.command
            break
    # end for

    # check for required arguments
    for k in required:
        if required[k] == "Not Found":

            print("Error in prisms_jobs.Job.read(). Not all required arguments were found.\n")

            # print what we found:
            print("Optional arguments:")
            for k, v in iteritems(optional):    #pylint: disable=invalid-name
                print(k + ":", v)
            print("\nRequired arguments:")
            for k, v in iteritems(required):    #pylint: disable=invalid-name
                if k == "command":
                    print(k + ":")
                    print("--- Begin command ---")
                    print(v)
                    print("--- End command ---")
                else:
                    print(k + ":", v)

            sys.exit()
    # end if
# end def
