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

ISVC_NAME=caikit-standalone-isvc
wait_for_pods_ready "serving.kserve.io/inferenceservice=${ISVC_NAME}" "${TEST_NS}"
oc wait --for=condition=ready pod -l serving.kserve.io/inferenceservice=${ISVC_NAME} -n ${TEST_NS} --timeout=300s

echo
echo "Testing text embedding"
echo

export ISVC_URL=$(oc get isvc "${ISVC_NAME}" -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}')

### Invoke the inferences:

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "all-MiniLM-L12-v2-caikit", "inputs": "first sentence"}' "${ISVC_URL}/api/v1/task/embedding"

echo
echo "Testing sentence similarity"
echo

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "all-MiniLM-L12-v2-caikit", "inputs": {
         "source_sentence": "first sentence",
         "sentences": ["first sentence", "another test sentence"]
        }
}' ${ISVC_URL}/api/v1/task/sentence-similarity

echo
echo "Testing document reranking"
echo

curl -kL -H 'Content-Type: application/json' -d '{"model_id": "all-MiniLM-L12-v2-caikit", "inputs": {
         "documents": [
            {"text": "first sentence", "title": "first title"},
            {"text": "another sentence", "more": "more attributes here"},
            {"text": "a doc with a nested metadata", "meta": {"foo": "bar", "i": 999, "f": 12.34}}
        ],
         "query": "first sentence"
        }}' ${ISVC_URL}/api/v1/task/rerank
