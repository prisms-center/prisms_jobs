.. api/index.rst

prisms_jobs documentation
=========================

prisms_jobs
-----------

.. autosummary::
    :toctree:

    prisms_jobs.Job
    prisms_jobs.JobDB
    prisms_jobs.JobsError
    prisms_jobs.JobDBError
    prisms_jobs.EligibilityError
    prisms_jobs.complete_job
    prisms_jobs.error_job

prisms_jobs.interface
---------------------

.. autosummary::
    :toctree:

    prisms_jobs.interface.torque
    prisms_jobs.interface.slurm
    prisms_jobs.interface.default

prisms_jobs.config
---------------------

.. autosummary::
    :toctree:

    prisms_jobs.config.configure
    prisms_jobs.config.dbpath
    prisms_jobs.config.settings
    prisms_jobs.config.read_config
    prisms_jobs.config.write_config
    prisms_jobs.config.default_settings
    prisms_jobs.config.config_dir
    prisms_jobs.config.config_path
    prisms_jobs.config.update_selection_method
    prisms_jobs.config.set_update_selection_method
    prisms_jobs.config.software
    prisms_jobs.config.set_software
    prisms_jobs.config.detect_software
    
prisms_jobs.misc
----------------

.. autosummary::
    :toctree:

    prisms_jobs.misc.getlogin
    prisms_jobs.misc.seconds
    prisms_jobs.misc.hours
    prisms_jobs.misc.strftimedelta
    prisms_jobs.misc.exetime

prisms_jobs.templates
---------------------

.. autosummary::
    :toctree:

    prisms_jobs.templates.PrismsJob
    prisms_jobs.templates.NonPrismsJob
    prisms_jobs.templates.PrismsPriorityJob
    prisms_jobs.templates.PrismsDebugJob
    prisms_jobs.templates.PrismsSpecialJob

