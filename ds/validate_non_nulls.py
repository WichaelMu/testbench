"""
Validate non-null GraphQL fields against a JSON payload.

Usage examples:
  # Validate a local sample file with a schema file
  python validate_non_nulls.py --schema schema.graphql --file sample-response.json --root-type SubstructuresContainer

  # Validate by hitting an HTTP endpoint (GET) with optional headers and query params
  python validate_non_nulls.py --schema schema.graphql --url https://example/substructures --root-type SubstructuresContainer \
      --header "Authorization: Bearer XYZ" --param "page=1" --param "limit=50"

Notes:
- The script parses your GraphQL SDL to discover *non-null* fields (fields whose type ends with '!').
- If a field is of list type (e.g., [T]!), the list itself must not be null.
- If list items are non-null (e.g., [T!] or [T!]!), each element must not be null. Nested objects are recursively validated.
- Optional fields (without '!') are validated only if they are present in the JSON; their inner non-null fields still apply once present.
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import dscore as dsc

try:
    import requests
except Exception:
    requests = None  # requests may not be installed in certain environments


# --- GraphQL SDL parsing ---

FieldDef = Dict[str, Any]  # {'type': 'TypeName', 'is_list': bool, 'non_null': bool, 'item_non_null': bool}
SchemaMap = Dict[str, Dict[str, FieldDef]]  # {'TypeName': {'fieldName': FieldDef, ...}, ...}

SCALAR_TYPES = {
    'String','ID','Int','Float','Boolean',
    'AWSDateTime','AWSDate','AWSTime','AWSJSON','AWSEmail','AWSPhone','AWSURL','AWSIPAddress',
}

TYPE_BLOCK_RE = re.compile (r"type\s+(\w+)\b[^{]*\{(?P<body>.*?)\}", re.DOTALL)
FIELD_LINE_RE = re.compile (r"^\s*(\w+)\s*:\s*([^#]+?)(?:\s+#.*)?$", re.MULTILINE)  # name: type ...

def parse_field_type (type_str: str) -> Tuple[str, bool, bool, bool]:
    """
    Parse a field type string like:
      - "String!" -> base='String', is_list=False, non_null=True, item_non_null=False
      - "[Foo!]!" -> base='Foo', is_list=True, non_null=True, item_non_null=True
      - "[Bar]"   -> base='Bar', is_list=True, non_null=False, item_non_null=False
    """
    s = type_str.strip ()
    non_null = s.endswith ('!')
    if non_null:
        s = s[:-1].strip ()

    is_list = False
    item_non_null = False
    base = s

    if s.startswith ('[') and s.endswith (']'):
        is_list = True
        inner = s[1:-1].strip ()
        item_non_null = inner.endswith ('!')
        if item_non_null:
            inner = inner[:-1].strip ()
        base = inner

    # Remove any trailing directives or comments (e.g., "@aws_oidc")
    base = base.split ('@', 1)[0].strip ()

    return base, is_list, non_null, item_non_null


def parse_schema (schema_text: str) -> SchemaMap:
    types: SchemaMap = {}
    for m in TYPE_BLOCK_RE.finditer (schema_text):
        type_name = m.group (1)
        body = m.group ('body')
        fields: Dict[str, FieldDef] = {}

        for fm in FIELD_LINE_RE.finditer (body):
            field_name = fm.group (1)
            type_part = fm.group (2).strip ()
            # ignore fields that look like method signatures (with parens), e.g. getX (arg: T): Y
            if '(' in field_name or '(' in type_part:
                continue
            base, is_list, non_null, item_non_null = parse_field_type (type_part)
            fields[field_name] = {
                'type': base,
                'is_list': is_list,
                'non_null': non_null,
                'item_non_null': item_non_null,
            }
        if fields:
            types[type_name] = fields
    return types


# --- Validation ---

class Violation:
    def __init__(self, path: str, type_name: str, field_name: Optional[str], message: str):
        self.path = path
        self.type_name = type_name
        self.field_name = field_name
        self.message = message

    def __str__(self):
        where = self.path
        if self.field_name:
            where = f"{self.path}.{self.field_name}"
        return f"[{self.type_name}] {where} -> {self.message}"


def is_scalar (type_name: str) -> bool:
    return type_name in SCALAR_TYPES


def validate_value (value: Any, type_name: str, schema: SchemaMap, path: str, required: bool, out: List[Violation]):
    # If required and value is None -> violation
    if value is None:
        if required:
            out.append (Violation (path, type_name, None, "value is null but field is non-nullable"))
        return

    # Scalars: nothing further to validate
    if is_scalar (type_name):
        return

    # Unknown types: can't recurse, but we can still accept presence
    type_def = schema.get (type_name)
    if not type_def:
        return

    if not isinstance (value, dict):
        # JSON shape mismatch; this script focuses on 'null' checks, but we still note mismatch to help debugging.
        out.append (Violation (path, type_name, None, f"expected object for type '{type_name}' but found {type (value).__name__}"))
        return

    # For each field declared in the type
    for field_name, fdef in type_def.items ():
        f_type = fdef['type']
        f_is_list = fdef['is_list']
        f_non_null = fdef['non_null']
        f_item_non_null = fdef['item_non_null']

        if f_is_list:
            arr = value.get (field_name)
            if arr is None:
                if f_non_null:
                    out.append (Violation (path, type_name, field_name, "field is null but list is non-nullable ([T]!)"))
                continue

            if not isinstance (arr, list):
                # Not primarily a null check, but report it anyway
                out.append (Violation (path, type_name, field_name, f"expected list ([{f_type}]) but found {type (arr).__name__}"))
                continue

            # Item nullability
            for idx, item in enumerate (arr):
                item_path = f"{path}.{field_name}[{idx}]"
                if item is None and f_item_non_null:
                    out.append (Violation (item_path, f_type, None, "list item is null but item type is non-nullable (T!)"))
                    continue

                # Recurse into objects if present
                if item is not None and not is_scalar (f_type):
                    validate_value (item, f_type, schema, item_path, required=False, out=out)

        else:
            f_val = value.get (field_name)
            if f_val is None:
                if f_non_null:
                    out.append (Violation (path, type_name, field_name, "field is null but non-nullable"))
                continue

            # Recurse into object fields
            if not is_scalar (f_type):
                validate_value (f_val, f_type, schema, f"{path}.{field_name}", required=False, out=out)


def main ():
    ap = argparse.ArgumentParser (description="Validate non-null GraphQL fields against JSON payloads.")
    src = ap.add_mutually_exclusive_group (required=True)
    src.add_argument ("--file", help="Path to a local JSON file.")
    ap.add_argument ("--schema", required=True, help="Path to GraphQL SDL schema file (.graphql).")
    ap.add_argument ("--root-type", required=True, help="Root GraphQL type name to validate against (e.g., SubstructuresContainer).")
    ap.add_argument ("--param", action="append", default=[], help='Query param, e.g. "page=1" (may be repeated)')
    args = ap.parse_args ()

    # Load schema
    schema_text = open (args.schema, "r", encoding="utf-8").read ()
    schema = parse_schema (schema_text)

    # Acquire JSON
    if args.url:
        if requests is None:
            print ("ERROR: The 'requests' package is not available. Install it, or use --file.", file=sys.stderr)
            sys.exit (2)

        url = dsc.get_api_url ()
        headers = dsc.set_access_token ()
        headers = { 'Authorization': F'Bearer {dsc.global_access_token}' }

        params = {}
        for p in args.param:
            if "=" not in p:
                print (f"WARNING: ignoring malformed param: {p}", file=sys.stderr)
                continue
            k, v = p.split ("=", 1)
            params[k.strip ()] = v.strip ()

        resp = requests.get (url, headers=headers, params=params, timeout=30)
        resp.raise_for_status ()
        data = resp.json ()
    else:
        with open (args.file, "r", encoding="utf-8") as f:
            data = json.load (f)

    # Validate starting from the declared root type
    violations: List[Violation] = []
    validate_value (data, args.root_type, schema, path="$", required=True, out=violations)

    # Report
    if not violations:
        print ("✅ No non-nullability violations found.")
    else:
        print (f"❌ Found {len (violations)} non-nullability violation (s):")
        for v in violations:
            print ("-", str (v))


if __name__ == "__main__":
    main ()
