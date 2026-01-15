import os
from datetime import datetime
import logging
from ulid import monotonic as ulid

RUNNING_FROM_LAMBDA = False;
"""True if the current version is being executed in a Lambda environment. False if this code is a local debug version."""
LOG_TRACES_ONLY = False;
FORCE_COLOURISE = False;
ENABLE_PRINTING = True;

logger = logging.getLogger ()

traces: list[dict] = []
service_name = "Default Service Name"

def lambda_log (message, verbosity: int, prefix, force_colourise):
    if (not ENABLE_PRINTING):
        return
    if (LOG_TRACES_ONLY):
        return

    if (not RUNNING_FROM_LAMBDA or force_colourise or FORCE_COLOURISE):
        suffix = "\033[0m" if len(prefix) > 0 else ""
        print (F'{prefix}{message}{suffix}')
    else:
        logging.log (verbosity, message)

# 'logging' has no TRACE level. Use DEBUG instead...
def dtrace (message, force_colourise=False):
    lambda_log (message, logging.DEBUG, '', force_colourise)
def debug (message, force_colourise=False):
    lambda_log (message, logging.DEBUG, '', force_colourise)
def dinfo (message, force_colourise=False):
    lambda_log (message, logging.INFO, '\033[32m', force_colourise)
def dwarn (message, force_colourise=False):
    lambda_log (message, logging.WARNING, '\033[33m', force_colourise)
def derr (message, force_colourise=False):
    lambda_log (message, logging.ERROR, '\033[31m', force_colourise)
def dcrit (critical, force_colourise=False):
    lambda_log (critical, logging.CRITICAL, '\033[1m\033[31m', force_colourise)

# Local Lambda Only...
def dmess (message, force_colourise=False):
    lambda_log (message, logging.INFO, '\033[32m', force_colourise)
def dspec (message, force_colourise=False):
    lambda_log (message, logging.INFO, '\033[36m', force_colourise)

class Verbosity:
    TRACE     = 0
    DEBUG     = 1
    INFO      = 2
    NOTICE    = 4
    WARN      = 8
    ERROR     = 16
    CRITICAL  = 32
    ALERT     = 64
    EMERGENCY = 128

    # Local Verbosities.
    MESS      = 256
    SPEC      = 512

class Status:
    START    = "START"
    END      = "END"
    CONTINUE = "CONTINUE"
    SUCCESS  = "SUCCESS"
    FAILURE  = "FAILURE"
    WARNING  = "WARNING"
    ABORT    = "ABORT"

verbosity_map = {
    Verbosity.TRACE:     lambda message,   with_colour: dtrace (message, with_colour),
    Verbosity.DEBUG:     lambda message,   with_colour: debug  (message, with_colour),
    Verbosity.INFO:      lambda message,   with_colour: dinfo  (message, with_colour),
    Verbosity.WARN:      lambda warning,   with_colour: dwarn  (warning, with_colour),
    Verbosity.ERROR:     lambda error,     with_colour: derr   (error, with_colour),
    Verbosity.CRITICAL:  lambda critical,  with_colour: dcrit  (critical, with_colour),
    Verbosity.ALERT:     lambda alert,     with_colour: dcrit  (alert, with_colour),     # Identical to CRITICAL
    Verbosity.EMERGENCY: lambda emergency, with_colour: dcrit  (emergency, with_colour), #
    Verbosity.MESS:      lambda message,   with_colour: dmess  (message, with_colour),
    Verbosity.SPEC:      lambda special,   with_colour: dspec  (special, with_colour),
}
"""Delegate Mapping for Logging with Verbosity."""

verbosity_to_level = {
    Verbosity.TRACE     : "TRACE",
    Verbosity.DEBUG     : "DEBUG",
    Verbosity.INFO      : "INFO",
    Verbosity.NOTICE    : "NOTICE",
    Verbosity.WARN      : "WARN",
    Verbosity.ERROR     : "ERROR",
    Verbosity.CRITICAL  : "CRITICAL",
    Verbosity.ALERT     : "ALERT",
    Verbosity.EMERGENCY : "EMERGENCY"
}

start_time = datetime.now ()

def register_starting_time ():
    global start_time
    start_time = datetime.now ()
    return start_time

# Cannot exceed 15 minutes for a Lambda Function.
def delta_time (as_dt = False):
    return str (datetime.now () - start_time) if not as_dt else (datetime.now () - start_time)

def generate_ulid_now () -> str:
    """Generates a new ULID based on the time of this function invocation."""
    return str (ulid.from_timestamp (start_time))

def set_service_name (svc_name):
    global service_name
    service_name = svc_name

def init_dbg (svc_name, logger_level=logging.INFO):
    logger.setLevel (logger_level)
    set_service_name (svc_name)
    st = register_starting_time ()
    ul = generate_ulid_now ()

    return ul, st

def trace_meta (code, version, harv_year, epoch, updated_by) -> dict:
    return {
        "courseCode"  : code,
        "version"     : version,
        "harvestYear" : harv_year,
        "epoch"       : epoch,
        "updatedBy"   : updated_by
    }

def append_epoch (epoch, existing_metadata):
    if (not epoch):
        return existing_metadata

    epoch_seconds = epoch
    if (isinstance (epoch_seconds, datetime)):
        epoch_seconds = epoch.timestamp ()

    return trace_meta (existing_metadata["courseCode"],
                       existing_metadata["version"],
                       existing_metadata["harvestYear"],
                       epoch_seconds,
                       existing_metadata["updatedBy"]
                       )

def iso_8601 ():
    import pytz
    aest = pytz.timezone ('Australia/Sydney')
    return str (datetime.now ().astimezone (aest).isoformat ())

# This is here for interop and versatility in naming functions.
def log_msg (ulid, tracepoint, tracemessage, status, action, metadata: dict|None=None, verbosity=Verbosity.INFO):
    trace (ulid, tracepoint, tracemessage, status, action, metadata, verbosity, False)

# Trace log.
def trace (ulid, tracepoint, tracemessage, status, action, metadata: dict|None=None, verbosity=Verbosity.INFO, force_colourise=False):
    trace_body = {
        "createdAt"   : iso_8601 (),
        "referenceId" : ulid,
        "env"         : 'testbench',
        "svc"         : service_name,
        "tracepoint"  : tracepoint,
        "message"     : tracemessage,
        "status"      : status,
        "level"       : verbosity_to_level[verbosity],
        "action"      : action,
        "elapsedTime" : delta_time (),
    }

    if (metadata):
        trace_body["metadata"] = metadata

    # Restrict Logging to this function, if LOG_TRACES_ONLY = True.
    global LOG_TRACES_ONLY
    t_log_traces_only = LOG_TRACES_ONLY
    LOG_TRACES_ONLY = False

    verbosity_map[verbosity] (trace_body, force_colourise)

    LOG_TRACES_ONLY = t_log_traces_only

    traces.append (trace_body)

def latest_trace () -> dict:
    return traces[-1] if len (traces) > 0 else {}
