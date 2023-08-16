#!/bin/bash
source "$(dirname "$(realpath "$0")")/../env.sh"
export KSERVE_OPERATOR_NS=$(getKserveNS)

# Workaround
while true
do
  oc get validatingwebhookconfiguration.admissionregistration.k8s.io/inferenceservice.serving.kserve.io

  if [[ $? == 0 ]]
  then
    break
  fi
  sleep 1
done
oc delete rolebinding redhat-ods-applications -n ${KSERVE_OPERATOR_NS}
oc delete pod --all --force -n ${KSERVE_OPERATOR_NS}
oc patch validatingwebhookconfiguration inferenceservice.serving.kserve.io -p="[{'op': 'replace', 'path': '/webhooks/0/clientConfig/service/namespace', 'value': 'redhat-ods-applications'}]" --type=json
