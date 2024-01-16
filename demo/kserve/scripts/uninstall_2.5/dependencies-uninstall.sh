#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source "$(dirname "$(realpath "$0")")/../env.sh"

oc delete ServiceMeshControlPlane,pod --all -n istio-system --force --grace-period=0
oc delete KnativeServing,pod --all -n knative-serving --force --grace-period=0
oc delete ns knative-serving

oc delete ns istio-system

oc delete -f custom-manifests/service-mesh/operators.yaml
oc delete -f custom-manifests/serverless/operators.yaml

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
oc delete subscription servicemeshoperator -n openshift-operators
oc delete subscription serverless-operator -n openshift-serverless

sm_csv_name=$(oc get csv -n openshift-operators | grep servicemeshoperator|awk '{print $1}')
oc delete csv $sm_csv_name -n openshift-operators

sl_csv_name=$(oc get csv -n openshift-operators | grep serverless-operator|awk '{print $1}')
oc delete csv $sm_csv_name -n openshift-serverless

oc delete csv OperatorGroup serverless-operators -n openshift-serverless

oc delete project istio-system
oc delete project knative-serving
oc delete project knative-eventing
oc delete project openshift-serverless

oc get ns ${TEST_NS}
if [[ $? ==  0 ]]
then
    oc delete project $TEST_NS
fi
