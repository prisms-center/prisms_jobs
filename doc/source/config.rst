.. config.rst

Configuration
=============

Environment variables (typically not necessary):

- ``PRISMS_JOBS_DB``: 

    The SQLite jobs database is stored by default at ``$HOME/.prisms_jobs/jobs.db``. 
    If ``PRISMS_JOBS_DB`` is set, then the jobs database is stored at 
    ``$PRISMS_JOBS_DB/jobs.db``.

- ``PRISMS_JOBS_SOFTWARE``: 

    By default, ``prisms-jobs`` will attempt to automatically 
    detect ``'torque'`` (by checking for the 'qstat' executable) or ``'slurm'`` (by 
    checking for the 'sbatch' executable). The ``'default'`` module provides stubs to 
    enable testing/use on systems with no job management software. If ``PRISMS_JOBS_SOFTWARE``
    is set to any other value, it is treated as the name of a Python module containing 
    a custom interface which ``prisms_jobs`` will attempt to import and use.

- ``PRISMS_JOBS_UPDATE``: 

    If unset or set to ``'default'``, the ``pstat`` script 
    will attempt to update the status of all jobs that are not yet complete (``'C'``). 
    For systems with multiple-clusters-same-home, this may be set to ``'check_hostname'`` 
    and ``pstat`` will only attempt to update the status of jobs that are not yet 
    complete (``'C'``) and have matching hostname, as determined by ``socket.gethostname()``.

