#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
set -u ### any reference to an unset variable will be considered as an error and will immediately stop execution
# set -x   #Uncomment this to debug script.

# Performs inference using gRPC

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"

echo
echo "Wait until grpc runtime is READY"

ISVC_NAME=caikit-standalone-isvc-grpc
wait_for_pods_ready "serving.kserve.io/inferenceservice=${ISVC_NAME}" "${TEST_NS}"
oc wait --for=condition=ready pod -l serving.kserve.io/inferenceservice=${ISVC_NAME} -n ${TEST_NS} --timeout=300s

echo
echo "Testing text embedding"
echo

export ISVC_HOSTNAME=$(oc get isvc "${ISVC_NAME}" -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}' | cut -d'/' -f3)

### Invoke the inferences:

grpcurl -insecure -d '{"text": "first sentence"}' -H "mm-model-id: all-MiniLM-L12-v2-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/EmbeddingTaskPredict

echo
echo "Testing sentence similarity"
echo

grpcurl -insecure -d '{"source_sentence": "first sentence", "sentences": ["first sentence", "another test sentence"]}' -H "mm-model-id: all-MiniLM-L12-v2-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/SentenceSimilarityTaskPredict

echo
echo "Testing document reranking"
echo

 grpcurl -insecure -d '{"documents": [
                    {"text": "first sentence", "title": "first title"},
                    {"text": "another sentence", "more": "more attributes here"},
                    {"text": "a doc with a nested metadata", "meta": {"foo": "bar", "i": 999, "f": 12.34}}
                ],
                 "query": "first sentence"}' -H "mm-model-id: all-MiniLM-L12-v2-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/RerankTaskPredict