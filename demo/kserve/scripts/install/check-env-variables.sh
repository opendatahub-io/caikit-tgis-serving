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
if [[ -n "${CHECK_UWM+x}" && ${CHECK_UWM} == "false" ]]
then
  input="y"
else
  echo "** Check User Workload Configmap for Kserve metrics before you execute this script **"
  echo 
  cat <<EOF

  $ oc get cm cluster-monitoring-config -n openshift-monitoring -o yaml

  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: cluster-monitoring-config
    namespace: openshift-monitoring
  data:
    config.yaml: |
      enableUserWorkload: true    #<==== Check this part

  ---

  $ oc get cm user-workload-monitoring-config -n openshift-user-workload-monitoring -o yaml

  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: user-workload-monitoring-config
    namespace: openshift-user-workload-monitoring
  data:
    config.yaml: |
      prometheus:
        logLevel: debug 
        retention: 15d #Change as needed  <==Check this
EOF

  echo
  read -p "Have you checked if user workload configmap is set correctly? (then enter 'y')" input
fi

if [ "$input" != "y" ];
then
    echo "ERROR: Please check the configmap and execute this script again"
    exit 1
fi

if [[ -n "${DEPLOY_ODH_OPERATOR+x}" ]]
then  
  deploy_odh_operator=${DEPLOY_ODH_OPERATOR}
fi

if [[ ! -n ${TARGET_OPERATOR+x} ]]
then
  read -p "TARGET_OPERATOR is not set. Is it for odh or rhods or brew?" input_target_op
  if [[ $input_target_op == "odh" || $input_target_op == "rhods" || $input_target_op == "brew" ]]
  then
    export TARGET_OPERATOR=$input_target_op
    export TARGET_OPERATOR_TYPE=$(getOpType $input_target_op)
  else 
    echo "[ERR] Only 'odh' or 'rhods' or 'brew' can be used"
    exit 1
  fi
else      
  export TARGET_OPERATOR_TYPE=$(getOpType $TARGET_OPERATOR)
fi
echo "${TARGET_OPERATOR_TYPE}"

if [[ ${deploy_odh_operator} == "true" ]] && [[ ${TARGET_OPERATOR} == 'brew' ]] && [[ ! -n "${BREW_TAG+x}" ]]
then
  read -p "BREW_TAG is not set, what is BREW_TAG?" brew_tag
  if [[ $brew_tag =~ ^[0-9]+$ ]]
  then
    export BREW_TAG=$brew_tag
  else 
    echo "[ERR] BREW_TAG must be number only"
    exit 1
  fi      
fi

# It does not check if the files exist
if [[ -n ${CUSTOM_CERT+x}  && ! -n ${CUSTOM_KEY+x} ]]; then
    die "ERROR: CUSTOM_KEY must be set if CUSTOM_CERT is set."
elif [[ ! -n ${CUSTOM_CERT+x} && -n ${CUSTOM_KEY+x} ]]; then
    die "ERROR: CUSTOM_CERT must be set if CUSTOM_KEY is set."
elif  [[ -n ${CUSTOM_CERT+x} && -n ${CUSTOM_KEY+x} ]]; then
    info "Both CUSTOM_CERT and CUSTOM_KEY are set."
    info "Knative gateway will use them "
else
    info "Neither CUSTOM_CERT nor CUSTOM_KEY is set."
    info "self signed cert will be generated but do not use it for production"
fi

export KSERVE_OPERATOR_NS=$(getKserveNS)
export TARGET_OPERATOR_NS=$(getOpNS ${TARGET_OPERATOR_TYPE})

success "[SUCCESS] Successfully get all environment variables" 
