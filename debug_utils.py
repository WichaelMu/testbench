import logging

RUNNING_FROM_LAMBDA = False;
"""True if the current version is being executed in a Lambda environment. False if this code is a local debug version."""

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_log(message, verbosity: int, prefix=''):
    if (RUNNING_FROM_LAMBDA):
        logging.log(verbosity, message)
    else:
        suffix = "\033[0m" if len(prefix) > 0 else ""
        print (F'{prefix}{message}{suffix}')

def debug(message):
    lambda_log (message, logging.INFO)
def dwarn(message):
    lambda_log (message, logging.WARNING, '\033[33m')
def derr(message):
    lambda_log (message, logging.ERROR, '\033[31m')
def dmess(message):
    lambda_log (message, logging.INFO, '\033[32m')
def dspec(message):
    lambda_log (message, logging.INFO, '\033[36m')
def dcrit (critical):
    lambda_log (critical, logging.CRITICAL, '\033[1m\033[31m')
