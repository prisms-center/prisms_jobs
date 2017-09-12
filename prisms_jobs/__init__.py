"""Job submission and management"""
import os
import imp
from distutils.spawn import find_executable
import warnings 

_IMPORT_WARNING_MSG = """\
prisms_jobs does not detect any job management software 
and the 'PRISMS_JOBS_SOFTWARE' environment variable is not set.
"""

def set_software(user_override=None):
    """
    Import interface with job management software as module named ``prisms_jobs.software``

    Args:
        user_override (str, optional, default=None):
            
            By default, will attempt to automatically detect 'torque' (via 'qstat') 
            or 'slurm' (via 'sbatch'), or lets user override choice of module via 
            the input argument or 'PRISMS_JOBS_SOFTWARE' environment variable. The 
            options are:
        
                * 'torque'
                * 'slurm'
                * Anything else will be treated as the name of an existing python module
    
    Raises:
        prisms_jobs.JobDBError: If 'PRISMS_JOBS_SOFTWARE' option is unrecognized 
        
    """
    global software
    if user_override is not None:
        if user_override.lower() == 'torque':
            import prisms_jobs.interface.torque as software
        elif user_override.lower() == 'slurm':
            import prisms_jobs.interface.slurm as software
        elif user_override.lower() == 'default':
            import prisms_jobs.interface.default as software
        else:
            try:
                f, filename, description = imp.find_module(user_override)
                try:
                    software = imp.load_module(user_override, f, filename, description)
                finally:
                    if f:
                        f.close()
            except:
                raise Exception('Unrecognized PRISMS_JOBS_SOFTWARE: ' + user_override)
    elif find_executable("qsub") is not None:
        import prisms_jobs.interface.torque as software
    elif find_executable("sbatch") is not None:
        import prisms_jobs.interface.slurm as software
    else:
        #warnings.warn(_IMPORT_WARNING_MSG)
        import prisms_jobs.interface.default as software

class JobsError(Exception):
    """ A custom error class for pbs errors """
    def __init__(self, jobid, msg):
        self.jobid = jobid
        self.msg = msg
        super(JobsError, self).__init__()

    def __str__(self):
        return self.jobid + ": " + self.msg
    
# import into 'prisms_jobs'
from job import Job
from jobdb import JobDB, JobDBError, EligibilityError, complete_job, error_job
import templates

set_software(user_override = os.environ.get('PRISMS_JOBS_SOFTWARE', None))

__version__ = '3.0.1'
__all__ = [
    'Job',
    'JobDB',
    'JobsError',
    'JobDBError',
    'EligibilityError', 
    'complete_job',
    'error_job'
    'set_software']
