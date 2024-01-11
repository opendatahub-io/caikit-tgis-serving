#!/bin/bash
# Environment variables
# - CHECK_UWM: Set this to "false", if you want to skip the User Workload Configmap check message
# - TARGET_OPERATOR: Set this among odh, rhods or brew, if you want to skip the question in the script.
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source ./scripts/install/check-env-variables.sh
source "$(dirname "$(realpath "$0")")/../env.sh"
source "$(dirname "$(realpath "$0")")/../utils.sh"


if [[ ! -d ${BASE_DIR} ]]
then
  mkdir ${BASE_DIR}
fi

if [[ ! -d ${BASE_CERT_DIR} ]]
then
  mkdir ${BASE_CERT_DIR}
fi

echo
info "Let's install ServiceMesh, OpenDataHub and Serverless operators"

# Install Service Mesh operators
echo
light_info "[INFO] Install Service Mesh operators"
echo
oc apply -f custom-manifests/service-mesh/operators.yaml

wait_for_csv_installed servicemeshoperator openshift-operators
oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s

echo
light_info "[INFO] Install Serverless Operator"
echo
oc apply -f custom-manifests/serverless/operators.yaml
wait_for_csv_installed serverless-operator openshift-serverless

wait_for_pods_ready "name=knative-openshift" "openshift-serverless"
wait_for_pods_ready "name=knative-openshift-ingress" "openshift-serverless"
wait_for_pods_ready "name=knative-operator" "openshift-serverless"
oc wait --for=condition=ready pod -l name=knative-openshift -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-openshift-ingress -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-operator -n openshift-serverless --timeout=300s


echo
light_info "[INFO] Deploy odh operator"
echo

# Create brew catalogsource
if [[ ${deploy_odh_operator} == "true" ]]
then
  if [[ ${TARGET_OPERATOR} == "brew" ]];
  then
    echo
    light_info "[INFO] Create catalogsource for brew registry"
    echo
    sed "s/<%brew_tag%>/$BREW_TAG/g" custom-manifests/brew/catalogsource.yaml |oc apply -f -

    wait_for_pods_ready "olm.catalogSource=rhods-catalog-dev" "openshift-marketplace"
    oc wait --for=condition=ready pod -l olm.catalogSource=rhods-catalog-dev -n openshift-marketplace --timeout=60s  
  fi

  # Deploy odh/rhods operator
  OPERATOR_LABEL="control-plane=controller-manager"
  if [[ ${TARGET_OPERATOR_TYPE} == "rhods" ]];
  then
    OPERATOR_LABEL="name=rhods-operator"
    oc create ns ${TARGET_OPERATOR_NS} -oyaml --dry-run=client | oc apply -f-  
    oc::wait::object::availability "oc get project ${TARGET_OPERATOR_NS}" 2 60    
  fi
  oc create -f custom-manifests/opendatahub/${TARGET_OPERATOR}-operators-2.x.yaml

  wait_for_pods_ready "${OPERATOR_LABEL}" "${TARGET_OPERATOR_NS}"
  oc wait --for=condition=ready pod -l ${OPERATOR_LABEL} -n ${TARGET_OPERATOR_NS} --timeout=300s 

else
  light_info "DEPLOY_ODH_OPERATOR set ${deploy_odh_operator}. Skip deploy odh/rhods operator" 
fi

success "[SUCCESS] Successfully installed ServiceMesh, Serverless, OpenDataHub(OpenShiftAI) operators" 
