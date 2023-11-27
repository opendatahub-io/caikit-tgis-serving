#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"

echo
echo "Wait until runtime is READY"

wait_for_pods_ready "serving.kserve.io/inferenceservice=caikit-example-isvc" "${TEST_NS}"
oc wait --for=condition=ready pod -l serving.kserve.io/inferenceservice=caikit-example-isvc -n ${TEST_NS} --timeout=300s

echo
echo "Testing all token in a single call"
echo

export KSVC_HOSTNAME=$(oc get ksvc caikit-example-isvc-predictor -n ${TEST_NS} -o jsonpath='{.status.url}' | cut -d'/' -f3)
curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' https://${KSVC_HOSTNAME}/api/v1/task/text-generation

echo
echo "Testing streams of token"
echo

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' https://${KSVC_HOSTNAME}/api/v1/task/server-streaming-text-generation