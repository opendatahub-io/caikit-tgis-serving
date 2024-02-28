#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

if ! command -v jq >/dev/null; then
	echo "jq is required to run this script" >&2
	exit 1
fi

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"

echo
echo "Wait until runtime is READY"

wait_for_pods_ready "serving.kserve.io/inferenceservice=caikit-tgis-isvc-grpc" "${TEST_NS}"
oc wait --for=condition=ready pod -l serving.kserve.io/inferenceservice=caikit-tgis-isvc-grpc -n ${TEST_NS} --timeout=300s

export ISVC_HOSTNAME=$(oc get isvc caikit-tgis-isvc-grpc -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}' | cut -d'/' -f3)

echo "test namespace: $TEST_NS"
echo "isvc hostname: $ISVC_HOSTNAME"

while true; do
	read -p "> " question
	grpcurl -insecure -d "{\"text\": \"${question}\"}" -H "mm-model-id: flan-t5-small-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict | jq .generated_text
done
