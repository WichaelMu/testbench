import sys
import json

def replace_arr(InList: list, JsonResult: str):
    for v in InList:
        if (isinstance (v, dict)):
            JsonResult = replace (v, JsonResult);
        elif (isinstance (v, list)):
            JsonResult = replace_arr(v, JsonResult);
    return JsonResult;

def replace(InDictionary: dict, JsonResult: str):
    for k, v in InDictionary.items():
        if (k.endswith(".$")):
            continue;
        if ('-' not in k):
            JsonResult = JsonResult.replace(F'"{k}"', F"{k}");
        if (isinstance (v, dict)):
            JsonResult =  replace (v, JsonResult);
        elif (isinstance (v, list)):
            JsonResult = replace_arr(v, JsonResult);
    return JsonResult;

def exec():
    JsonSource = "";
    JsonResult = {};

    if (len(sys.argv) > 1):
        JsonSource = sys.argv[1];
        JsonResult = open(JsonSource, "r").read();
    else:
        print (F"Please supply a .json file as argv[1]");
        sys.exit(1);

    JsonResult = replace (json.loads(JsonResult), JsonResult);
    JsonResult = JsonResult.replace(": ", " = ");

    print (JsonResult);

if (__name__ == "__main__"):
    exec();
    sys.exit(0);
