#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
set -u ### any reference to an unset variable will be considered as an error and will immediately stop execution

# set -x   #Uncomment this to debug script.

# Performs inference using HTTP

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"

echo
echo "Wait until http runtime is READY"

ISVC_NAME=caikit-tgis-isvc
wait_for_pods_ready "serving.kserve.io/inferenceservice=${ISVC_NAME}" "${TEST_NS}"
oc wait --for=condition=ready pod -l serving.kserve.io/inferenceservice=${ISVC_NAME} -n ${TEST_NS} --timeout=300s

echo
echo "Testing all token in a single call"
echo

ISVC_URL=$(oc get isvc "${ISVC_NAME}" -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}')

### Invoke the inferences:

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' "${ISVC_URL}/api/v1/task/text-generation"

echo
echo "Testing streams of token"
echo

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' "${ISVC_URL}/api/v1/task/server-streaming-text-generation"
