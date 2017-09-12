.. overview.rst

Overview
========

When submitted through the ``prisms_jobs`` Python package or the included scripts, 
cluster jobs are stored in a SQLite jobs database. This allows for convenient 
monitoring and searching of submitted jobs. 

It is often necessary to submit multiple jobs until a particular task is complete,
whether due to walltime or other limitations. ``prisms-jobs`` distinguishes and 
tracks both individual "jobstatus" ('R', 'Q', 'C', 'E', etc.) and "taskstatus".
Jobs marked as 'auto' can be automatically or easily resubmitted until the 
"taskstatus" is "Complete".

Possible values for "taskstatus" are:

+------------+------------------------------------------------+
|"Complete"  |Job and task are complete.                      |
+------------+------------------------------------------------+
|"Incomplete"|Job or task are incomplete.                     |
+------------+------------------------------------------------+
|"Continued" |Job is complete, but task was not complete.     |
+------------+------------------------------------------------+
|"Check"     |Non-auto job is complete and requires user      |
|            |input for status.                               |
+------------+------------------------------------------------+
|"Error:.*"  |Some kind of error was noted.                   |
+------------+------------------------------------------------+
|"Aborted"   |The job and task have been aborted.             |
+------------+------------------------------------------------+


Jobs are marked 'auto' either by submitting through the python class ``prisms_jobs.Job`` 
with the attribute ``auto=True``, or by submitting a PBS script which contains 
the line ``#auto=True`` using the included ``psub`` script.  

Jobs can be monitored using the command line program ``pstat``. All 'auto' jobs 
which have stopped can be resubmitted using ``pstat --continue``. In this case, 
'continuation_jobid' is set with the jobid for the next job in the series of jobs
comprising a task.

Example screen shot:

::

    $ pstat


    Tracked:
    JobID        JobName                  Nodes Procs     Walltime S      Runtime Task                     A ContJobID   
    ------------ ------------------------ ----- ----- ------------ - ------------ ------------------------ - ------------
    11791024     STDIN                      1     1     0:01:00:00 Q            - Incomplete               1 -           
    11791025     STDIN                      1     1     0:01:00:00 Q            - Incomplete               1 -           


    Untracked:
    JobID        JobName                  Nodes Procs     Walltime S      Runtime Task                     A ContJobID   
    ------------ ------------------------ ----- ----- ------------ - ------------ ------------------------ - ------------
    11791026     taskmaster                 1     1     0:01:00:00 W   0:01:00:00 Untracked                0 -           

Additionally, when scheduling periodic jobs is not allowed other ways, the 
``taskmaster`` script can fully automate this process. ``taskmaster`` executes 
``pstat --continue`` and then resubmits itself to execute again periodically.

A script marked 'auto' should check itself for completion and when reached execute 
``pstat --complete $PBS_JOBID --force`` in bash, or ``prisms_jobs.complete_job()`` 
in Python. If an 'auto' job script does not set its taskstatus to "Complete" it 
may continue to be resubmitted indefinitely.    

Jobs not marked 'auto' are shown with the status "Check" in ``pstat`` until the user 
marks them as "Complete".

