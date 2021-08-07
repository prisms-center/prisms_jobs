"""Job submission and management"""

class JobsError(Exception):
    """ A custom error class for prisms_jobs errors """
    def __init__(self, jobid, msg):
        self.jobid = jobid
        self.msg = msg
        super(JobsError, self).__init__()

    def __str__(self):
        return self.jobid + ": " + self.msg

# import into 'prisms_jobs'
from prisms_jobs.job import Job
from prisms_jobs.jobdb import JobDB, JobDBError, EligibilityError, complete_job, error_job

__version__ = '4.0.3'
__all__ = [
    'Job',
    'JobDB',
    'JobsError',
    'JobDBError',
    'EligibilityError',
    'complete_job',
    'error_job']
