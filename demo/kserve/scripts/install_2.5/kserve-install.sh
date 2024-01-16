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

source ./scripts/install/check-env-variables.sh
./scripts/install_2.5/1-prerequisite-operators.sh
./scripts/install_2.5/2-verify-istio.sh
./scripts/install_2.5/3-kserve-install.sh
