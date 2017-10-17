"""Automatically resubmit jobs"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

import argparse
import sys
import subprocess
from six import iteritems

import prisms_jobs
from prisms_jobs import config
software = config.software()

def check_for_other():
    jobid = software.job_id(name="taskmaster")
    if not len(jobid):
        return
    tmaster_status = software.job_status(jobid)
    for j in jobid:
        if j != software.job_id() and tmaster_status[j]["jobstatus"] != "C":
            print("A taskmaster is already running. JobID:", j, "  Status:",  tmaster_status[j]["jobstatus"]) 
            sys.exit()

DESC = \
"""
Automatically resubmit jobs.

'taskmaster' submits itself with instructions to be run after an amount of time
specified by --delay (default=15:00). When it runs, it continues all auto
prisms_jobs jobs in the database that are incomplete and then re-submits itself
to execute again after the specified delay.

The specifics of 'taskmaster' submission can be customized by editing the 
'taskmaster_job_kwargs' object in the prisms_jobs configuration file:
``$PRISMS_JOBS_DIR/config.json``.
"""

parser = argparse.ArgumentParser(description=DESC, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-d','--delay', type=str, default="15:00", \
                    help='How long to delay ("[[[DD:]HH:]MM:]SS") between executions.  Default is "15:00".')

group = parser.add_mutually_exclusive_group()
group.add_argument('--hold', action='store_true', help='Place a hold on the currently running taskmaster')
group.add_argument('--release', action='store_true', help='Release the currently running taskmaster')
group.add_argument('--kill', action='store_true', help='Kill the currently running taskmaster')


def taskmaster_job_kwargs(delay, cli_args):

    # default args
    data = {
        'name': "taskmaster",
        'account': "prismsprojectdebug_fluxoe",
        'nodes': "1",
        'ppn': "1",
        'walltime': "1:00:00",
        'pmem': "3800mb",
        'qos': "flux",
        'queue': "fluxoe",
        'message': None,
        'email': None,
        'priority': "-1000",
        'command': "rm taskmaster.o*; rm taskmaster.e*\n",
        'auto': False}
    
    settings = config.settings()
    if 'taskmaster_job_kwargs' not in settings:
        settings['taskmaster_job_kwargs'] = data
        config.configure(settings)
        config.write_config()
    else:
        for key, value in iteritems(settings['taskmaster_job_kwargs']):
            data[key] = value
    
    data['exetime'] = prisms_jobs.misc.exetime(delay)
    data['command'] += "\ntaskmaster " + ' '.join(cli_args)
    
    return data
            

def main():
    args = parser.parse_args()

    if args.hold:
        jobid = software.job_id(name="taskmaster")
        if len(jobid) != 0:
            software.hold(jobid[-1])
    elif args.release:
        jobid = software.job_id(name="taskmaster")
        if len(jobid) != 0:
            software.release(jobid[-1])
    elif args.kill:
        jobid = software.job_id(name="taskmaster")
        if len(jobid) != 0:
            software.alter(jobid[-1], "-a " + prisms_jobs.misc.exetime("10:00:00:00") )
            software.delete(jobid[-1])
    else:
        
        # check if taskmaster already running (besides this one)
        check_for_other()
        
        # continue jobs
        db = prisms_jobs.JobDB()
        db.update()
        db.continue_all()
        db.close()
        
        # submit taskmaster
        print("submit taskmaster")
        j = prisms_jobs.Job(**taskmaster_job_kwargs(args.delay, sys.argv[1:]))
        j.submit(add=False)
        
        #print "submit string:"
        #print j.sub_string()


if __name__ == "__main__":
    main()
