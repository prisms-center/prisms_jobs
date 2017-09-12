"""Job management software interfaces

Each interface is expected to have the following variables/functions. See
one of the included interfaces for specifics of arguments and return values.

* NAME (str): Interface module name
* sub_string(job): Write prisms_jobs.Job instance as a string suitable for submission
* job_id(all=False, name=None): Get job ID(s)
* job_rundir(): Get job run directories
* job_status(jobid=None): Get job status
* submit(substr): Submit a job
* delete(jobid): Delete a job
* hold(jobid): Hold / delay a job
* release(jobid): Release a job
* alter(jobid, arg): Alter job options
* read(jobid, arg): Read prisms_jobs.Job instance from a submit script
"""
