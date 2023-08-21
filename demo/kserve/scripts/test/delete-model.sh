#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source "$(dirname "$(realpath "$0")")/../env.sh"

oc delete isvc --all -n ${TEST_NS} --force --grace-period=0
oc delete ns ${TEST_NS} ${MINIO_NS}

# Get the index of the target member in the array
INDEX=$(oc get servicemeshmemberroll/default -n istio-system -o jsonpath='{.spec.members[*]}')
INDEX=$(echo ${INDEX} | tr ' ' '\n' | grep -n ${TEST_NS} | cut -d: -f1)

if [ -z "${INDEX}" ]; then
  echo "Target member ${TEST_NS} not found in the array."
  exit 1
fi

# Perform the patch operation
oc patch servicemeshmemberroll/default -n istio-system --type='json' -p="[{'op': 'remove', 'path': \"/spec/members/$((INDEX - 1))\"}]"
