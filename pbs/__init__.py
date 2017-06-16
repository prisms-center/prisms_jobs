"""Cluster job submission and management"""
import os
import imp
from distutils.spawn import find_executable
import warnings 

_IMPORT_WARNING_MSG = """\
casm-pbs does not detect any job management software 
and the 'CASM_PBS_SOFTWARE' environment variable is not set.
"""

def set_software(user_override=None):
    """
    Import interface with job management software as module named ``pbs.software``

    Args:
        user_override (str, optional, default=None):
            
        By default, will attempt to automatically detect 'torque' (via 'qstat') 
        or 'slurm' (via 'sbatch'), or lets user override choice of module via 
        the input argument or 'CASM_PBS_SOFTWARE' environment variable. The 
        options are:
    
            * 'torque'
            * 'slurm'
            * Anything else will be treated as the name of an existing python module
    
    Raises:
        pbs.JobDBError: If 'CASM_PBS_SOFTWARE' option is unrecognized 
        
    """
    global software
    if user_override is not None:
        if user_override.lower() == 'torque':
            import pbs.interface.torque as software
        elif user_override.lower() == 'slurm':
            import pbs.interface.slurm as software
        elif user_override.lower() == 'default':
            import pbs.interface.default as software
        else:
            try:
                f, filename, description = imp.find_module(user_override)
                try:
                    software = imp.load_module(user_override, f, filename, description)
                finally:
                    if f:
                        f.close()
            except:
                raise Exception('Unrecognized CASM_PBS_SOFTWARE: ' + user_override)
    elif find_executable("qsub") is not None:
        import pbs.interface.torque as software
    elif find_executable("sbatch") is not None:
        import pbs.interface.slurm as software
    else:
        #warnings.warn(_IMPORT_WARNING_MSG)
        import pbs.interface.default as software
    
# import into 'pbs'
from job import Job
from jobdb import JobDB, JobDBError, EligibilityError, complete_job, error_job
from misc import PBSError
import templates

set_software(user_override = os.environ.get('CASM_PBS_SOFTWARE', None))

__version__ = '3.0.0'
__all__ = [
    'Job',
    'JobDB',
    'JobDBError',
    'EligibilityError', 
    'complete_job',
    'error_job'
    'PBSError',
    'set_software']
