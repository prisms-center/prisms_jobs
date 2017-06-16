""" Misc functions for interfacing between torque and the pbs module """

import subprocess
import os
import StringIO
import re
import datetime
import time
import sys
from pbs.misc import getlogin, seconds, PBSError
from distutils.spawn import find_executable

### Internal ###

def _getversion():
    """Returns the torque version or 0. if no ``qstat`` """
    if find_executable("qstat") is None:
        return 0.
    opt = ["qstat", "--version"]

    # call 'qstat' using subprocess
    p = subprocess.Popen(opt, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) #pylint: disable=invalid-name
    stdout, stderr = p.communicate()    #pylint: disable=unused-variable
    sout = StringIO.StringIO(stdout)

    # return the version number
    return float(sout.read().rstrip("\n").lower().lstrip("version: ").split(".")[0])

torque_version = _getversion()


def _qstat(jobid=None, username=getlogin(), full=False):
    """Return the stdout of ``qstat`` minus the header lines.

       By default, 'username' is set to the current user.
       'full' is the '-f' option
       'jobid' is a string or list of strings of job ids

       Returns the text of qstat, minus the header lines
    """

    # -u and -f contradict in earlier versions of Torque
    if full and username is not None and (torque_version < 5.0 and jobid is None):
        # First get all jobs by the user
        qopt = ["qselect"]
        qopt += ["-u", username]

        # Call 'qselect' using subprocess
        q = subprocess.Popen(qopt, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)     #pylint: disable=invalid-name
        stdout, stderr = q.communicate()    #pylint: disable=unused-variable

        qsout = StringIO.StringIO(stdout)

        # Get the jobids
        jobid = []
        for line in qsout:
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
        if isinstance(jobid, str) or isinstance(jobid, unicode):
            jobid = [jobid]
        elif isinstance(jobid, list):
            pass
        else:
            print "Error in pbs.interface.torque.qstat(). type(jobid):", type(jobid)
            sys.exit()
        opt += jobid

    # call 'qstat' using subprocess
    # print opt
    p = subprocess.Popen(opt, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)     #pylint: disable=invalid-name
    stdout, stderr = p.communicate()        #pylint: disable=unused-variable

    sout = StringIO.StringIO(stdout)

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
        job (pbs.Job instance): Job to be submitted
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
        jobid (str, List(str), or None):
            Returns a List(str) if all==True, a str if all==False and 
            ``PBS_JOBID`` exists, else None.
    
    """
    if all or name is not None:
        jobid = []
        stdout = _qstat()
        sout = StringIO.StringIO(stdout)
        for line in sout:
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
        rundirs (dict):
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
    
        status (dict of dict):
        
            The outer dict uses jobid as key in outer dict.
   
            Inner dict contains:
       
            ===============    =====================================================
            "name"             Job name
            "nodes"            Number of nodes
            "procs"            Number of processors
            "walltime"         Walltime
            "jobstatus"        status ("Q","C","R", etc.)
            "qstatstr"         result of ``squeue -f jobid``, None if not found
            "elapsedtime"      None if not started, else seconds as int
            "starttime"        None if not started, else seconds since epoch as int
            "completiontime"   None if not completed, else seconds since epoch as int

    Note:
        *This should be edited to return job_status_dict()'s*
    """
    status = dict()

    stdout = _qstat(jobid=jobid, full=True)
    sout = StringIO.StringIO(stdout)

### TODO: figure out why jobstatus is being initialized as a None vs as a dict() and then checked for content ### pylint: disable=fixme
    jobstatus = None

    for line in sout:

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

def submit(substr):
    """Submit a job using ``qsub``.

    Args:
        substr (str): The submit script string
    
    Returns:
        jobid (str): ID of submitted job
    
    Raises:
        PBSError: If a submission error occurs
    """

    m = re.search(r"-N\s+(.*)\s", substr)       #pylint: disable=invalid-name
    if m:
        jobname = m.group(1)        #pylint: disable=unused-variable
    else:
        raise PBSError(
            None,
            r"Error in pbs.misc.submit(). Jobname (\"-N\s+(.*)\s\") not found in submit string.")

    p = subprocess.Popen(   #pylint: disable=invalid-name
        "qsub", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = p.communicate(input=substr)       #pylint: disable=unused-variable
    print stdout[:-1]
    if re.search("error", stdout):
        raise PBSError(0, "PBS Submission error.\n" + stdout + "\n" + stderr)
    else:
        jobid = stdout.split(".")[0]
        return jobid

def delete(jobid):
    """``qdel`` a PBS job.
    
    Args:
        jobid (str): ID of job to delete
    
    Returns:
        code (int): ``qdel`` returncode
    
    """
    p = subprocess.Popen(   #pylint: disable=invalid-name
        ["qdel", jobid], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = p.communicate()        #pylint: disable=unused-variable
    return p.returncode

def hold(jobid):
    """``qhold`` a job.
    
    Args:
        jobid (str): ID of job to hold
    
    Returns:
        code (int): ``qhold`` returncode
    
    """
    p = subprocess.Popen(   #pylint: disable=invalid-name
        ["qhold", jobid], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = p.communicate()    #pylint: disable=unused-variable
    return p.returncode

def release(jobid):
    """``qrls`` a job.
    
    Args:
        jobid (str): ID of job to release
    
    Returns:
        code (int): ``qrls`` returncode
    
    """
    p = subprocess.Popen(   #pylint: disable=invalid-name
        ["qrls", jobid], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = p.communicate()    #pylint: disable=unused-variable
    return p.returncode

def alter(jobid, arg):
    """``qalter`` a job.

    Args:
        jobid (str): ID of job to alter
        arg (str): 'arg' is a scontrol command option string. For instance, "-a 201403152300.19"
    
    Returns:
        code (int): ``qalter`` returncode
    """
    p = subprocess.Popen(   #pylint: disable=invalid-name
        ["qalter"] + arg.split() + [jobid], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = p.communicate()    #pylint: disable=unused-variable
    return p.returncode

