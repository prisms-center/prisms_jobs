"""Print or modify PRISMS_JOBS job and task status."""
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

### External ###
# import sys
import argparse

### Local ###
import prisms_jobs  #pylint: disable=import-error

# input parser

DESC = \
"""
Print or modify `prisms-jobs` job and task status.


By default, 'pstat' prints status for select jobs. Jobs are
selected by listing jobids or using --all, --range, or
--recent, optionally combined with --active. Running 'pstat'
with no selection is equivalent to selecting '--all --active'.
The default display style is a summary list. Other options are
--full or --series.

Using one of --complete, --continue, --error, --abort, or
--delete modifies status instead of printing. User
confirmation is required before a modification is applied,
unless the --force option is given.


Job status is as given by `prisms-jobs` for a single job ('C', 'R',
'Q', etc.).

Task status is user-defined and defines the status of a single
job within a possible series of jobs comprising some task.
'Auto' jobs may be re-submitted with the --continue option.

Jobs are marked 'auto' either by submitting through the python
class ``prisms_jobs.Job`` with the attribute ``auto=True``, or
by submitting a script which contains the line ``#auto=True``
via ``psub``.

Possible values for task status are:

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
"""

def make_parser():
    parser = argparse.ArgumentParser(description=DESC,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('job', metavar='JOBID', type=str, nargs='*',
                        help='Job IDs to query or operate on')

    style = parser.add_mutually_exclusive_group()
    style.add_argument('-f', '--full', default=False, action='store_true',
                       help='List all fields instead of summary')
    style.add_argument('-s', '--series', default=False, action='store_true',
                       help='List all fields grouped by continuation jobs')

    group = parser.add_mutually_exclusive_group()
    select = parser.add_mutually_exclusive_group()

    select.add_argument('-a', '--all', default=False, action='store_true',
                        help='Select all jobs in database')
    select.add_argument('--range', metavar=('MINID', 'MAXID'), type=str, nargs=2,
                        help='A range of Job IDs (inclusive) to query or operate on')
    select.add_argument('--recent', metavar='DD:HH:MM:SS', type=str, nargs=1,
                        help='Select jobs created or modified within given amout of time')
    select.add_argument('--regex', metavar=('KEY', 'REGEX'), type=str, nargs=2,
                        help='Select jobs where the value of column \'KEY\' matches\
                              the regular expression \'REGEX\'.')

    parser.add_argument('--active', default=False, action='store_true',
                        help='Select active jobs only. May be combined with --range and --recent')

    group.add_argument('--complete', default=False, action='store_true',
                       help='Mark jobs as \'Complete\'')
    group.add_argument('--continue', dest="cont", default=False, action='store_true',
                       help='Re-submit auto jobs')
    group.add_argument('--reset', default=False, action='store_true',
                       help='Mark job as \'Incomplete\'')
    group.add_argument('--abort', default=False, action='store_true',
                       help='Call qdel on job and mark as \'Aborted\'')
    group.add_argument('--error', metavar='ERRMSG', type=str, help='Add error message.')
    group.add_argument('--delete', default=False, action='store_true',
                       help='Delete jobs from database. Aborts jobs that are still running.')
    group.add_argument('--key', type=str, nargs=1,
                       help='Output data corresponding to \'key\' for selected jobs.')

    parser.add_argument('--force', default=False, action='store_true',
                        help='Modify jobs without user confirmation')

    return parser


def main(): #pylint: disable=missing-docstring, too-many-statements

    # functions

    def select_job(args):   #pylint: disable=redefined-outer-name
        """ Select which jobs to operate on """
        if args.all:
            job = db.select_all_id()
        elif args.range:
            job = db.select_range_id(args.range[0], args.range[1])
        elif args.recent:
            job = db.select_recent_id(args.recent[0])
        elif args.regex:
            job = db.select_regex_id(args.regex[0], args.regex[1])
        elif args.job != []:
            job = args.job
        else:
            args.active = True
            job = db.select_all_id()

        if args.active:
            if job == []:
                return job
            active = db.select_all_active_id()
            active_job = []
            for j in job:
                if j in active:
                    active_job.append(j)
            return active_job
        else:
            return job


    def operate(args, check_eligibility, operation, summary_msg, prompt_msg, action_msg):   #pylint: disable=redefined-outer-name, too-many-arguments
        """ Perform an operation on some jobs.

            Args:
                args:                   Command line input from argparse

                check_eligibility:      A function that checks if job is eligible for the
                                        requested operation. Expects signature similar to
                                        JobDB.eligible_for_X functions.

                operation:              The function to perform on a sqlite3.Row

                summary_msg:            Display a message before the list of jobs the
                                        operation will be performed on.

                prompt_msg:             Message displayed to prompt user to confirm the
                                        operation.

                action_msg:             Message displayed as operation is performed
        """


        # select jobs
        selection_id = select_job(args)

        # filter to find eligible jobs
        job = []
        for j in selection_id:
            try:
                selected_job = db.select_job(j)
                eligible, id, msg = check_eligibility(selected_job) #pylint: disable=redefined-builtin, invalid-name
                if eligible:
                    job.append(selected_job)
                else:
                    print(id + ":", msg)
            except prisms_jobs.JobDBError as e: #pylint: disable=invalid-name
                print(e)


        # print jobs to operate on:
        print(summary_msg)

        db.print_header()

        for j in job:
            db.print_job(job=j, series=args.series)
        answer = None

        if args.force:
            answer = "yes"
        else:
            # prompt user for confirmation
            while answer != "yes" and answer != "no":
                answer = input(prompt_msg)

        # perform operation
        if answer == "yes" and job != []: # or args.select:
            for j in job:
                print(action_msg, j["jobid"])
                operation(job=j)


    def print_data(args):
        """ Print job data """
        # user defined selection (don't show untracked)
        jobid = select_job(args)
        if jobid != []:

            # remove potential duplicates for series
            if args.series:
                seriesid = []
                for j in jobid:
                    series = db.select_series_id(j)
                    if not series[-1] in seriesid:
                        seriesid.append(series[-1])
                jobid = seriesid

            # print rundir
            if args.series:
                for j in jobid:
                    series = db.select_series_id(j)
                    for s in series: #pylint: disable=invalid-name
                        try:
                            job = db.select_job(s)
                            print(s, job[args.key[0]])
                        except prisms_jobs.JobDBError as e: #pylint: disable=invalid-name
                            print(e)
                    print("")
            else:
                for j in jobid:
                    try:
                        job = db.select_job(j)
                        print(j, job[args.key[0]])
                    except prisms_jobs.JobDBError as e: #pylint: disable=invalid-name
                        print(e)


    def print_jobs(args):
        """ Print jobs """
        if args.all and not args.active:
            # 'pstat --all' case
            #    show all and untracked
            db.print_all(full=args.full, series=args.series)
            print('\n')
            db.print_untracked(full=args.full)
        elif (not args.all and not args.range and not args.recent
              and not args.regex and args.job == []):
            # default 'pstat' case with no selection
            #   show active and untracked
            db.print_active(full=args.full, series=args.series)
            print('\n')
            db.print_untracked(full=args.full)
        else:
            # user defined selection (don't show untracked)
            jobid = select_job(args)
            if jobid != []:
                if args.series:
                    seriesid = []
                    for j in jobid:
                        series = db.select_series_id(j)
                        if not series[-1] in seriesid:
                            seriesid.append(series[-1])
                    jobid = seriesid

                if not args.full:
                    db.print_header()
                for j in jobid:
                    try:
                        db.print_job(jobid=j, full=args.full, series=args.series)
                    except prisms_jobs.JobDBError as e: #pylint: disable=invalid-name
                        print(e)

    parser = make_parser()

    args = parser.parse_args()



    # open the Job database
    db = prisms_jobs.JobDB()    #pylint: disable=invalid-name
    db.update()


    # perform an operation, or print jobs
    if args.complete:
        operate(args, \
                db.eligible_to_complete, \
                db.complete_job, \
                "Jobs to be mark completed:", \
                "Are you sure you want to mark the above jobs completed? (yes/no): ", \
                "Marking job complete:")
    elif args.cont:
        operate(args, \
                db.eligible_to_continue, \
                db.continue_job, \
                "Jobs to be continued:", \
                "Are you sure you want to continue the above jobs? (yes/no): ", \
                "Continuing job:")
    elif args.reset:
        operate(args, \
                db.eligible_to_reset, \
                db.reset_job, \
                "Jobs to be reset:", \
                "Are you sure you want to reset the above jobs? (yes/no): ", \
                "Resetting job:")
    elif args.abort:
        operate(args, \
                db.eligible_to_abort, \
                db.abort_job, \
                "Jobs to be aborted:", \
                "Are you sure you want to abort the above jobs? (yes/no): ", \
                "Aborting job:")
    elif args.delete:
        operate(args, \
                db.eligible_to_delete, \
                db.delete_job, \
                "Jobs to be deleted:", \
                "Are you sure you want to delete the above jobs? (yes/no): ", \
                "Deleting job:")
    elif args.error:
        operate(args, \
                db.eligible_to_error, \
                db.error_job, \
                "Jobs to be marked with an error:", \
                "Are you sure you want to mark the above jobs with an error? (yes/no): ", \
                "Marking job with an error:")
    elif args.key:
        print_data(args)
    else:
        print_jobs(args)

    # close the database
    db.close()

if __name__ == "__main__":
    main()
