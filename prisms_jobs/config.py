"""Configuration"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

import imp
import json
import os
import six
import socket
import warnings
from distutils.spawn import find_executable

import prisms_jobs

__settings = None
__software = None
__write_submit_script = None
__update_selection_method = None

_IMPORT_WARNING_MSG = """\
prisms_jobs does not detect any job management software
and the 'PRISMS_JOBS_SOFTWARE' environment variable is not set.
"""

def detect_software():
    """
    Detect installed job management software

    Returns:
        A string naming the job management software, or None. Possibilities are:

            * 'torque' - detected via 'qsub'
            * 'slurm' - detected via 'sbatch'
    """
    if find_executable('qsub') is not None:
        return 'torque'
    elif find_executable('sbatch') is not None:
        return 'slurm'
    else:
        return None

def set_software(software_name=None):
    """
    Import interface with job management software as module named ``prisms_jobs.software``

    Args:
        software_name (str, optional, default=None):

            ===================    =======================================================
            'torque'               TORQUE
            'slurm'                SLURM
            <other_module>         The name of an existing findable python module
            None or 'default'      Empty stub, does nothing
            ===================    =======================================================

    Raises:
        prisms_jobs.JobDBError: If software_name is unrecognized

    """
    if software_name is None:
        software_name = 'default'
    if software_name.lower() == 'default':
        import prisms_jobs.interface.default as software
    elif software_name.lower() == 'torque':
        import prisms_jobs.interface.torque as software
    elif software_name.lower() == 'slurm':
        import prisms_jobs.interface.slurm as software
    else:
        try:
            f, filename, description = imp.find_module(software_name)
            try:
                software = imp.load_module(software_name, f, filename, description)
            finally:
                if f:
                    f.close()
        except:
            raise Exception('Unrecognized \'software\': ' + software_name)
    global __software
    __software = software

def software():
    """The job management software interface module"""
    if __software is None:
        configure()
    return __software


def _default_update_selection(curs):
    """Select jobs with jobstatus!='C'"""
    curs.execute("SELECT jobid FROM jobs WHERE jobstatus!='C'")

def _check_hostname_update_selection(curs):
    """Select jobs with jobstatus!='C' and matching hostname"""
    hostname = socket.gethostname()

    # Parse our hostname so we can only select jobs from THIS host
    #   Otherwise, if we're on a multiple-clusters-same-home setup,
    #   we may incorrectly update jobs from one cluster onto the other
    m = re.search(r"(.*?)(?=[^a-zA-Z0-9]*login.*)", hostname)   #pylint: disable=invalid-name
    if m:
        hostname_regex = m.group(1) + ".*"
    else:
        hostname_regex = hostname + ".*"

    curs.execute("SELECT jobid FROM jobs WHERE jobstatus!='C' AND hostname REGEXP ?",
                 (hostname_regex, ))


def set_update_selection_method(update_method=None):
    """Enable customization of which jobs are selected for JobDB.update()

    Args:
        update_method (str, optional):

            ===================    =======================================================
            'default' (or None)    Select jobs with jobstatus != 'C'
            'check_hostname'       Select jobs with jobstatus != 'C' and matching hostname
            ===================    =======================================================

    Raises:
        prisms_jobs.JobsError: For unexpected value.
    """
    global __update_selection_method
    if update_method is None:
        __update_selection_method = _default_update_selection
    elif update_method.lower() == 'default':
        __update_selection_method = _default_update_selection
    elif update_method.lower() == 'check_hostname':
        __update_selection_method = _check_hostname_update_selection
    else:
        raise JobsError('Unrecognized update_method: ' + update_method)

def update_selection_method():
    """The jobdb update selection method function"""
    if __update_selection_method is None:
        configure()
    return __update_selection_method

def set_write_submit_script(write_submit_script=None):
    """If true, write submit script to file and then submit job; else submit via command line."""
    global __write_submit_script
    if __write_submit_script is None:
        __write_submit_script = write_submit_script
    return __write_submit_script

def write_submit_script():
    """If true, write submit script to file and then submit job; else submit via command line."""
    if __write_submit_script is None:
        configure()
    return __write_submit_script


def config_dir():
    """Return configuration directory"""
    return os.environ.get('PRISMS_JOBS_DIR', os.path.join(os.environ['HOME'], '.prisms_jobs'))

def config_path(dir=None):
    """Return configuration file location"""
    if dir is None:
        dir = config_dir()
    return os.path.join(dir, 'config.json')

def default_settings(dir=None):
    """Default configuration dictionary

    Args:
        dir (str): Location of the directory storing the config.json file.

    Notes:
        See configure for details.

    Returns:
        Dict with configuration settings.
    """
    if dir is None:
        dir = config_dir()
    return {
        'dbpath': os.path.join(dir, 'jobs.db'),
        'software': detect_software(),
        'write_submit_script': False,
        'update_method': 'default'
    }

def read_config(dir=None):
    """Read configuration file.

    Note:
        Will create with default values if not existing.

    Args:
        dir (str, optional): Location of the directory storing the config.json file.
            The default location is ``$PRISMS_JOBS_DIR/.prisms_jobs``, where
            the environment variable ``PRISMS_JOBS_DIR``=``$HOME`` if not set.

    Returns:
        Dict with configuration settings.
    """
    if dir is None:
        dir = config_dir()
    if not os.path.exists(dir):
        print("Creating config directory:", dir)
        os.mkdir(dir)
    configpath = config_path(dir)
    if not os.path.exists(configpath):
        settings = default_settings(dir)
        write_config(dir, settings)
        return settings
    else:
        with open(configpath, 'r') as f:
            try:
                return json.load(f)
            except Exception as e:
                print("Could not read", configpath + ":")
                print("-------------")
                print(f.read())
                print("-------------")
                print("Delete to restart from defaults\n")
                raise e

def write_config(dir=None, settings=None):
    """Write current configuration settings to file.

    Args:
        dir (str, optional): Location of the directory storing the config.json file.
            The default location is ``$PRISMS_JOBS_DIR/.prisms_jobs``, where
            the environment variable ``PRISMS_JOBS_DIR``=``$HOME`` if not set.
        settings (dict, optional): Settings to write to config.json file. Uses
            current settings by default.

    Returns:
        Dict with configuration settings.
    """
    if dir is None:
        dir = config_dir()
    if settings is None:
        settings = __settings
    with open(config_path(dir), 'w') as f:
        # for python2/3 compatibility don't use json.dump:
        f.write(json.dumps(settings, indent=2, ensure_ascii=False))

def settings():
    """Settings dictionary"""
    if __settings is None:
        configure()
    return __settings

def dbpath():
    """Settings dictionary"""
    if __settings is None:
        configure()
    return __settings['dbpath']

def configure(settings=None):
    """Set configuration

    Sets the global configuration settings dictionary. Options are:

        * 'dbpath': (str)
            Location of the SQLite jobs database.
        * 'software': (str)
            Which job management software to use. See set_software for options.
        * 'write_submit_script': (bool, default=False)
            If true, write submit script to file and then submit job; otherwise
            submit via command line.
        * 'update_method': (str, default='default')
            Controls which jobs are updated when JobDB.update() is called.
            See set_update_selection_method for options.

    The values are then used to update:
        * software: Module used to interface with job submission software
        * update_selection_method: Function used by JobDB.update()

    Args:
        config_dict (dict, optional): All configuration settings. Default reads
            configuration settings using read_config.
    """
    if settings is None:
        settings = read_config()
    global __settings
    __settings = settings
    set_software(__settings['software'])
    set_write_submit_script(__settings['write_submit_script'])
    set_update_selection_method(__settings['update_method'])
