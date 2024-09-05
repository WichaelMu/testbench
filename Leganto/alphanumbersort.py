from functional import seq
INT_MAX = (1 << 31) - 1

def find_first_numerical_occurence (v):
    has_hit_numeric = False
    str_val = ''
    bias_value = 0
    for c in v:
        if (ord (c) >= ord ('0') and ord (c) <= ord ('9')):
            # print (F"{c} - {v}")
            str_val += c
            has_hit_numeric = True
        elif (has_hit_numeric):
            return int (str_val) + bias_value
        else:
            bias_value += ord (c)
    return bias_value

def exec ():
    c = [
        { "name": "Week 10: ABC (1)", "value": "d" },
        { "name": "Week 1: ABC (5)", "value": "c" },
        { "name": "Module 1: ABC (2)", "value": "a" },
        { "name": "Module 11: ABC (0)", "value": "b" },
        { "name": "inactive Resources", "value": "f" },
        { "name": "active Resources but redundant", "value": "e" }
    ]

    sorter = []
    for t in c:
        n = find_first_numerical_occurence (t["name"])
        sorter.append ({ "sorting_key": n, "data": t })
        # print (F"{type (n)} {n}")

    result = sorted (sorter, key=lambda k: k["sorting_key"])
    result = seq (result).map (lambda x: x['data']).to_list ()
    print (result)


if (__name__ == "__main__"):
    exec ()
