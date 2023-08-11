#!/bin/bash
# Environment variables
# - CHECK_UWM: Set this to "false", if you want to skip the User Workload Configmap check message
# - TARGET_OPERATOR: Set this among odh, rhods or brew, if you want to skip the question in the script.
source "$(dirname "$(realpath "$0")")/../env.sh"
if [[ -n ${CHECK_UWM} && ${CHECK_UWM} == "false" ]]
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

if [ "$input" = "y" ]; then
    if [[ ! -n ${TARGET_OPERATOR} ]]
    then
      read -p "TARGET_OPERATOR is not set. Is it for odh or rhods or brew?" input_target_op
      if [[ $input_target_op == "odh" || $input_target_op == "rhods" || $input_target_op == "brew" ]]
      then
        export TARGET_OPERATOR=$input_target_op
        export TARGET_OPERATOR_NS=$(getOpNS)
        export TARGET_OPERATOR_TYPE=$(getOpType $input_target_op)
      else 
        echo "[ERR] Only 'odh' or 'rhods' or 'brew' can be entered"
        exit 1
      fi
    else      
      export TARGET_OPERATOR_NS=$(getOpNS)
      export TARGET_OPERATOR_TYPE=$(getOpType $TARGET_OPERATOR)
    fi

    if [[ ! -n ${BREW_TAG} ]]
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
    echo
    echo "Let's install KServe"
else
    echo "ERROR: Please check the configmap and execute this script again"
    exit 1
fi

mkdir ${BASE_DIR}
mkdir ${BASE_CERT_DIR}
# cd ${BASE_DIR}
# git clone https://github.com/opendatahub-io/caikit-tgis-serving
# cd caikit-tgis-serving/demo/kserve

# Install Service Mesh operators
oc apply -f custom-manifests/service-mesh/operators.yaml
echo
echo "Wait 30s for servicemesh operators"
echo
sleep 30
oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=jaeger-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=kiali-operator -n openshift-operators --timeout=300s

# Create an istio instance
oc create ns istio-system
sleep 2
oc apply -f custom-manifests/service-mesh/smcp.yaml
echo
echo "Wait 30s for servicemesh control plane"
echo
sleep 30
oc wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-egressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=jaeger -n istio-system --timeout=300s

# kserve/knative
oc create ns redhat-ods-applications
oc create ns knative-serving
oc apply -f custom-manifests/service-mesh/smmr-${TARGET_OPERATOR_TYPE}.yaml
oc apply -f custom-manifests/service-mesh/peer-authentication.yaml
oc apply -f custom-manifests/service-mesh/peer-authentication-${TARGET_OPERATOR_TYPE}.yaml 
# we need this because of https://access.redhat.com/documentation/en-us/openshift_container_platform/4.12/html/serverless/serving#serverless-domain-mapping-custom-tls-cert_domain-mapping-custom-tls-cert

oc apply -f custom-manifests/serverless/operators.yaml
echo
echo "Wait 60s for serverless operators"
echo
sleep 60
oc wait --for=condition=ready pod -l name=knative-openshift -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-openshift-ingress -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-operator -n openshift-serverless --timeout=300s

# Create a Knative Serving installation
oc apply -f custom-manifests/serverless/knativeserving-istio.yaml
echo
echo "Wait 15s for detecting knative-serving cr"
echo
sleep 15
oc wait --for=condition=ready pod -l app=controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler-hpa -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=domain-mapping -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=webhook -n knative-serving --timeout=300s
oc delete pod -n knative-serving -l app=activator --force --grace-period=0
oc delete pod -n knative-serving -l app=autoscaler --force --grace-period=0
oc wait --for=condition=ready pod -l app=activator -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler -n knative-serving --timeout=300s

# Generate wildcard cert for a gateway.
export DOMAIN_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}' | awk -F'.' '{print $(NF-1)"."$NF}')
export COMMON_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}'|sed 's/apps.//')

# cd ${BASE_CERT_DIR}
## Generate wildcard cert using openssl
./scripts/generate-wildcard-certs.sh ${BASE_CERT_DIR} ${DOMAIN_NAME} ${COMMON_NAME}

# Create the Knative gateways
oc create secret tls wildcard-certs --cert=${BASE_CERT_DIR}/wildcard.crt --key=${BASE_CERT_DIR}/wildcard.key -n istio-system
oc apply -f custom-manifests/serverless/gateways.yaml

# Create brew catalogsource
if [[ ${TARGET_OPERATOR} == "brew" ]];
then
  echo "Create catalogsource for brew registry"
  sed "s/<%brew_tag%>/$BREW_TAG/g" custom-manifests/brew/catalogsource.yaml |oc apply -f -
  oc wait --for=condition=ready pod -l olm.catalogSource=rhods-catalog-dev -n openshift-marketplace --timeout=300s  
fi

# Deploy odh/rhods operator
oc create ns redhat-ods-operator
oc create -f custom-manifests/opendatahub/${TARGET_OPERATOR}-operators-2.0.yaml

oc wait --for=condition=ready pod -l name=rhods-operator -n ${TARGET_OPERATOR_NS} --timeout=300s 
echo
echo "Wait 30s for opendatahub operator"
echo
sleep 30
oc create -f custom-manifests/opendatahub/kserve-dsc.yaml
