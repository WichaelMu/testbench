import sys
import dscore as dsc
from functional import seq, pseq


PROGRAM_NAME = 'post-osfl-heroes'
OPENSEARCH_PROGRAM_NAME = 'opensearch-full-load'


def register_microsoft_graph_api ():
    microsoft_credentials = dsc.load_json ('secrets.json')['MICROSOFT']

    token = dsc.get_custom_auth (**microsoft_credentials)

def staff_id_to_hero (staff_id):
    hero = dsc.make_get_request (F"https://graph.microsoft.com/v1.0/users/?$filter=mailNickname eq '{staff_id}'")
    return hero['value'][0]['mail']

def is_probably_staff_id (probably):
    return isinstance (probably, str) and len (probably) == 6 and probably.isnumeric ()

def main ():
    register_microsoft_graph_api ()

    unprocessable_subjects = dsc.load_generated (OPENSEARCH_PROGRAM_NAME, 'unprocessable-subjects')
    unproc_subjects = pseq (unprocessable_subjects) \
        .map (lambda x: {
            'sys_id': x['sys_id'],
            'code': x['code'],
            'sys_created_by': staff_id_to_hero (x['sys_created_by']) if is_probably_staff_id (x['sys_created_by']) else x['sys_created_by'],
            'sys_created_on': x['sys_created_on'],
            'sys_updated_by': staff_id_to_hero (x['sys_updated_by']) if is_probably_staff_id (x['sys_updated_by']) else x['sys_updated_by'],
            'sys_updated_on': x['sys_updated_on'],
            'version': x['version'],
            'version_approved': x['version_approved'],
            'sms_version': x['sms_version']
        })\
        .to_list ()

    dsc.save_generated (PROGRAM_NAME, 'extracted', unproc_subjects)

if (__name__ == '__main__'):
    main ()
    sys.exit (0)
