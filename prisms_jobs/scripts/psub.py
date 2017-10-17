"""Submit jobs and store in the jobs database"""
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

# This script submits a PBS script, as with 'qsub script.sh'
# and adds the job to the prisms_jobs.JobDB job database

import sys
import argparse

import prisms_jobs

parser = argparse.ArgumentParser(description='Submit a script and add to `prisms-jobs` database')
parser.add_argument('scriptname', type=str, help='Submit script')

def main():
    args = parser.parse_args()

    substr = open(args.scriptname, 'r').read()
    job = prisms_jobs.Job(substr=substr)
    job.submit()

if __name__ == "__main__":
    main()
