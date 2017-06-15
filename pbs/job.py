""" Class for individual Job objects """
### External ###
# import subprocess
import re
import os
import sys
import StringIO

### Local ###
import jobdb
import misc

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
            Create using ``pbs.misc.exetime(deltatime)``, where deltatime 
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
            
            Only set to True if the command uses this pbs module to set 
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
        command (str):   String with command to run by script. Ex: ``"echo \"hello\" > test.txt"``
        auto (bool):     Indicates an automatically re-submitting job.  Ex: ``True``
        
    """


    def __init__(self, name="STDIN", account=None, nodes=None, ppn=None, walltime=None, #pylint: disable=too-many-arguments, too-many-locals
                 pmem=None, qos=None, queue=None, exetime=None, message="a", email=None,
                 priority="0", command=None, auto=False, substr=None):

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
        # create using pbs.misc.exetime( deltatime), where deltatime is a [[[DD:]MM:]HH:]SS string
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
        """ Output Job as a string suitable for pbs.software """
        return pbs.software.sub_string(self)

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
        Submit this Job using the appropriate command for pbs.software.

        Args:
           add (bool): Should this job be added to the JobDB database?
           dbpath (str): Specify a non-default JobDB database
        
        Raises:
            PBSError: If error submitting the job.

        """

        try:
            self.jobID = pbs.software.submit(substr=self.sub_string())
        except misc.PBSError as e:  #pylint: disable=invalid-name
            raise e

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
        Set this Job object from string representing a PBS submit script.

        * Will read many but not all valid PBS scripts.
        * Will ignore any arguments not included in pbs.Job()'s attributes.
        * Will add default optional arguments (i.e. ``-A``, ``-a``, ``-l pmem=(.*)``, 
          ``-l qos=(.*)``, ``-M``, ``-m``, ``-p``, ``"Auto:"``) if not found.
        * Will ``exit()`` if required arguments (``-N``, ``-l walltime=(.*)``, 
          ``-l nodes=(.*):ppn=(.*)``, ``-q``, ``cd $PBS_O_WORKDIR``) not found.
        * Will always include ``-V``
        
        Args:
            qsubstr (str): A submit script as a string

        """
        s = StringIO.StringIO(qsubstr)  #pylint: disable=invalid-name

        self.pmem = None
        self.email = None
        self.message = "a"
        self.priority = "0"
        self.auto = False
        self.account = None
        self.exetime = None
        self.qos = None

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
        required["name"] = "Not Found"
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
                    self.name = m.group(1)
                    required["name"] = self.name

                m = re.search(r"-A\s+(.*)\s", line)  #pylint: disable=invalid-name
                if m:
                    self.account = m.group(1)
                    optional["account"] = self.account

                m = re.search(r"-a\s+(.*)\s", line)  #pylint: disable=invalid-name
                if m:
                    self.exetime = m.group(1)
                    optional["exetime"] = self.exetime

                m = re.search(r"\s-l\s", line)   #pylint: disable=invalid-name
                if m:
                    m = re.search(r"walltime=([0-9:]+)", line)   #pylint: disable=invalid-name
                    if m:
                        self.walltime = m.group(1)
                        required["walltime"] = self.walltime

                    m = re.search(r"nodes=([0-9]+):ppn=([0-9]+)", line)   #pylint: disable=invalid-name
                    if m:
                        self.nodes = int(m.group(1))
                        self.ppn = int(m.group(2))
                        required["nodes"] = self.nodes
                        required["ppn"] = self.ppn

                    m = re.search(r"pmem=([^,\s]+)", line)    #pylint: disable=invalid-name
                    if m:
                        self.pmem = m.group(1)
                        optional["pmem"] = self.pmem

                    m = re.search(r"qos=([^,\s]+)", line) #pylint: disable=invalid-name
                    if m:
                        self.qos = m.group(1)
                        optional["qos"] = self.qos
                #

                m = re.search(r"-q\s+(.*)\s", line)  #pylint: disable=invalid-name
                if m:
                    self.queue = m.group(1)
                    required["queue"] = self.queue

                m = re.match(r"-M\s+(.*)\s", line) #pylint: disable=invalid-name
                if m:
                    self.email = m.group(1)
                    optional["email"] = self.email

                m = re.match(r"-m\s+(.*)\s", line) #pylint: disable=invalid-name
                if m:
                    self.message = m.group(1)
                    optional["message"] = self.message

                m = re.match(r"-p\s+(.*)\s", line)   #pylint: disable=invalid-name
                if m:
                    self.priority = m.group(1)
                    optional["priority"] = self.priority
            #

            m = re.search(r"auto=\s*(.*)\s", line)   #pylint: disable=invalid-name
            if m:
                if re.match("[fF](alse)*|0", m.group(1)):
                    self.auto = False
                    optional["auto"] = self.auto
                elif re.match("[tT](rue)*|1", m.group(1)):
                    self.auto = True
                    optional["auto"] = self.auto
                else:
                    print "Error in pbs.Job().read(). '#auto=' argument not understood:", line
                    sys.exit()

            m = re.search(r"cd\s+\$PBS_O_WORKDIR\s+", line)  #pylint: disable=invalid-name
            if m:
                required["cd $PBS_O_WORKDIR"] = "Found"
                self.command = s.read()
                required["command"] = self.command
                break
        # end for

        # check for required arguments
        for k in required.keys():
            if required[k] == "Not Found":

                print "Error in pbs.Job.read(). Not all required arguments were found.\n"

                # print what we found:
                print "Optional arguments:"
                for k, v in optional.iteritems():    #pylint: disable=invalid-name
                    print k + ":", v
                print "\nRequired arguments:"
                for k, v in required.iteritems():    #pylint: disable=invalid-name
                    if k == "command":
                        print k + ":"
                        print "--- Begin command ---"
                        print v
                        print "--- End command ---"
                    else:
                        print k + ":", v

                sys.exit()
        # end if
    # end def







