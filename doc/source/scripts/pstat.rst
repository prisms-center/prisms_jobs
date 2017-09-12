.. scripts/pstat.rst

pstat
=====


Summary
-------


``pstat`` gives command line access to the jobs database. It can be used to:

- List job info by:
  
  - Job id
  - Modification time
  - If still active
  - Database column and regex
    
    - Possible columns can be determined from the ``-f`` output
  
  - Grouped series of continuation jobs, or ungrouped

- Continue (re-submit) 'Auto' jobs
- Mark jobs as 'Complete' or 'Incomplete'
- Abort running jobs
- Add/modify an error message
- Delete jobs from the database (and abort if currently running)
  

Help documentation:
-------------------

.. argparse::
    :filename: scripts/pstat
    :func: make_parser
    :prog: pstat
    
    
