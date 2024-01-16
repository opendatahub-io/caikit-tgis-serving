#!/bin/bash
# Environment variables
# - CHECK_UWM: Set this to "false", if you want to skip the User Workload Configmap check message
# - TARGET_OPERATOR: Set this among odh, rhods or brew, if you want to skip the question in the script.
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"

# Create an istio instance
echo
light_info "[INFO] Verify istio pods"
echo

oc::wait::object::availability "oc get project istio-system" 2 60    
oc::wait::object::availability "oc get smcp data-science-smcp -n istio-system" 2 60    

if [[ -n ${PLATFORM+x} ]] && [[ $PLATFORM == "rosa" ]]
then
  oc patch smcp data-science-smcp --type merge --patch   '{"spec":{"security":{"identity":{"type":"ThirdParty"}}}}' -n istio-system
fi

wait_for_pods_ready "app=istiod" "istio-system"
wait_for_pods_ready "app=istio-ingressgateway" "istio-system"
wait_for_pods_ready "app=istio-egressgateway" "istio-system"

oc wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-egressgateway -n istio-system --timeout=300s

success "[SUCCESS] ISTIO pods are running properly" 
