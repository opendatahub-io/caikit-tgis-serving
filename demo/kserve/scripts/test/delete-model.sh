#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

### This script will remove objects related to the protocol specified (http or grpc) as single and mandatory parameter

# Check if a single argument is passed
if [ "$#" -ne 1 ]; then
    echo "Error: exactly one argument is required: either 'http' or 'grpc'"
    exit 1
fi

# Check if the argument is either "http" or "grpc"
if [ "$1" = "http" ] || [ "$1" = "grpc" ]; then
    INF_PROTO=$1
else
    echo "Error: Argument must be either 'http' or 'grpc'."
    exit 1
fi

source "$(dirname "$(realpath "$0")")/../env.sh"
export TEST_NS_REMOVE=${TEST_NS}"-"${INF_PROTO}

oc get ns ${TEST_NS_REMOVE}
if [[ $? ==  0 ]]
then
    oc delete isvc,pod --all -n ${TEST_NS_REMOVE} --force --grace-period=0
    oc delete ns  ${TEST_NS_REMOVE} --force --grace-period=0
fi


