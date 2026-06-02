import dscore as dsc
import debug_utils as dbg

import bs4
from bs4 import BeautifulSoup
from functional import pseq, seq

PROGRAM_NAME = 'urgent-osi'

def remove_ml_attributes (markup):
    ATTRIBUTES_TO_REMOVE = [ 'style' ]
    attributes = BeautifulSoup (markup, 'html.parser')

    for att in attributes.descendants:
        if (isinstance (att, bs4.Tag)):
            att.attrs = { k: v for k, v in att.attrs.items () if k not in ATTRIBUTES_TO_REMOVE }

    return attributes.get_text ()

OWNING_ORG = 'owning-org'
def evaluate_owning_org (ia, is_draft = False):
    if ('academic_org' in ia.keys () and len (ia['academic_org']) > 0):
        ia[F'{OWNING_ORG}-label'] = ia['academic_org']['label']
        ia[F'{OWNING_ORG}-value'] = ia['academic_org']['value']

    elif ('parent_academic_org' in ia.keys () and len (ia['parent_academic_org']) > 0):
        ia[F'{OWNING_ORG}-label'] = ia['parent_academic_org']['label']
        ia[F'{OWNING_ORG}-value'] = ia['parent_academic_org']['value']

    return ia

TEACHING_ORG = 'teaching-org'
def evaluate_teaching_org (in_array, is_draft = False):
    none = []
    multi = []
    for ia in in_array:
        if ('delivery_responsibility' in ia.keys () and len (ia['delivery_responsibility']) == 1):
            ia[F'{TEACHING_ORG}-label'] = ia['delivery_responsibility'][0]['academic_org']['label']
            ia[F'{TEACHING_ORG}-value'] = ia['delivery_responsibility'][0]['academic_org']['value']

        else:
            draft_message = ' (draft) ' if is_draft else ' '

            if ('delivery_responsibility' not in ia.keys ()):
                dbg.dwarn (F"{ia['code']}{draft_message}has no delivery_responsibility!")
                none += ia['code']

            elif (len (ia['delivery_responsibility']) != 1):
                dbg.dwarn (F"{ia['code']}{draft_message}has {len (ia['delivery_responsibility'])} delivery_responsibility/ies!")
                multi += { 'code': ia['code'], 'how-many': len (ia['delivery_responsibility']) }

    return in_array, none, multi

def sanitise_description (ia):
    if ('description' in ia.keys ()):
        ia['description'] = remove_ml_attributes (ia['description'])

    return ia

CUSTOM_STATUS = 'subject-status'
def format_status (ia, is_draft):
    ia[CUSTOM_STATUS] = 'draft' if is_draft else 'current'
    return ia

def exec (generated_key, url_suffix, extract_key, columns_to_keep, is_draft = False):
    if (not dsc.has_generated (PROGRAM_NAME, generated_key)):
        api_url = F'{dsc.get_api_url ()}/{url_suffix}'
        print (api_url)
        result = dsc.request_in_parallel (api_url, extract_key, PROGRAM_NAME, generated_key)

    else:
        result = dsc.load_generated (PROGRAM_NAME, generated_key)

    for ia in result:
        ia = evaluate_owning_org (ia, is_draft)
        ia = sanitise_description (ia)
        ia = format_status (ia, is_draft)
    
    result, none, multi = evaluate_teaching_org (result, is_draft)
    dsc.to_csv (result, columns_to_keep, dsc.get_generated_path (PROGRAM_NAME, generated_key, '.csv'))

def main ():
    dsc.set_environment ('PROD')
    dsc.set_access_token ()

    columns_to_keep = [ 'code', 'name', 'sms_version', CUSTOM_STATUS, 'description', F'{OWNING_ORG}-label', F'{OWNING_ORG}-value', F'{TEACHING_ORG}-label', F'{TEACHING_ORG}-value' ]

    exec ('subjects', 'subjects?page=', 'subjects', columns_to_keep)
    exec ('subjects-draft', 'subjects?status=draft&page=', 'subjects', columns_to_keep, is_draft = True)

if (__name__ == '__main__'):
    main ()
