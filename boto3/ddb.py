import os
import json

from boto3.dynamodb.types import TypeDeserializer

from decimal import Decimal
from typing import Any, Iterable, Mapping

import py_log_event_module as lem
import py_msk_serverless_data_streaming_client as kem

import dscore as dsc

# Iffy but will do
DESER = TypeDeserializer ()

def is_integral (d: Decimal) -> bool:
    # Decimal.is_integer () is not available in Py3.12 – use to_integral_value

    return d == d.to_integral_value ()

def normalise (x: Any) -> Any:
    """Recursively convert Decimals→int/float, sets→sorted lists, and keep nested containers pure."""

    match x:
        case Decimal () as d:
            return int (d) if is_integral (d) else float (d)

        case set () as s:
            # Stable, JSON-friendly order; normalise elements recursively
            return sorted ((normalise (v) for v in s), key = lambda v: (str (type (v)), str (v)))

        case list () as lst:
            return [ normalise (v) for v in lst ]

        case dict () as m:
            return { k: normalise (v) for k, v in m.items () }

        case _:
            return x

def from_av (av: Any) -> Any:
    """Single AttributeValue → Python, then normalise."""

    return normalise (DESER.deserialize (av))

def from_av_map (av_map: Mapping[str, Any] | None) -> dict | None:
    """AttributeValue map (e.g. NewImage/OldImage/Keys) → plain dict."""

    return None if not av_map else { k: from_av (v) for k, v in av_map.items () }

from boto3.dynamodb.types import TypeDeserializer

def deserialize_dynamo_item (item):
    deserializer = TypeDeserializer ()
    return { k: deserializer.deserialize (v) for k, v in item.items () }

if (__name__ == '__main__'):
    ddb_input = dsc.load_json ('inputs/ddb.json')['Keys']
    r = from_av_map (ddb_input)
    # r = deserialize_dynamo_item (ddb_input)

    print (r)
