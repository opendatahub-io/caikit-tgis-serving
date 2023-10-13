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

  # Example CUSTOM_MANIFESTS_URL ==> https://github.com/opendatahub-io/odh-manifests/tarball/master
  if [[ -n "${CUSTOM_MANIFESTS_URL+x}" ]]
  then
    echo
    light_info "Added custom manifest url into default dscinitializations"
    oc patch dscinitializations default -p="[{\"op\": \"add\", \"path\": \"/spec/manifestsUri\",\"value\": \"${CUSTOM_MANIFESTS_URL}\"}]" --type='json'
  fi
else
  light_info "DEPLOY_ODH_OPERATOR set ${deploy_odh_operator}. Skip deploy odh/rhods operator" 
fi

echo
info "[INFO] Create DataScienceCluster"
echo

dsc_exists=$(oc get datasciencecluster default --all-namespaces)
if [[ -n $dsc_exists ]]
then
  oc patch datasciencecluster default --type=merge -p '{"spec": {"components":{"kserve": {"managementState": "Managed"}}}}'
else
  oc create -f custom-manifests/opendatahub/kserve-dsc.yaml
fi

wait_for_pods_ready "control-plane=kserve-controller-manager" "${KSERVE_OPERATOR_NS}"

success "[SUCCESS] Successfully deployed KServe operator! Ready for demo" 
