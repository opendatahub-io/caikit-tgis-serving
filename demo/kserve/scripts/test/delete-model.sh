#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

### This script will remove, if relevant, both kserve-demo-http and kserve-demo-grpc namespaces and their content and then will remove the minio namespace

source "$(dirname "$(realpath "$0")")/../env.sh"
export TEST_NS_HTTP=${TEST_NS}"-http"
export TEST_NS_GRPC=${TEST_NS}"-grpc"

oc get ns ${TEST_NS_HTTP}}
if [[ $? ==  0 ]]
then
    oc delete isvc,pod --all -n ${TEST_NS_HTTP} --force --grace-period=0
fi

oc get ns ${TEST_NS_GRPC}}
if [[ $? ==  0 ]]
then
    oc delete isvc,pod --all -n ${TEST_NS_GRPC} --force --grace-period=0
fi

### common to all protocols:
oc delete ns ${MINIO_NS} --force --grace-period=0

