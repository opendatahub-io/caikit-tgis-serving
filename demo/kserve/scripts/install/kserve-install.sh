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

if [[ ! -n ${TARGET_OPERATOR+x} ]]
then
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
echo "${TARGET_OPERATOR_TYPE}"
if [[ ${TARGET_OPERATOR} == 'brew' ]] && [[ ! -n "${BREW_TAG+x}" ]]
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

export KSERVE_OPERATOR_NS=$(getKserveNS)
export TARGET_OPERATOR_NS=$(getOpNS ${TARGET_OPERATOR_TYPE})
echo
echo "Let's install KServe"


if [[ ! -d ${BASE_DIR} ]]
then
  mkdir ${BASE_DIR}
fi

if [[ ! -d ${BASE_CERT_DIR} ]]
then
  mkdir ${BASE_CERT_DIR}
fi

# Install Service Mesh operators
echo "[INFO] Install Service Mesh operators"
echo
oc apply -f custom-manifests/service-mesh/operators.yaml

wait_for_csv_installed servicemeshoperator openshift-operators
wait_for_csv_installed kiali-operator openshift-operators
wait_for_csv_installed jaeger-operator openshift-operators
oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=jaeger-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=kiali-operator -n openshift-operators --timeout=300s

# Create an istio instance
echo
echo "[INFO] Create an istio instance"
echo
oc create ns istio-system -oyaml --dry-run=client | oc apply -f-
oc::wait::object::availability "oc get project istio-system" 2 60

oc apply -f custom-manifests/service-mesh/smcp.yaml
wait_for_pods_ready "app=istiod" "istio-system"
wait_for_pods_ready "app=istio-ingressgateway" "istio-system"
wait_for_pods_ready "app=istio-egressgateway" "istio-system"
wait_for_pods_ready "app=jaeger" "istio-system"

oc wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-egressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=jaeger -n istio-system --timeout=300s

# kserve/knative
echo
echo "[INFO]Update SMMR"
echo
if [[ ${TARGET_OPERATOR_TYPE} == "odh" ]];
then
  oc create ns opendatahub -oyaml --dry-run=client | oc apply -f-
  oc::wait::object::availability "oc get project opendatahub" 2 60
else
  oc create ns redhat-ods-applications -oyaml --dry-run=client | oc apply -f-
  oc::wait::object::availability "oc get project redhat-ods-applications" 2 60
fi
oc create ns knative-serving -oyaml --dry-run=client | oc apply -f-
oc::wait::object::availability "oc get project knative-serving" 2 60

oc apply -f custom-manifests/service-mesh/smmr-${TARGET_OPERATOR_TYPE}.yaml
oc apply -f custom-manifests/service-mesh/peer-authentication.yaml
oc apply -f custom-manifests/service-mesh/peer-authentication-${TARGET_OPERATOR_TYPE}.yaml 
# we need this because of https://access.redhat.com/documentation/en-us/openshift_container_platform/4.12/html/serverless/serving#serverless-domain-mapping-custom-tls-cert_domain-mapping-custom-tls-cert

echo
echo "[INFO] Install Serverless Operator"
echo
oc apply -f custom-manifests/serverless/operators.yaml
wait_for_csv_installed serverless-operator openshift-serverless

wait_for_pods_ready "name=knative-openshift" "openshift-serverless"
wait_for_pods_ready "name=knative-openshift-ingress" "openshift-serverless"
wait_for_pods_ready "name=knative-operator" "openshift-serverless"
oc wait --for=condition=ready pod -l name=knative-openshift -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-openshift-ingress -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-operator -n openshift-serverless --timeout=300s

# Create a Knative Serving installation
echo
echo "[INFO] Create a Knative Serving installation"
echo
oc apply -f custom-manifests/serverless/knativeserving-istio.yaml

wait_for_pods_ready "app=controller" "knative-serving"
wait_for_pods_ready "app=net-istio-controller" "knative-serving"
wait_for_pods_ready "app=net-istio-webhook" "knative-serving"
wait_for_pods_ready "app=autoscaler-hpa" "knative-serving"
wait_for_pods_ready "app=domain-mapping" "knative-serving"
wait_for_pods_ready "app=webhook" "knative-serving"
oc delete pod -n knative-serving -l app=activator --force --grace-period=0
oc delete pod -n knative-serving -l app=autoscaler --force --grace-period=0
wait_for_pods_ready "app=activator" "knative-serving"
wait_for_pods_ready "app=autoscaler" "knative-serving"

oc wait --for=condition=ready pod -l app=controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler-hpa -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=domain-mapping -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=activator -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler -n knative-serving --timeout=300s

# Generate wildcard cert for a gateway.
export DOMAIN_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}' | awk -F'.' '{print $(NF-1)"."$NF}')
export COMMON_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}')

# cd ${BASE_CERT_DIR}
## Generate wildcard cert using openssl
echo
echo "[INFO] Generate wildcard cert using openssl"
echo
bash -x ./scripts/generate-wildcard-certs.sh ${BASE_CERT_DIR} ${DOMAIN_NAME} ${COMMON_NAME}

# Create the Knative gateways
oc create secret tls wildcard-certs --cert=${BASE_CERT_DIR}/wildcard.crt --key=${BASE_CERT_DIR}/wildcard.key -n istio-system
oc apply -f custom-manifests/serverless/gateways.yaml

# Create brew catalogsource
if [[ ${TARGET_OPERATOR} == "brew" ]];
then
  echo
  echo "[INFO] Create catalogsource for brew registry"
  echo
  sed "s/<%brew_tag%>/$BREW_TAG/g" custom-manifests/brew/catalogsource.yaml |oc apply -f -

  wait_for_pods_ready "olm.catalogSource=rhods-catalog-dev" "openshift-marketplace"
  oc wait --for=condition=ready pod -l olm.catalogSource=rhods-catalog-dev -n openshift-marketplace --timeout=60s  
fi

# Deploy odh/rhods operator
echo
echo "[INFO] Deploy odh/rhods operator"
echo
OPERATOR_LABEL="control-plane=controller-manager"
if [[ ${TARGET_OPERATOR_TYPE} == "rhods" ]];
then
  OPERATOR_LABEL="name=rhods-operator"
  oc create ns ${TARGET_OPERATOR_NS} -oyaml --dry-run=client | oc apply -f-  
  oc::wait::object::availability "oc get project ${TARGET_OPERATOR_NS} " 2 60
fi
oc create -f custom-manifests/opendatahub/${TARGET_OPERATOR}-operators-2.x.yaml

wait_for_pods_ready "${OPERATOR_LABEL}" "${TARGET_OPERATOR_NS}"
oc wait --for=condition=ready pod -l ${OPERATOR_LABEL} -n ${TARGET_OPERATOR_NS} --timeout=300s 

# Example CUSTOM_MANIFESTS_URL ==> https://github.com/opendatahub-io/odh-manifests/tarball/master
if [[ -n "${CUSTOM_MANIFESTS_URL+x}" ]]
then
  echo
  echo "Added custom manifest url into default dscinitializations"
  oc patch dscinitializations default -p="[{\"op\": \"add\", \"path\": \"/spec/manifestsUri\",\"value\": \"${CUSTOM_MANIFESTS_URL}\"}]" --type='json'
fi

echo
echo "[INFO] Deploy KServe"
echo
# ODH 1.9 use alpha api so this logic needed but from ODH 1.10, this logic must be deleted.
#oc create -f custom-manifests/opendatahub/kserve-dsc.yaml
if [[ ${TARGET_OPERATOR_TYPE} == "rhods" ]]; then
  oc create -f custom-manifests/opendatahub/kserve-dsc.yaml
else
  oc create -f custom-manifests/opendatahub/kserve-dsc-v1alpha1.yaml
fi

wait_for_pods_ready "control-plane=kserve-controller-manager" "${KSERVE_OPERATOR_NS}"
