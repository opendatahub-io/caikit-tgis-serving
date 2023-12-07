#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

# Usage: a single! arg: "http" or "grpc" - the protocol to be used 

# Check if a single argument is passed
if [ "$#" -ne 1 ]; then
    echo "Error: exactly one argument is required: either 'http' or 'grpc'"
    exit 1
fi

# Check if the argument is either "http" or "grpc"
if [ "$1" = "http" ] || [ "$1" = "grpc" ]; then
    INF_PROTO=$1
else
    echo "Error: Argument must be either 'http' or 'grpc'."
    exit 1
fi

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"
export TEST_NS=${TEST_NS}"-$INF_PROTO"

echo
echo "Wait until $INF_PROTO runtime is READY"

ISVC_NAME=caikit-tgis-isvc-"$INF_PROTO"
wait_for_pods_ready "serving.kserve.io/inferenceservice=$ISVC_NAME" "${TEST_NS}"
oc wait --for=condition=ready pod -l serving.kserve.io/inferenceservice=$ISVC_NAME -n ${TEST_NS} --timeout=300s

echo
echo "Testing all token in a single call"
echo

export KSVC_HOSTNAME=$(oc get ksvc "$ISVC_NAME"-predictor -n ${TEST_NS} -o jsonpath='{.status.url}' | cut -d'/' -f3)
export THE_QUESTION="At what temperature does Nitrogen boil?"
export THE_MODEL="flan-t5-small-caikit"

### Invoke the inferences:

if [ "$INF_PROTO" = "http" ]; then
    curl -kL -H 'Content-Type: application/json' -d '{"model_id": "$THE_MODEL", "inputs": "$THE_QUESTION"}' https://${KSVC_HOSTNAME}/api/v1/task/text-generation

    echo
    echo "Testing streams of token"
    echo

    curl -kL -H 'Content-Type: application/json' -d '{"model_id": "$THE_MODEL", "inputs": "$THE_QUESTION"}' https://${KSVC_HOSTNAME}/api/v1/task/server-streaming-text-generation
elif [ "$INF_PROTO" = "grpc" ]; then
    grpcurl -insecure -d '{"text": "$THE_QUESTION"}' -H "mm-model-id: $THE_MODEL" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict

    echo
    echo "Testing streams of token"
    echo

    grpcurl -insecure -d '{"text": "$THE_QUESTION"}' -H "mm-model-id: $THE_MODEL" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/ServerStreamingTextGenerationTaskPredict
fi

