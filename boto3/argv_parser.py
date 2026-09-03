import os
import sys

KENABLE = 'enable'
KPREFIX = 'prefix'
KSUFFIX = 'suffix'
KCONTAINS = 'contains'
KEXCLUDES = 'excludes'
KLAMBDA_VERSIONS_ONLY = 'lambda-versions'
KREWIND_ONLY = 'rewind-only'
KQUERY_ONLY = 'query'
KSTATUS_CHECK = 'status'

def parse_argv ():
    argv = sys.argv[1:]
    argc = len (argv)

    # print (F'argc, argv: {argc}, {argv}')

    def process_option (option, iterator):
        match option:
            case '--enable':
                iterator += 1

                if (argv[iterator].lower () == 'yes' or argv[iterator].lower () == 'true'):
                    result = True
                elif (argv[iterator].lower () == 'no' or argv[iterator].lower () == 'false'):
                    result = False
                else:
                    print ('--enable must be [ yes | no | true | false ]')
                    sys.exit (1)

                return { KENABLE: result }, iterator

            case '--dry' | '--query':
                return { KQUERY_ONLY: True }, iterator

            case '--status':
                return { KSTATUS_CHECK: True }, iterator

            case '--lambda-versions-only':
                return { KLAMBDA_VERSIONS_ONLY: True }, iterator

            case '--prefix':
                iterator += 1

                return { KPREFIX: argv[iterator] }, iterator

            case '--suffix':
                iterator += 1

                return { KSUFFIX: argv[iterator] }, iterator

            case '--contains':
                iterator += 1

                return { KCONTAINS: argv[iterator] }, iterator

            case '--excludes':
                iterator += 1

                return { KEXCLUDES: argv[iterator] }, iterator

            case '--rewind-only':
                iterator += 1

                if (argv[iterator].lower () == 'yes' or argv[iterator].lower () == 'true'):
                    result = True
                elif (argv[iterator].lower () == 'no' or argv[iterator].lower () == 'false'):
                    result = False
                else:
                    print ('--rewind-only must be [ yes | no | true | false ]')
                    sys.exit (1)

                return { KREWIND_ONLY: argv[iterator] }, iterator

            case '?' | '--help' | 'help' | '__HELP__':
                print ('--enable true | false --prefix PREFIX --suffix SUFFIX')
                sys.exit (0)
                return {}, iterator

            case _:
                return {}, iterator

    options = {
        KPREFIX: '',
        KSUFFIX: '',
        KCONTAINS: '',
        KQUERY_ONLY: False,
        KSTATUS_CHECK: False,
        KLAMBDA_VERSIONS_ONLY: False
    }

    iterator = 0
    while (iterator < argc):
        try:

            option, iterator = process_option (argv[iterator], iterator)
            options = options | option

            iterator += 1

        except IndexError:

            print (F'Option {iterator + 1} ({argv[iterator]}) requires a parameter.')
            process_option ('?', 0)
            sys.exit (1)

    # print (options)

    errors_exist = False
    if (KENABLE not in options and KREWIND_ONLY not in options):
        if (not options[KQUERY_ONLY] and not options[KSTATUS_CHECK]):
            print (F'One of --enable or --rewind-only is required')
            errors_exist = True

    if (options[KPREFIX] == '' and options[KSUFFIX] == '' and options[KCONTAINS] == ''):
        print (F'One of --prefix, --suffix, or --contains must be present')
        errors_exist = True

    if (errors_exist):
        sys.exit (1)

    return options
