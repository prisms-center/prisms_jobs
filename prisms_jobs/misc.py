""" Misc functions for interacting between the OS and the prisms_jobs """
from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import *

import datetime
import os
import pwd
import subprocess
import sys

def _set_encoding(encoding=None):
    if encoding is None:
        if sys.stdout.encoding is not None:
            return sys.stdout.encoding
        else:
            return 'utf-8'
    else:
        return encoding

def _decode(val, encoding=None):
    try:
        if isinstance(val, bytes):
            return val.decode(_set_encoding(encoding))
        else:
            return val
    except Exception as e:
        print("Exception in prisms_jobs.misc._decode:", e)
        print("val:", val)
        print("sys.stdout.encoding:", sys.stdout.encoding)
        raise e
        
def run(cmd, input=None, stdin=None, encoding=None):
    """Run subprocess and return stdout, stderr as text, returncode as int
    
    Args:
        cmd (List[str]): Command to run as subprocess
        input (str): Data to be sent to child process
        stdin (stream): Use subprocess.PIPE to pass data via stdin
        encoding (str, optional): Encoding to use to decode stdout, stderr. By
            default, uses sys.stdout.encoding if available, else 'utf-8'.
    
    Returns:
        (stdout, stderr, returncode): With stdout and stderr as strings, and 
            returncode as int
    """
    try:
        p = subprocess.Popen(cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        encoding = _set_encoding(encoding)
        if input is not None:
            input = bytearray(input, encoding=encoding)
        stdout, stderr = p.communicate(input=input)
        return (_decode(stdout, encoding), _decode(stderr, encoding), p.returncode)
    except Exception as e:
        print("Exception in prisms_jobs.misc.run:", e)
        print("cmd:", cmd)
        print("input:", input)
        print("stdin:", stdin)
        print("encoding:", encoding)
        print("sys.stdout.encoding:", sys.stdout.encoding)
        raise e

def getlogin():
    """Returns os.getlogin(), else os.environ["LOGNAME"], else "?" """
    try:
        return pwd.getpwuid(os.getuid())[0]
    except:
        return os.environ.get("LOGNAME","?")

def seconds(walltime):
    """Convert [[[DD:]HH:]MM:]SS to hours"""
    wtime = walltime.split(":")
    if len(wtime) == 1:
        return float(wtime[0])
    elif len(wtime) == 2:
        return float(wtime[0])*60.0 + float(wtime[1])
    elif len(wtime) == 3:
        return float(wtime[0])*3600.0 + float(wtime[1])*60.0 + float(wtime[2])
    elif len(wtime) == 4:
        return (float(wtime[0])*24.0*3600.0
                + float(wtime[0])*3600.0
                + float(wtime[1])*60.0
                + float(wtime[2]))
    else:
        print("Error in walltime format:", walltime)
        sys.exit()

def hours(walltime):
    """Convert [[[DD:]HH:]MM:]SS to hours"""
    wtime = walltime.split(":")
    if len(wtime) == 1:
        return float(wtime[0])/3600.0
    elif len(wtime) == 2:
        return float(wtime[0])/60.0 + float(wtime[1])/3600.0
    elif len(wtime) == 3:
        return float(wtime[0]) + float(wtime[1])/60.0 + float(wtime[2])/3600.0
    elif len(wtime) == 4:
        return (float(wtime[0])*24.0
                + float(wtime[0])
                + float(wtime[1])/60.0
                + float(wtime[2])/3600.0)
    else:
        print("Error in walltime format:", walltime)
        sys.exit()

def strftimedelta(seconds):     #pylint: disable=redefined-outer-name
    """Convert seconds to D+:HH:MM:SS"""
    seconds = int(seconds)

    day_in_seconds = 24.0*3600.0
    hour_in_seconds = 3600.0
    minute_in_seconds = 60.0

    day = int(seconds/day_in_seconds)
    seconds -= day*day_in_seconds

    hour = int(seconds/hour_in_seconds)
    seconds -= hour*hour_in_seconds

    minute = int(seconds/minute_in_seconds)
    seconds -= minute*minute_in_seconds

    return str(day) + ":" + ("%02d" % hour) + ":" + ("%02d" % minute) + ":" + ("%02d" % seconds)

def exetime(deltatime):
    """Get the exetime string for the PBS '-a'option from a [[[DD:]MM:]HH:]SS string

       exetime string format: YYYYmmddHHMM.SS
    """
    return (datetime.datetime.now()
            +datetime.timedelta(hours=hours(deltatime))).strftime("%Y%m%d%H%M.%S")
