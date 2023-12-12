#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

# Performs inference using HTTP

PREFIX=""
INF_PROTO=""

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"

echo
echo "Wait until $INF_PROTO runtime is READY"

ISVC_NAME=caikit-tgis-isvc"${PREFIX}${INF_PROTO}"
wait_for_pods_ready "serving.kserve.io/inferenceservice=$ISVC_NAME" "${TEST_NS}"
oc wait --for=condition=ready pod -l serving.kserve.io/inferenceservice=$ISVC_NAME -n ${TEST_NS} --timeout=300s

echo
echo "Testing all token in a single call"
echo

export KSVC_HOSTNAME=$(oc get ksvc "$ISVC_NAME"-predictor -n ${TEST_NS} -o jsonpath='{.status.url}' | cut -d'/' -f3)
#export THE_QUESTION="At what temperature does Nitrogen boil?"
# export THE_MODEL="flan-t5-small-caikit"

### Invoke the inferences:

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' https://${KSVC_HOSTNAME}/api/v1/task/text-generation

echo
echo "Testing streams of token"
echo

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' https://${KSVC_HOSTNAME}/api/v1/task/server-streaming-text-generation

