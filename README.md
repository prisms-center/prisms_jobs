prisms-jobs
===========

A Python package and set of scripts used for submitting and managing 
cluster jobs via PBS (TORQUE) or Slurm. 

This code is developed by the PRedictive Integrated Structural Materials Science Center (PRISMS), at the University of Michigan, which is supported by the U.S. Department of Energy, Office of Basic Energy Sciences, Division of Materials Sciences and Engineering under Award #DE-SC0008637, and the Van der Ven group, originally at the University of Michigan and 
currently at the University of California Santa Barbara.


## Overview

When submitted through the ``prisms_jobs`` Python package or the included scripts, 
cluster jobs are stored in a SQLite jobs database. This allows for convenient 
monitoring and searching of submitted jobs. 

It is often necessary to submit multiple jobs until a particular task is complete,
whether due to walltime or other limitations. ``prisms_jobs`` distinguishes and 
tracks both individual "jobstatus" ('R', 'Q', 'C', 'E', etc.) and "taskstatus".
Jobs marked as 'auto' can be automatically or easily resubmitted until the 
"taskstatus" is "Complete".

Possible values for "taskstatus" are:

| Taskstatus | Meaning                                                     |
|------------|-------------------------------------------------------------|
|"Complete"  |Job and task are complete.                                   |
|"Incomplete"|Job or task are incomplete.                                  |
|"Continued" |Job is complete, but task was not complete.                  |
|"Check"     |Non-auto job is complete and requires user input for status. |
|"Error:.*"  |Some kind of error was noted.                                |
|"Aborted"   |The job and task have been aborted.                          |


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
``pstat --complete $PBS_JOBID`` in bash, or ``prisms_jobs.complete_job()`` in Python. If 
an 'auto' job script does not set its taskstatus to "Complete" it may continue 
to be resubmitted indefinitely.    

Jobs not marked 'auto' are shown with the status "Check" in ``pstat`` until the user 
marks them as "Complete".


## Installation from PyPI (todo)

Using ``pip``:

    pip install prisms-jobs

or, to install in your user directory:
   
   	pip install --user prisms-jobs
   
If installing to a user directory, you may need to set your PATH to find the installed scripts. This can be done using:
   
   	export PATH=$PATH:`python -m site --user-base`/bin


## Install using conda (todo)

    conda config --add channels prisms-center
    conda install prisms-jobs


## Installation from source

1. Clone the repository:

        cd /path/to/
        git clone https://github.com/prisms-center/prisms_jobs.git
        cd prisms_jobs

2. Checkout the branch/tag containing the version you wish to install. Latest is ``v3.0.0``:

        git checkout v3.0.0

2. From the root directory of the repository:

        pip install .
   
   or, to install in your user directory:
   
   		pip install --user .
   
   If installing to a user directory, you may need to set your PATH to find the installed scripts. This can be done using:
   
   		export PATH=$PATH:`python -m site --user-base`/bin


## Documentation

See the [docs](todo).


## License

This directory contains the prisms_jobs Python package and related scripts developed 
by the PRISMS Center at the University of Michigan, Ann Arbor, USA, and
the Van der Ven group, originally at the University of Michigan and 
currently at the University of California Santa Barbara.

(c) 2014 The Regents of the University of Michigan
(c) 2015 The Regents of the University of California

PRISMS Center http://prisms.engin.umich.edu 
contact: casm-developers@lists.engr.ucsb.edu

This code is a free software; you can use it, redistribute it,
and/or modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either version
2.1 of the License, or (at your option) any later version.

Please see the file LICENSE for details.


