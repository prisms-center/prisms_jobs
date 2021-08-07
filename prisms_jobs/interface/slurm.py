""" Functions for interfacing between slurm and the prisms_jobs module """

#pylint: disable=line-too-long, too-many-locals, too-many-branches
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

### External ###
import datetime
import os
import re
import subprocess
import time

from io import StringIO

### Internal ###
import prisms_jobs
from prisms_jobs import JobsError
from prisms_jobs.misc import getlogin, run, seconds

def _squeue(jobid=None, username=getlogin(), full=False, sformat=None):    #pylint: disable=unused-argument
    """Return the stdout of squeue minus the header lines.

       By default, 'username' is set to the current user.
       'full' is the '-f' option
       'jobid' is a string or list of strings of job ids
       'sformat' is a squeue format string (e.g., "%A %i %j %c")

    Returns:
        str: the text of squeue, minus the header lines
    """

    # If Full is true, we need to use scontrol:
    if full is True:
        if jobid is None:
            if username is None:
                # Clearly we want ALL THE JOBS
                sopt = ["scontrol", "show", "job"]

                # Submit the command
                # Nothing to strip, as scontrol provides no headers
                return run(sopt)[0]

            else:
                # First, get jobids that belong to that username using
                # squeue (-h strips the header)
                sopt = ["squeue", "-h", "-u", username]

                qsout = run(sopt)[0]

                # Get the jobids
                jobid = []
                for line in StringIO(qsout):
                    jobid += [line.rstrip("\n").split()[0]]
                # Great, now we have some jobids to pass along

        # Ensure the jobids are a list, even if they're a list of 1...
        if not isinstance(jobid, list) and jobid is not None:
            jobid = [jobid]
        if isinstance(jobid, list):
            opt = ["scontrol", "show", "job"]
            sreturn = ""
            for my_id in jobid:
                sopt = opt + [str(my_id)]
                sreturn = sreturn + run(sopt)[0] + "\n"

            return sreturn

    else:
        sopt = ["squeue", "-h"]
        if username is not None:
            sopt += ["-u", username]
        if jobid is not None:
            sopt += ["--job="]
            if isinstance(jobid, list):
                sopt += ["'"+",".join([str(i) for i in jobid])+"'"]
            else:
                sopt += [str(jobid)]
        if sformat is not None:
            sopt += ["-o", "'" + sformat + "'"]
        else:
            if jobid is None and username is None:
                sopt += ["-o", "'%i %u %P %j %U %D %C %m %l %t %M'"]
            else:
                sopt += ["-o", "'%i %j %u %M %t %P'"]

        return run(sopt)[0]


### Required ###

NAME = 'slurm'

def sub_string(job):
    """Write Job as a string suitable for slurm

    Args:
        prisms_jobs.Job: Job to be submitted
    """
    ### NOT USED:
    ###    exetime
    ###    priority
    ###    auto
    jobstr = "#!/bin/sh\n"
    jobstr += "#SBATCH -J {0}\n".format(job.name)
    if job.account is not None:
        jobstr += "#SBATCH -A {0}\n".format(job.account)
    jobstr += "#SBATCH -t {0}\n".format(job.walltime)
    jobstr += "#SBATCH -n {0}\n".format(job.nodes*job.ppn)
    if job.pmem is not None:
        jobstr += "#SBATCH --mem-per-cpu={0}\n".format(job.pmem)
    if job.qos is not None:
        jobstr += "#SBATCH --qos={0}\n".format(job.qos)
    if job.email != None and job.message != None:
        jobstr += "#SBATCH --mail-user={0}\n".format(job.email)
        if 'b' in job.message:
            jobstr += "#SBATCH --mail-type=BEGIN\n"
        if 'e' in job.message:
            jobstr += "#SBATCH --mail-type=END\n"
        if 'a' in job.message:
            jobstr += "#SBATCH --mail-type=FAIL\n"
    # SLURM does assignment to no. of nodes automatically
    # jobstr += "#SBATCH -N {0}\n".format(job.nodes)
    if job.queue is not None:
        jobstr += "#SBATCH -p {0}\n".format(job.queue)
    if job.constraint is not None:
        jobstr += "#SBATCH --constraint={0}\n".format(job.constraint)
    jobstr += "{0}\n".format(job.command)

    return jobstr

def job_id(all=False, name=None):       #pylint: disable=redefined-builtin
    """Get job IDs

    Args:
        all (bool): If True, use ``squeue`` to query all user jobs. Else, check
        ``SLURM_JOBID`` environment variable for ID of current job.

        name (str): If all==True, use name to filter results.

    Returns:
        One of str, List(str), or None:
            Returns a str if all==False and ``SLURM_JOBID`` exists, a List(str)
            if all==True,  else None.

    """
    if all or name is not None:
        jobid = []
        sout = _squeue()
        for line in StringIO(sout):
            if name is not None:
                if line.split()[3] == name:
                    jobid.append((line.split()[0]).split(".")[0])
            else:
                jobid.append((line.split()[0]).split(".")[0])
        return jobid
    else:
        if 'SLURM_JOBID' in os.environ:
            return os.environ['SLURM_JOBID'].split(".")[0]
        else:
            return None

def job_rundir(jobid):
    """Return the directory job was run in using ``squeue``.

    Args:
        jobid (str or List(str)):
            IDs of jobs to get the run directory

    Returns:
        dict:
            A dict, with id:rundir pairs.
    """
    rundir = dict()

    if isinstance(jobid, (list)):
        for i in jobid:
            stdout = _squeue(jobid=i, full=True)
            match = re.search("WorkDir=(.*),", stdout)
            rundir[i] = match.group(1)
    else:
        stdout = _squeue(jobid=jobid, full=True)
        match = re.search("WorkDir=(.*),", stdout)
        rundir[i] = match.group(1)
    return rundir

def job_status(jobid=None):
    """Return job status using ``squeue``

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
            "qstatstr"          result of ``squeue -f jobid``, None if not found
            "elapsedtime"       None if not started, else seconds as int
            "starttime"         None if not started, else seconds since epoch as int
            "completiontime"    None if not completed, else seconds since epoch as int
            ================    ======================================================

    """
    status = dict()

    sout = _squeue(jobid=jobid, full=True)

    jobstatus = {
        "jobid" : None,
        "jobname" : None,
        "nodes" : None,
        "procs" : None,
        "walltime" : None,
        "qstatstr" : None,
        "elapsedtime" : None,
        "starttime" : None,
        "completiontime" : None,
        "jobstatus" : None,
        "cluster": None}

    for line in StringIO(sout):
        # Check for if we're at a new job header line
        m = re.search(r"JobId=\s*(\S*)\s*", line)      #pylint: disable=invalid-name
        if m:
            if jobstatus["jobstatus"] is not None:
                status[jobstatus["jobid"]] = jobstatus
            jobstatus = {"jobid" : None, "jobname" : None, "nodes" : None, "procs" : None, "walltime" : None, "qstatstr" : None, "elapsedtime" : None, "starttime" : None, "completiontime" : None, "jobstatus" : None, "cluster" : None}
            jobstatus["jobid"] = m.group(1)

            # Grab the job name
            m = re.match(r"\S*\s*Name=\s*(.*)\s?", line)       #pylint: disable=invalid-name
            if m:
                jobstatus["jobname"] = m.group(1)

            # Save the full output
            jobstatus["qstatstr"] = line
            continue

        jobstatus["qstatstr"] += line

        # Look for the Nodes/PPN Info
        m = re.search(r"NumNodes=\s*([0-9]*)\s", line)
        if m:
            jobstatus["nodes"] = int(m.group(1))
            m = re.search(r"NumCPUs=\s*([0-9]*)\s", line)
            if m:
                jobstatus["procs"] = int(m.group(1))
            continue


        # Look for timing info
        m = re.search(r"RunTime=\s*([0-9]*:[0-9]*:[0-9]*)\s", line) #pylint: disable=invalid-name
        if m:
            if m.group(1) == "Unknown":
                continue
            hrs, mns, scs = m.group(1).split(":")
            runtime = datetime.timedelta(hours=int(hrs), minutes=int(mns), seconds=int(scs))
            jobstatus["elapsedtime"] = runtime.seconds

            m = re.match(r"\S*\s*TimeLimit=\s*([0-9]*:[0-9]*:[0-9]*)\s", line) #pylint: disable=invalid-name
            if m:
                walltime = datetime.timedelta(hours=int(hrs), minutes=int(mns), seconds=int(scs))
                jobstatus["walltime"] = walltime.seconds
            continue

        # Grab the job start time
        m = re.search(r"StartTime=\s*([0-9]*\-[0-9]*\-[0-9]*T[0-9]*:[0-9]*:[0-9]*)\s", line) #pylint: disable=invalid-name
        if m:
            if m.group(1) == "Unknown":
                continue
            year, month, day = m.group(1).split("T")[0].split("-")
            hrs, mns, scs = m.group(1).split("T")[1].split(":")
            starttime = datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hrs), minute=int(mns), second=int(scs))
            jobstatus["starttime"] = time.mktime(starttime.timetuple())
            continue

        # Grab the job status
        m = re.search(r"JobState=\s*([a-zA-Z]*)\s", line) #pylint: disable=invalid-name
        if m:
            my_status = m.group(1)
            if my_status == "RUNNING" or my_status == "CONFIGURING":
                jobstatus["jobstatus"] = "R"
            elif my_status == "BOOT_FAIL" or my_status == "FAILED" or my_status == "NODE_FAIL" or my_status == "CANCELLED" or my_status == "COMPLETED" or my_status == "PREEMPTED" or my_status == "TIMEOUT":
                jobstatus["jobstatus"] = "C"
            elif my_status == "COMPLETING" or my_status == "STOPPED":
                jobstatus["jobstatus"] = "E"
            elif my_status == "PENDING" or my_status == "SPECIAL_EXIT":
                jobstatus["jobstatus"] = "Q"
            elif my_status == "SUSPENDED":
                jobstatus["jobstatus"] = "S"
            else:
                jobstatus["jobstatus"] = "?"
            continue

        # Grab the cluster/allocating node:
        m = re.search(r"AllocNode:\s*.*=(.*):.*", line) #pylint: disable=invalid-name
        if m:
            raw_str = m.group(1)
            m = re.search(r"(.*?)(?=[^a-zA-Z0-9]*login.*)", raw_str)    #pylint: disable=invalid-name
            if m:
                jobstatus["cluster"] = m.group(1)
            else:
                jobstatus["cluster"] = raw_str


    if jobstatus["jobstatus"] is not None:
        status[jobstatus["jobid"]] = jobstatus

    return status

def submit(substr, write_submit_script=None):
    """Submit a job using ``sbatch``.

    Args:
        substr (str): The submit script string
        write_submit_script (bool, optional): If true, submit via file skipping
            lines containing '#SBATCH -J'; otherwise, submit via commandline. If
            not specified, uses ``prisms_jobs.config['write_submit_script']``.


    Returns:
        str: ID of submitted job

    Raises:
        JobsError: If a submission error occurs
    """

    m = re.search(r"#SBATCH\s+-J\s+(.*)\s", substr)       #pylint: disable=invalid-name
    if m:
        jobname = m.group(1)        #pylint: disable=unused-variable
    else:
        raise JobsError(
            None,
            r"""Error in pbs.misc.submit(). Jobname ("#SBATCH\s+-J\s+(.*)\s") not found in submit string.""")

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
                if not re.search(r"SBATCH\s+-J\s+(.*)", line):
                    f.write(line + '\n')
        stdout, stderr, returncode = run(["sbatch", jobname])  #pylint: disable=unused-variable
    else:
        stdout, stderr, returncode = run(["sbatch"], input=substr, stdin=subprocess.PIPE)  #pylint: disable=unused-variable
    print(stdout[:-1])
    if re.search("error", stdout):
        raise JobsError(0, "Submission error.\n" + stdout + "\n" + stderr)
    else:
        jobid = stdout.rstrip().split()[-1]
        return jobid

def delete(jobid):
    """``scancel`` a job.

    Args:
        jobid (str): ID of job to cancel

    Returns:
        int: ``scancel`` returncode

    """
    return run(["scancel", jobid])[2]

def hold(jobid):
    """``scontrol`` delay a job.

    Args:
        jobid (str): ID of job to delay (for 30days)

    Returns:
        int: ``scontrol`` returncode

    """
    return run(["scontrol", "update", "JobId=", jobid, "StartTime=", "now+30days"])[2]

def release(jobid):
    """``scontrol`` un-delay a job.

    Args:
        jobid (str): ID of job to release

    Returns:
        int: ``scontrol`` returncode

    """
    return run(["scontrol", "update", "JobId=", jobid, "StartTime=", "now"])[2]

def alter(jobid, arg):
    """``scontrol`` update job.

    Args:
        jobid (str): ID of job to alter
        arg (str): 'arg' is a scontrol command option string. For instance, "-a 201403152300.19"

    Returns:
        int: ``scontrol`` returncode
    """
    return run(["scontrol", "update", "JobId=", jobid] + arg.split())[2]

def read(job, qsubstr):
    """Raise exception"""
    raise Exception("primsms_jobs.read is not yet implemented for Slurm")
