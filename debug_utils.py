import os
import logging
from datetime import datetime
from ulid import monotonic as ulid
from api_common import get_envar_ENV as getenv

RUNNING_FROM_LAMBDA = False;
"""True if the current version is being executed in a Lambda environment. False if this code is a local debug version."""

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_log(message, verbosity: int, prefix, force_colourise):
    if (not RUNNING_FROM_LAMBDA or force_colourise):
        suffix = "\033[0m" if len(prefix) > 0 else ""
        print (F'{prefix}{message}{suffix}')
    else:
        logging.log(verbosity, message)

def debug(message, force_colourise=False):
    lambda_log (message, logging.INFO, '', force_colourise)
def dwarn(message, force_colourise=False):
    lambda_log (message, logging.WARNING, '\033[33m', force_colourise)
def derr(message, force_colourise=False):
    lambda_log (message, logging.ERROR, '\033[31m', force_colourise)
def dmess(message, force_colourise=False):
    lambda_log (message, logging.INFO, '\033[32m', force_colourise)
def dspec(message, force_colourise=False):
    lambda_log (message, logging.INFO, '\033[36m', force_colourise)
def dcrit (critical, force_colourise=False):
    lambda_log (critical, logging.CRITICAL, '\033[1m\033[31m', force_colourise)

class Verbosity:
    INFO     = 1
    WARN     = 2
    ERROR    = 4
    MESS     = 8
    SPEC     = 16
    CRITICAL = 32

class Status:
    START    = "START"
    END      = "END"
    CONTINUE = "CONTINUE"
    SUCCESS  = "SUCCESS"
    FAILURE  = "FAILURE"

verbosity_map = {
    Verbosity.INFO:     lambda message,  with_colour: debug (message, with_colour),
    Verbosity.WARN:     lambda warning,  with_colour: dwarn (warning, with_colour),
    Verbosity.ERROR:    lambda error,    with_colour: derr  (error, with_colour),
    Verbosity.MESS:     lambda message,  with_colour: dmess (message, with_colour),
    Verbosity.SPEC:     lambda special,  with_colour: dspec (special, with_colour),
    Verbosity.CRITICAL: lambda critical, with_colour: dcrit (critical, with_colour),
}
"""Delegate Mapping for Logging with Verbosity."""

def generate_ulid_now() -> str:
    """Generates a new ULID based on the time of this function invocation."""
    begin = datetime.now()
    return str (ulid.from_timestamp(begin))

def trace_meta (code, version, harv_year, epoch, updated_by) -> dict:
    return {
        "CourseCode"  : code,
        "Version"     : version,
        "HarvestYear" : harv_year,
        "Epoch"       : epoch,
        "UpdatedBy"   : updated_by
    }

def trace(ulid, tracepoint, tracemessage, status, action, metadata: dict|None=None, verbosity: int=Verbosity.INFO, force_colourise=False):
    trace_body = {
        "ReferenceId" : ulid,
        "Tracepoint"  : tracepoint,
        "Message"     : tracemessage,
        "Status"      : status,
        "Action"      : action,
        "Environment" : os.environ[getenv()],
    }

    if (metadata):
        trace_body["Metadata"] = metadata

    verbosity_map[verbosity] (trace_body, force_colourise)