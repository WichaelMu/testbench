import os

from datetime import datetime

from functional import pseq, seq

import py_log_event_module as lem
import rule_engine as ren

import cohorts_lookup_table
import dscore as dsc

import sys
sys.path.append (F'{os.environ['DITLOC']}/tf-data-plane-copt/contrib/src/lambda/student_cohorts_common_data/')
import evaluation_and_persistence as eap

PROGRAM_NAME = 'rule-engine'

def main ():
    event = dsc.load_json ('rules/input.json')
    result = eap.run_rules ('', event, should_persist = True)

    tags = result['tags']
    print (tags)

if (__name__ == '__main__'):
    main ()
