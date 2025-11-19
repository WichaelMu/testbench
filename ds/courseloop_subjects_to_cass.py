import requests

import dscore as dsc

ENVIRONMENT = 'CL_TO_CASS'

def set_access_token ():
    credentials = dsc.load_json ('secrets.json')
    client_id = credentials[ENVIRONMENT]['client_id']
    client_secret = credentials[ENVIRONMENT]['client_secret']
    token_url = credentials[ENVIRONMENT]['token_url']

    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    }

    response = requests.post (token_url, data=payload)
    response.raise_for_status ()
    token_data = response.json ()

    return token_data['access_token']

def main ():
    dsc.set_environment ('CL_TO_CASS')
    dsc.set_access_token ()

    spk_cat_type_rules     = 'https://uts-test.t1cloud.com/T1Default/CiAnywhere/Web/UTS-TEST/Api/RaaS/v1/StudyPackageCategoryTypeRules?q=CurriculumType=SJ'
    active_sok_header      = 'https://uts-test.t1cloud.com/T1Default/CiAnywhere/Web/UTS-TEST/Api/WS/v1/Curriculum/ReadActiveOrHighestVersionHeaderBySpk/17136'
    spk_details            = 'https://uts-test.t1cloud.com/T1Default/CiAnywhere/Web/UTS-TEST/Api/WS/v1/Curriculum/ReadForStudyPackage/35315/1'
    external_org_id_number = 'https://uts-test.t1cloud.com/T1Default/CiAnywhere/Web/UTS-TEST/Api/RaaS/v1/ExtOrgUnits?q=Code={source.input.subjects[0].external_provider[0].provider_name.value}'

    test = "https://uts-test.t1cloud.com/T1Default/CiAnywhere/Web/UTS-TEST/Api/WS/v1/EtlRunHistory/ReadByJobId/3065555"

    print (dsc.make_get_request (test))

if (__name__ == '__main__'):
    main ()
