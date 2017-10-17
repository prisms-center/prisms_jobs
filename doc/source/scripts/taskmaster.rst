.. scripts/taskmaster.rst

``taskmaster``
==============

Summary:
--------

``taskmaster`` submits a job that will repeatedly resubmit any ``Auto`` jobs in 
the job database that have completed but whose taskstatus is still ``'Incomplete'`` 
(perhaps because the jobs has hit the walltime before completing or failed to 
converge) and then resubmit itself with a delay before execution. As not all
compute resources allow this behavior, remember check the policy prior to using
``taskmaster`` on a new compute resource.

The job submission options can be customized by editing the ``prisms-jobs``
`configuration file`_.


``--help`` documentation:
-------------------------

.. argparse::
    :filename: prisms_jobs/scripts/taskmaster.py
    :func: parser
    :prog: taskmaster

_`configuration file`: config.html
