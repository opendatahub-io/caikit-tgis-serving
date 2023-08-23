#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source "$(dirname "$(realpath "$0")")/../env.sh"

if [[ ! -n "${TARGET_OPERATOR+x}" ]]
  then
    echo
    read -p "TARGET_OPERATOR is not set. Is it for odh or rhods or brew?" input_target_op
    if [[ $input_target_op == "odh" || $input_target_op == "rhods" || $input_target_op == "brew" ]]
    then
      export TARGET_OPERATOR=$input_target_op
      export TARGET_OPERATOR_TYPE=$(getOpType $input_target_op)
    else 
      echo "[ERR] Only 'odh' or 'rhods' or 'brew' can be entered"
      exit 1
    fi
  else      
    export TARGET_OPERATOR_TYPE=$(getOpType $TARGET_OPERATOR)
  fi
export KSERVE_OPERATOR_NS=$(getKserveNS)

# Delete the Knative gateways
oc delete -f custom-manifests/serverless/gateways.yaml
oc delete Jaeger jaeger -n istio-system
oc delete Kiali kiali -n istio-system
oc delete ServiceMeshControlPlane minimal -n istio-system

oc delete -f custom-manifests/serverless/knativeserving-istio.yaml
oc delete -f custom-manifests/serverless/operators.yaml

oc delete -f custom-manifests/service-mesh/smmr-${TARGET_OPERATOR_TYPE}.yaml  
oc delete -f custom-manifests/service-mesh/peer-authentication.yaml 
oc delete -f custom-manifests/service-mesh/peer-authentication-${TARGET_OPERATOR_TYPE}.yaml
oc delete ns redhat-ods-applications
oc delete ns knative-serving
oc delete -f custom-manifests/service-mesh/smcp.yaml
oc delete ns istio-system
oc delete -f custom-manifests/service-mesh/operators.yaml

if [[ -n "${BASE_DIR+x}"  ]] && [[ -n "${BASE_CERT_DIR+x}" ]]
then
  if [[ ! z$BASE_DIR == 'z' ]]
  then
    rm -rf /${BASE_DIR}
    rm -rf /${BASE_CERT_DIR}
  fi
fi

# Verify 

oc delete KnativeServing knative-serving -n knative-serving
oc delete subscription jaeger-product -n openshift-operators
oc delete subscription kiali-ossm -n openshift-operators
oc delete subscription servicemeshoperator -n openshift-operators
oc delete subscription serverless-operator -n openshift-serverless

jaeger_csv_name=$(oc get csv -n openshift-operators | grep jaeger|awk '{print $1}')
oc delete csv $jaeger_csv_name -n openshift-operators

kiali_csv_name=$(oc get csv -n openshift-operators | grep kiali|awk '{print $1}')
oc delete csv $kiali_csv_name -n openshift-operators

sm_csv_name=$(oc get csv -n openshift-operators | grep servicemeshoperator|awk '{print $1}')
oc delete csv $sm_csv_name -n openshift-operators

sl_csv_name=$(oc get csv -n openshift-operators | grep serverless-operator|awk '{print $1}')
oc delete csv $sm_csv_name -n openshift-serverless

oc delete csv OperatorGroup serverless-operators -n openshift-serverless

oc delete project istio-system
oc delete project knative-serving
oc delete project knative-eventing
oc delete project $TEST_NS
