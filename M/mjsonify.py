import sys
import json
import ast

def main ():
    inbound = sys.stdin.read ().strip ().replace ('\n', '').replace ('\r', '')

    if (len (inbound) == 0):
        return json.dumps ({ 'MJSN': 'Nothing was received as input.' })

    try:
        dict_form = ast.literal_eval (inbound)

        result = json.dumps (dict_form, indent = 4)
        return result

    except:
        return inbound

if (__name__ == '__main__'):
    print (main ())
