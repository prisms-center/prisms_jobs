""" Stub to use when running on a machine without job management software """


### Required ###

NAME = 'default'

def job_id(all=False, name=None):       #pylint: disable=redefined-builtin
    """Get job IDs"""
    raise Exception("No job management software found")

def job_rundir(jobid):
    """Return the directory job was run in"""
    raise Exception("No job management software found")

def job_status(jobid=None):
    """Return job status"""
    raise Exception("No job management software found")

def submit(substr):
    """Submit a job"""
    raise Exception("No job management software found")

def delete(jobid):
    """Delete a job"""
    raise Exception("No job management software found")

def hold(jobid):
    """Hold a job"""
    raise Exception("No job management software found")

def release(jobid):
    """Release a job"""
    raise Exception("No job management software found")

def alter(jobid, arg):
    """Alter a job"""
    raise Exception("No job management software found")

