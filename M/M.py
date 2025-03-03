import json

def pt (p, b_print=True):
    result = F"{type (p)}: {p}"
    if (b_print):
        print (result)
    else:
        return result

def filter_empties (response_file, is_aggregation=True):
    response = json.loads (open (response_file, 'r').read ())

    if (is_aggregation):
        pass
    else:
        result = clean_aggregation (response)
        return result

    return {}

def clean_aggregation (r):
    debug_null_values = True
    debug_empty_arrays = True
    debug_empty_strings = True
    buckets = r.get("aggregations", {}).get("agg_key_1", {}).get("buckets", [])
    clean_items = []

    for bucket in buckets:
        inner_hits = bucket.get("agg_key_2", {}).get("hits", {}).get("hits", [])

        for hit in inner_hits:
            item = hit.get("_source", {})

            def clean_data(data):
                if isinstance(data, list):
                    return [
                        clean_data(subitem)
                        for subitem in data
                        if (subitem is not None or debug_null_values)
                        and (subitem != [] or debug_empty_arrays)
                        and (subitem != "" or debug_empty_strings)
                    ]
                elif isinstance(data, dict):
                    return {
                        key: clean_data(value)
                        for key, value in data.items()
                        if (value is not None or debug_null_values)
                        and (value != [] or debug_empty_arrays)
                        and (value != "" or debug_empty_strings)
                    }
                else:
                    return data

            cleaned_item = clean_data(item)
            clean_items.append(cleaned_item)

    return clean_items
