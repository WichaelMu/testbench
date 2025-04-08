import os

import dscore as dsc

def parse_clia ():
    print (os.sys.argv)

def main ():
    dsc.set_environment ('NONPROD')
    print (F'ENVIRONMENT: {dsc.get_wenvironment ()}')
    dsc.set_access_token ()

    parse_clia ()

if (__name__ == '__main__'):
    main ()
    os.sys.exit (0)
