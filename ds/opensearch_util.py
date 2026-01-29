"""
AOSS (Amazon OpenSearch Serverless) index + write PoC using opensearch-py.

Requirements:
  pip install opensearch-py boto3

Usage examples:
  # Using your default AWS credentials (env vars or ~/.aws/credentials)
  python aoss_poc.py \
    --endpoint https://ut4da9bt9aqp0y61c0ac.ap-southeast-2.aoss.amazonaws.com \
    --region ap-southeast-2 \
    --index poc-index \
    --id "C88888,1"

  # Using an AWS CLI profile
  python aoss_poc.py \
    --profile yourprofile \
    --endpoint https://ut4da9bt9aqp0y61c0ac.ap-southeast-2.aoss.amazonaws.com \
    --region ap-southeast-2 \
    --index poc-index

Notes:
  - You need BOTH:
      (1) AOSS Network access policy to allow your source (public/VPC),
      (2) AOSS Data access policy to include your principal for index permissions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from requests_aws4auth import AWS4Auth
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth


DEFAULT_MESSAGE = (
    "In the perpetual meantime of a sheltered eternity, most are content to live, and not to dream. "
    "But in the hidden corners where the gods' gaze does not fall, there are those who dream of dreaming."
)


def _strip_scheme(endpoint: str) -> str:
    s = (endpoint or "").strip()
    if s.startswith("https://"):
        s = s[len("https://") :]
    elif s.startswith("http://"):
        s = s[len("http://") :]
    # Drop any path suffix
    s = s.split("/", 1)[0]
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True, help="AOSS collection endpoint (https://...aoss.amazonaws.com)")
    ap.add_argument("--region", required=True, help="AWS region, e.g. ap-southeast-2")
    ap.add_argument("--index", default="poc-index", help="Index name to create/use")
    ap.add_argument("--id", default="poc-1", help="Document id (can include commas)")
    ap.add_argument("--profile", default=None, help="AWS CLI profile name (optional)")
    ap.add_argument('--use-role', action='store_true', help='Should we use a ROLE_ARN instead?')
    ap.add_argument('--role-arn', default=None, help='The ARN of the Role to Assume.')
    args = ap.parse_args()

    host = _strip_scheme(args.endpoint)
    if not host:
        print("Bad --endpoint", file=sys.stderr)
        return 2

    auth = None
    if (not args.use_role):
        # Credentials from env/instance-profile by default, or from the provided profile.
        session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
        credentials = session.get_credentials()
        if credentials is None:
            print("No AWS credentials found (check env vars / AWS profile / instance role).", file=sys.stderr)
            return 2

        # IMPORTANT for Serverless: service must be "aoss" (not "es"). :contentReference[oaicite:1]{index=1}
        auth = AWSV4SignerAuth(credentials, args.region, service="aoss")

    else:
        sess = boto3.Session()
        sts = sess.client("sts", region_name=args.region)

        resp = sts.assume_role(
            RoleArn=args.role_arn,
            RoleSessionName='mw-test-please-ignore-me',
        )

        creds = resp["Credentials"]

        auth = AWS4Auth(
            creds["AccessKeyId"],
            creds["SecretAccessKey"],
            args.region,
            "aoss",
            session_token=creds["SessionToken"],
        )

    client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True,
        pool_maxsize=10,
    )

    index_name = args.index
    doc_id = args.id

    document = {
        "message": DEFAULT_MESSAGE,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp_index = client.index(
            index=index_name,
            id=doc_id,
            body=document
        )

        print (resp_index.keys ())
        print("Index response:", json.dumps(resp_index, indent=2, default=str))

    except Exception as exc:
        print(f"Indexing failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
