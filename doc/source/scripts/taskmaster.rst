.. scripts/taskmaster.rst

taskmaster
==========

``taskmaster`` submits a job on the PRISMS flux debug queue that will repeatedly
resubmit any ``Auto`` jobs in the job database that have completed but whose
taskstatus is still ``'Incomplete'`` (perhaps because the jobs has hit the walltime
before completing or failed to converge) and then resubmit itself with a delay
before execution.

To use on machines other than flux change the line containing 

::

    j = prisms_jobs.templates.PrismsDebugJob(...)

Help documentation:
-------------------

.. argparse::
    :filename: scripts/taskmaster
    :func: parser
    :prog: taskmaster
    
    
