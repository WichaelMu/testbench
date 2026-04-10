import os

import rule_engine as ren
import dscore as dsc

PAYLOAD = {
  "documents": [
    { "type": "invoice", "fields": { "email": "john@doe.com", "taxId": "" } },
    { "type": "id",      "fields": { "email": "",             "taxId": "123-45-6789" } }
  ]
}

def main ():
    result = ren.run_rule_engine (PAYLOAD)
    print (result)

if (__name__ == '__main__'):
    main ()
