#!/bin/bash

export ENV=dev
export FUNCTION_NAME="dev_post_statements_ahegs_lambda"
export SECRET_NAME=dev/curriculum/courseloop/endpoints/api/credentials/client
export OPENSEARCH_ENDPOINT_URL=search.curriculum.dev.mesh.uts.edu.au
export MSSQL_SECRETS=dev/curriculum/cognos/endpoints/sqlserver/verge/credentials

python3 testbench.py