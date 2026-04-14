import os

import rule_engine as ren
import dscore as dsc

from functional import pseq

def read_from_tags (tags, what):
    what += '='
    readed = pseq (tags) \
        .filter (lambda r: r[0:len (what)] == what) \
        .map (lambda r: r[len (what):]) \
        .to_list ()

    if (len (readed) == 0):
        return F'Failed to read {what}'

    return readed[0]

def construct_tags (tags):
    return pseq (tags) \
        .map (lambda t: t.split ('=', 1)) \
        .to_dict ()

def main ():
    result = ren.run_rule_engine (dsc.load_json ('rules/input.json'))

    tags = result['tags']
    print (construct_tags (tags))

    readed = read_from_tags (tags, 'CourseCode')
    # print (readed)

if (__name__ == '__main__'):
    main ()
