#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source "$(dirname "$(realpath "$0")")/../env.sh"

oc delete isvc,pod --all -n ${TEST_NS} --force --grace-period=0
oc delete ns ${TEST_NS} ${MINIO_NS} --force --grace-period=0

