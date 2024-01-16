#!/bin/bash
# Environment variables
# - CHECK_UWM: Set this to "false", if you want to skip the User Workload Configmap check message
# - TARGET_OPERATOR: Set this among odh, rhods or brew, if you want to skip the question in the script.
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

if [[ ! -n ${BASE_DIR+} ]];
then
  source ./scripts/install/check-env-variables.sh
fi

source "$(dirname "$(realpath "$0")")/../utils.sh"

if [[ ! -n "${CHECK_UWM+x}" ||  ! -n ${TARGET_OPERATOR+x}  ]]
then
  source ./scripts/install/check-env-variables.sh
fi

echo
info "[INFO] Create DataScienceCluster"
echo

dsc_name=$(oc get dsc --no-headers|awk '{print $1}')
if [[ ${dsc_name} != "" ]]
then
  oc patch datasciencecluster ${dsc_name} --type=merge -p '{"spec": {"components":{"kserve": {"managementState": "Managed"}}}}'
else
  oc create -f custom-manifests/opendatahub/kserve-dsc-2.5.yaml
fi
wait_for_pods_ready "control-plane=kserve-controller-manager" "${KSERVE_OPERATOR_NS}"

# Example CUSTOM_MANIFESTS_URL ==> https://github.com/opendatahub-io/odh-manifests/tarball/master
if [[ -n "${CUSTOM_MANIFESTS_URL+x}" ]]
then
  echo
  light_info "Added custom manifest url into default dsc"
  oc patch dsc ${dsc_name} -p="[{\"op\": \"add\", \"path\": \"/spec/components/kserve\",\"value\": \"${CUSTOM_MANIFESTS_URL}\"}]" --type='json'

  light_info "Restart kserve with a new custom manifest"
  oc delete deploy -l control-plane=kserve-controller-manager "${KSERVE_OPERATOR_NS}"
  wait_for_pods_ready "control-plane=kserve-controller-manager" "${KSERVE_OPERATOR_NS}"
fi

# Create a Knative Serving installation
echo
light_info "[INFO] Verify a Knative Serving"
echo

wait_for_pods_ready "app=controller" "knative-serving"
wait_for_pods_ready "app=net-istio-controller" "knative-serving"
wait_for_pods_ready "app=net-istio-webhook" "knative-serving"
wait_for_pods_ready "app=autoscaler-hpa" "knative-serving"
wait_for_pods_ready "app=domain-mapping" "knative-serving"
wait_for_pods_ready "app=webhook" "knative-serving"
wait_for_pods_ready "app=activator" "knative-serving"
wait_for_pods_ready "app=autoscaler" "knative-serving"

oc wait --for=condition=ready pod -l app=controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler-hpa -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=domain-mapping -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=activator -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler -n knative-serving --timeout=300s

success "[SUCCESS] KNative pods are running properly" 
success "[SUCCESS] Successfully deployed KServe operator! Ready for demo" 
