
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
export TARGET_OPERATOR_NS=$(getOpNS ${TARGET_OPERATOR_TYPE})

oc delete validatingwebhookconfiguration inferencegraph.serving.kserve.io  inferenceservice.serving.kserve.io 
oc delete mutatingwebhookconfiguration inferenceservice.serving.kserve.io
oc delete isvc --all -n ${TEST_NS} --force --grace-period=0

echo "It would take around around 3~4 mins"
oc delete ns ${TEST_NS} ${MINIO_NS}
oc delete secret wildcard-certs -n istio-system

oc delete DataScienceCluster --all -n "${KSERVE_OPERATOR_NS}"
sleep 15
oc delete sub "${KSERVE_OPERATOR_NS}-operator" -n ${TARGET_OPERATOR_NS}
  
if [[ ${TARGET_OPERATOR} == "brew" ]];
then  
  oc delete catalogsource rhods-catalog-dev -n openshift-marketplace
fi
if [[ ${TARGET_OPERATOR_TYPE} == "rhods" ]]; then
  oc delete ns redhat-ods-operator redhat-ods-applications rhods-notebooks redhat-ods-monitoring --force --grace-period=0
  oc delete csv -n ${TARGET_OPERATOR_NS} $(oc get csv -n ${TARGET_OPERATOR_NS}|grep rhods|awk '{print $1}')
else
  oc delete ns ${KSERVE_OPERATOR_NS} --force --grace-period=0
  oc delete csv -n ${TARGET_OPERATOR_NS} $(oc get csv -n ${TARGET_OPERATOR_NS} |grep opendatahub|awk '{print $1}')
fi

# Remove test namespace from SMMR
INDEX=$(oc get servicemeshmemberroll/default -n istio-system -o jsonpath='{.spec.members[*]}')
INDEX=$(echo ${INDEX} | tr ' ' '\n' | grep -n ${TEST_NS} | cut -d: -f1)

if [ -z "${INDEX}" ]; then
  echo "Target member ${TEST_NS} not found in the array."
fi
oc patch servicemeshmemberroll/default -n istio-system --type='json' -p="[{'op': 'remove', 'path': \"/spec/members/$((INDEX - 1))\"}]"


# Remove kserve namespace from SMMR
INDEX=$(oc get servicemeshmemberroll/default -n istio-system -o jsonpath='{.spec.members[*]}')
INDEX=$(echo ${INDEX} | tr ' ' '\n' | grep -n ${KSERVE_OPERATOR_NS} | cut -d: -f1)

if [ -z "${INDEX}" ]; then
  echo "Target member ${TEST_NS} not found in the array."
fi
oc patch servicemeshmemberroll/default -n istio-system --type='json' -p="[{'op': 'remove', 'path': \"/spec/members/$((INDEX - 1))\"}]"
