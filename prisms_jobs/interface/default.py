""" Stub to use when running on a machine without job management software """
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

### Required ###

NAME = 'default'

def job_id(all=False, name=None):       #pylint: disable=redefined-builtin
    """Raise exception"""
    raise Exception("No job management software found")

def job_rundir(jobid):
    """Raise exception"""
    raise Exception("No job management software found")

def job_status(jobid=None):
    """Raise exception"""
    raise Exception("No job management software found")

def submit(substr):
    """Raise exception"""
    raise Exception("No job management software found")

def delete(jobid):
    """Raise exception"""
    raise Exception("No job management software found")

def hold(jobid):
    """Raise exception"""
    raise Exception("No job management software found")

def release(jobid):
    """Raise exception"""
    raise Exception("No job management software found")

def alter(jobid, arg):
    """Raise exception"""
    raise Exception("No job management software found")

def read(job, qsubstr):
    """Raise exception"""
    raise Exception("No job management software found")

