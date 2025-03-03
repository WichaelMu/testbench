import os;

print ([ k for k in os.sys.argv ])

import json

i = os.sys.argv[1] if (len (os.sys.argv) > 1) else ''
print (json.dumps (i))
