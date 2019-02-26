""" Class for individual Job objects """
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

### External ###
# import subprocess
import os
import re
import sys

### Local ###
import prisms_jobs
from prisms_jobs import config, jobdb, misc

class Job(object):  #pylint: disable=too-many-instance-attributes
    """Represents a computational job

    Initialize either with all the parameters, or with 'substr' a submit script as a string.
    If 'substr' is given, all other arguments are ignored.

    Args:
        substr (str): A submit script as a string.
        name (str): Job name. Ex: ``"myjob-0"``

            The name specified may be up to and including 15 characters
            in length. It must consist of printable, non white space characters
            with the first character alphabetic.

        account (str):  Account name. Ex: ``"prismsproject_fluxoe"``
        nodes (int):    Number of nodes. Ex: 2
        ppn (int):      Processors per node. Ex: 16
        walltime (str): Walltime (``HH:MM:SS``). Ex: ``"10:00:00"``
        pmem (str):     Memory requsted. Ex: ``"3800mb"``
        qos (str):      Ex: ``"flux"``
        queue (str):    Ex: ``"fluxoe"``

        exetime (str):  Time after which the job is eligible for execution. Ex: ``"1100"``

            Has the form: ``[[[[CC]YY]MM]DD]hhmm[.SS]``
            Create using ``prisms_jobs.misc.exetime(deltatime)``, where deltatime
            is a ``[[[DD:]MM:]HH:]SS`` string.

        message (str):  When to send email about the job. Ex: ``"abe"``

            The mail_options argument is a string which consists of either the single
            character ``"n"``, or one or more of the characters ``"a"``, ``"b"``,
            and ``"e"``.

            If the character ``"n"`` is specified, no normal mail is sent. Mail for job
            cancels and other events outside of normal job processing are still sent.

            For the letters ``"a"``, ``"b"``, and ``"e"``:

               ===    ===
                a     mail is sent when the job is aborted by the batch system.
                b     mail is sent when the job begins execution.
                e     mail is sent when the job terminates.
               ===    ===

        email (str):  Where to send notifications.  Ex: ``"jdoe@umich.edu"``

            The email string is of the form: ``user[@host][,user[@host],...]``

        priority (str):  Priority ranges from (low) -1024 to (high) 1023. Ex: ``"-200"``

        command (str):   String with command to run by script. Ex: ``"echo \"hello\" > test.txt"``

        auto (bool, optional, Default=False):

            Indicates an automatically re-submitting job.  Ex: ``True``

            Only set to True if the command uses this prisms_jobs module to set
            itself as completed when it is completed. Otherwise, you may submit
            it extra times leading to wasted resources and overwritten data.

    Attributes:
        name (str): Job name. Ex: ``"myjob-0"``
        account (str):  Account name. Ex: ``"prismsproject_fluxoe"``
        nodes (int):    Number of nodes. Ex: 2
        ppn (int):      Processors per node. Ex: 16
        walltime (str): Walltime (``HH:MM:SS``). Ex: ``"10:00:00"``
        pmem (str):     Memory requsted. Ex: ``"3800mb"``
        qos (str):      Ex: ``"flux"``
        queue (str):    Ex: ``"fluxoe"``
        exetime (str):  Time after which the job is eligible for execution. Ex: ``"1100"``
        message (str):  When to send email about the job. Ex: ``"abe"``
        email (str):  Where to send notifications.  Ex: ``"jdoe@umich.edu"``
        priority (str):  Priority ranges from (low) -1024 to (high) 1023. Ex: ``"-200"``
        constraint (str): Constraint. Ex: ``"haswell"``
        command (str):   String with command to run by script. Ex: ``"echo \"hello\" > test.txt"``
        auto (bool):     Indicates an automatically re-submitting job.  Ex: ``True``

    """


    def __init__(self, name="STDIN", account=None, nodes=None, ppn=None, walltime=None, #pylint: disable=too-many-arguments, too-many-locals
                 pmem=None, qos=None, queue=None, exetime=None, message="a", email=None,
                 priority="0", constraint=None, command=None, auto=False, substr=None):

        if substr != None:
            self.read(substr)
            return

        # Declares a name for the job. The name specified may be up to and including
        # 15 characters in length. It must consist of printable, non white space characters
        # with the first character alphabetic.
        # If the name option is not specified, to STDIN.
        self.name = name

        # account string
        self.account = account

        # number of nodes to request
        self.nodes = int(nodes)

        # number of processors per node to request
        self.ppn = int(ppn)

        # string walltime for job (HH:MM:SS)
        self.walltime = walltime

        # string memory requested (1000mb)
        self.pmem = pmem

        # qos string
        self.qos = qos

        # queue string
        self.queue = queue

        # time eligible for execution
        # PBS -a exetime
        # Declares the time after which the job is eligible for execution,
        # where exetime has the form: [[[[CC]YY]MM]DD]hhmm[.SS]
        # create using prisms_jobs.misc.exetime( deltatime), where deltatime is a [[[DD:]MM:]HH:]SS string
        self.exetime = exetime

        # when to send email about the job
        # The mail_options argument is a string which consists of either the single
        # character "n", or one or more of the characters "a", "b", and "e".
        #
        # If the character "n" is specified, no normal mail is sent. Mail for job
        # cancels and other events outside of normal job processing are still sent.
        #
        # For the letters "a", "b", and "e":
        # a     mail is sent when the job is aborted by the batch system.
        # b     mail is sent when the job begins execution.
        # e     mail is sent when the job terminates.
        self.message = message

        # User list to send email to. The email string is of the form:
        #       user[@host][,user[@host],...]
        self.email = email

        # Priority ranges from (low) -1024 to (high) 1023
        self.priority = priority

        # Constraint (str): Ex: ``"haswell"``
        self.constraint = constraint

        # text string with command to run
        self.command = command

        # if True, simply rerun job until complete; if False, human intervention required
        # 'auto' jobs should set JobDB status to "finished" when finished
        self.auto = bool(auto)

        #self.date_time

        ##################################
        # Submission status:

        # jobID
        self.jobID = None   #pylint: disable=invalid-name

    #

    def sub_string(self):   #pylint: disable=too-many-branches
        """ Output Job as a string suitable for prisms_jobs.config.software() """
        return config.software().sub_string(self)

    def script(self, filename="submit.sh"):
        """
        Write this Job as a bash script

        Args:
            filename (str):  Name of the script. Ex: "submit.sh"

        """
        with open(filename, "w") as myfile:
            myfile.write(self.sub_string())

    def submit(self, add=True, dbpath=None):
        """
        Submit this Job using the appropriate command for prisms_jobs.config.software().

        Args:
           add (bool): Should this job be added to the JobDB database?
           dbpath (str): Specify a non-default JobDB database

        Raises:
            prisms_jobs.JobsError: If error submitting the job.

        """

        self.jobID = config.software().submit(substr=self.sub_string())

        if add:
            db = jobdb.JobDB(dbpath=dbpath) #pylint: disable=invalid-name
            status = jobdb.job_status_dict(jobid=self.jobID, jobname=self.name,
                                           rundir=os.getcwd(), jobstatus="?",
                                           auto=self.auto, qsubstr=self.sub_string(),
                                           walltime=misc.seconds(self.walltime),
                                           nodes=self.nodes, procs=self.nodes*self.ppn)
            db.add(status)
            db.close()


    def read(self, qsubstr):    #pylint: disable=too-many-branches, too-many-statements
        """
        Set this Job object from string representing a submit script appropriate
        for the config.software().

        Args:
            qsubstr (str): A submit script as a string

        """
        config.software().read(self, qsubstr)
