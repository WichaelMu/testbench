import json
import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_oauth2client import OAuth2Client
import yaml
import logging
import re

logger = logging.getLogger(os.environ["FUNCTION_NAME"])
logger.setLevel(logging.DEBUG)


def load_yaml():
    with open("curriculum-data-spec.yaml", "r") as file:
        openapi_spec = yaml.safe_load(file)

    pagination_info = openapi_spec["components"]["parameters"]
    default_page = pagination_info["page"]["schema"]["default"]
    default_limit = pagination_info["limit"]["schema"]["default"]
    maximum_limit = pagination_info["limit"]["schema"]["maximum"]

    return default_page, default_limit, maximum_limit


def load_yaml_s3(openapi_spec):
    pagination_info = openapi_spec["components"]["parameters"]
    default_page = pagination_info["page"]["schema"]["default"]
    default_limit = pagination_info["limit"]["schema"]["default"]
    maximum_limit = pagination_info["limit"]["schema"]["maximum"]

    return default_page, default_limit, maximum_limit


def validate_pagination(page, limit, default_page, default_limit, maximum_limit):
    if not isinstance(page, int) or page < 1:
        return {
            "statusCode": "400",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"message": "Page should be an integer greater than 0."}
            ),
        }

    if not isinstance(limit, int) or limit < 1 or limit > maximum_limit:
        return {
            "statusCode": "400",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": f"Limit should be an integer between 1 and {maximum_limit}."
                }
            ),
        }
    # if total == 0:
    #     return {
    #         "statusCode": "200",
    #         "headers": {"Content-Type": "application/json"},
    #         "body": json.dumps({"message": "No data available."}),
    #     }

    # max_page = total // limit if total % limit == 0 else total // limit + 1
    # if page > max_page:
    #     return {
    #         "statusCode": "400",
    #         "headers": {"Content-Type": "application/json"},
    #         "body": json.dumps(
    #             {"message": f"Page should not exceed maximum page: {max_page}."}
    #         ),
    #     }

    return None


def get_envar_ENV():
    return "ENV"


def get_secret_envar_name():
    return "SECRET_NAME"


def get_secret_envar_host():
    return "OPENSEARCH_ENDPOINT_URL"


def boto3_client_config():
    config = Config(
        region_name="ap-southeast-2",
        signature_version="v4",
        retries={"max_attempts": 8, "mode": "standard"},
    )

    return config


def str_to_bool(value):
    return str(value).lower() != "false"


def transform_and_clean_data(response, event):
    remove_empty_arrays = str_to_bool(
        event.get("queryStringParameters", {}).get("removeEmptyArrays", "True")
    )
    remove_empty_strings = str_to_bool(
        event.get("queryStringParameters", {}).get("removeEmptyStrings", "True")
    )
    hits = response.get("hits", {}).get("hits", [])

    clean_items = []
    for hit in hits:
        item = hit.get("_source", {})

        def clean_data(data):
            if isinstance(data, list):
                if not data and not remove_empty_arrays:
                    return data
                else:
                    return [
                        clean_data(subitem)
                        for subitem in data
                        if subitem is not None
                        and (subitem != [] or not remove_empty_arrays)
                        and (subitem != "" or not remove_empty_strings)
                    ]
            elif isinstance(data, dict):
                return {
                    key: clean_data(value)
                    for key, value in data.items()
                    if value is not None
                    and (value != [] or not remove_empty_arrays)
                    and (value != "" or not remove_empty_strings)
                }
            else:
                return data

        cleaned_item = clean_data(item)
        clean_items.append(cleaned_item)

    return clean_items


def transform_and_clean_data_aggregation(response, event):
    remove_empty_arrays = str_to_bool(
        event.get("queryStringParameters", {}).get("removeEmptyArrays", "True")
    )
    remove_empty_strings = str_to_bool(
        event.get("queryStringParameters", {}).get("removeEmptyStrings", "True")
    )

    buckets = response.get("aggregations", {}).get("agg_key_1", {}).get("buckets", [])

    clean_items = []

    for bucket in buckets:
        inner_hits = bucket.get("agg_key_2", {}).get("hits", {}).get("hits", [])

        for hit in inner_hits:
            item = hit.get("_source", {})

            def clean_data(data):
                if isinstance(data, list):
                    if not data and not remove_empty_arrays:
                        return data
                    else:
                        return [
                            clean_data(subitem)
                            for subitem in data
                            if subitem is not None
                            and (subitem != [] or not remove_empty_arrays)
                            and (subitem != "" or not remove_empty_strings)
                        ]
                elif isinstance(data, dict):
                    return {
                        key: clean_data(value)
                        for key, value in data.items()
                        if value is not None
                        and (value != [] or not remove_empty_arrays)
                        and (value != "" or not remove_empty_strings)
                    }
                else:
                    return data

            cleaned_item = clean_data(item)
            clean_items.append(cleaned_item)

    return clean_items


def get_secret(secret_name, secret_stage=None):
    try:
        secretsmanager_client = boto3.client(
            "secretsmanager", config=boto3_client_config()
        )

        kwargs = {"SecretId": secret_name}

        if secret_stage is not None:
            kwargs["VersionStage"] = secret_stage

        response = secretsmanager_client.get_secret_value(**kwargs)
    except ClientError:
        logger.exception("could not obtain the value in secret %s", secret_name)

        raise
    else:
        return json.loads(response["SecretString"])


def render_error_with_message(error_message, status_code="500"):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "level": "ERROR",
        "message": error_message,
    }


# used for awsauth
def create_oauth2client(cl_secret):
    token_endpoint = cl_secret["authz_token_url"]
    oauth2client = OAuth2Client(
        token_endpoint=token_endpoint,
        auth=(cl_secret["data_client_id"], cl_secret["data_client_secret"]),
        scope=cl_secret["data_scope"],
    )

    return oauth2client


def get_pagination_params(event, default_page, default_limit):
    page = int(event.get("queryStringParameters", {}).get("page", default_page))
    limit = int(event.get("queryStringParameters", {}).get("limit", default_limit))
    from_ = (page - 1) * limit

    return page, limit, from_


def extract_code(event, regularExpression):
    pattern = regularExpression
    code = event["rawPath"]
    match = re.match(pattern, code)
    if match:
        # Extracting the course code
        return match.group(1)
    else:
        return None


def invoke_other_lambda():
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName="other_lambda_function_name",
        InvocationType="RequestResponse",
    )

    response_payload = json.loads(response["Payload"].read())
    return response_payload


def parse_yaml_data(response_payload):
    yaml_data = yaml.safe_load(response_payload["body"])
    return yaml_data
