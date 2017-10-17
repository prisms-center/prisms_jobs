.. config.rst

Configuration
=============

Some configuration is possible:

- ``PRISMS_JOBS_DIR``: (optional, default=``$HOME/.prisms_jobs``) 

    The jobs database is stored at ``$PBS_JOB_DIR/jobs.db``.

- ``PRISMS_JOBS_DIR/config.json``: 

    Automatically generated JSON configuration file storing settings:
    
    - ``"dbpath"``: (str) 
    
        The location of the SQLite jobs database.
    
    - ``"software"``: (str) 
    
        The job submission software interface to use. ``"torque"`` or ``"slurm"``
        is automatically detected if present.
        
        +-------------------+------------------------------------------------+
        |"torque"           |TORQUE                                          |
        +-------------------+------------------------------------------------+
        |"slurm"            |Slurm                                           |
        +-------------------+------------------------------------------------+
        |"default" (or null)|Empty stub, does nothing                        |
        +-------------------+------------------------------------------------+
        |other              |The name of an existing findable python module  |
        |                   |implementing an interface                       |
        +-------------------+------------------------------------------------+

    - ``"write_submit_script"``: (bool, optional, default=false) 
    
        If ``true``, submit jobs by first writing a submit script file and then 
        submitting it. Otherwise, by default, the job is submitted via the command 
        line.
    
    - ``"update_method"``: (str, optional, default="default")
        
        Controls which jobs are updated when JobDB.update() is called.
        
        +-------------------+------------------------------------------------+
        |"default" (or null)| Select jobs with jobstatus != 'C'              |
        +-------------------+------------------------------------------------+
        |"check_hostname"   | Select jobs with jobstatus != 'C' and matching |
        |                   | hostname                                       |
        +-------------------+------------------------------------------------+
    
    - ``"taskmaster_job_kwargs"``: (JSON object, optional)
    
        Holds options for the `taskmaster`_ job. Defaults are:
        
        +-----------+------------------------------------------------+
        |'name'     | "taskmaster"                                   |
        +-----------+------------------------------------------------+
        |'account'  | "prismsprojectdebug_fluxoe"                    |
        +-----------+------------------------------------------------+
        |'nodes'    | "1"                                            |
        +-----------+------------------------------------------------+
        |'ppn'      | "1"                                            |
        +-----------+------------------------------------------------+
        |'walltime' | "1:00:00"                                      |
        +-----------+------------------------------------------------+
        |'pmem'     | "3800mb"                                       |
        +-----------+------------------------------------------------+
        |'qos'      | "flux"                                         |
        +-----------+------------------------------------------------+
        |'queue'    | "fluxoe"                                       |
        +-----------+------------------------------------------------+
        |'message'  | null                                           |
        +-----------+------------------------------------------------+
        |'email'    | null                                           |
        +-----------+------------------------------------------------+
        |'priority' | "-1000"                                        |
        +-----------+------------------------------------------------+
        |'command'  | "rm taskmaster.o*; rm taskmaster.e*\\n"        |
        +-----------+------------------------------------------------+
        |'auto'     | false                                          |
        +-----------+------------------------------------------------+
        
        Additionally, the ``'exetime'`` is set based on the ``--delay`` 
        commandline argument and the commandline invocation used to launch 
        ``taskmaster`` is appended to ``'command'``.

.. _taskmaster: scripts/taskmaster.html

