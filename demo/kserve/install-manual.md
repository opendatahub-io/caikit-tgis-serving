# Manual Installation
## Export Environment Variables
Set the variables below with desired values.
`TARGET_OPERATOR` could be either `odh` or `rhods`.
~~~
export TARGET_OPERATOR=odh
~~~
## Clone the repo and setup the environment
~~~
git clone https://github.com/opendatahub-io/caikit-tgis-serving
cd caikit-tgis-serving/demo/kserve

source ./scripts/env.sh
export TARGET_OPERATOR_TYPE=$(getOpType $TARGET_OPERATOR)
export TARGET_OPERATOR_NS=$(getOpNS)
export KSERVE_OPERATOR_NS=$(getKserveNS)
~~~

## Install Service Mesh operators
~~~
oc apply -f custom-manifests/service-mesh/operators.yaml
sleep 30
oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=jaeger-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=kiali-operator -n openshift-operators --timeout=300s
~~~

## Create an Istio instance
~~~
oc create ns istio-system
oc apply -f custom-manifests/service-mesh/smcp.yaml
sleep 30
oc wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-egressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=jaeger -n istio-system --timeout=300s
~~~

## Install Knative Serving
~~~
oc create ns ${KSERVE_OPERATOR_NS}
oc create ns knative-serving
oc -n istio-system apply -f custom-manifests/service-mesh/smmr-${TARGET_OPERATOR_TYPE}.yaml 
oc apply -f custom-manifests/service-mesh/peer-authentication.yaml
oc apply -f custom-manifests/service-mesh/peer-authentication-${TARGET_OPERATOR_TYPE}.yaml 
~~~
We use PeerAuthentications to enable mTLS according to [Openshift Serverless Documentation](https://access.redhat.com/documentation/en-us/red_hat_openshift_serverless/1.28/html/serving/configuring-custom-domains-for-knative-services#serverless-domain-mapping-custom-tls-cert_domain-mapping-custom-tls-cert)
~~~
oc apply -f custom-manifests/serverless/operators.yaml
sleep 30
oc wait --for=condition=ready pod -l name=knative-openshift -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-openshift-ingress -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-operator -n openshift-serverless --timeout=300s
~~~

## Create a KnativeServing Instance
~~~
oc apply -f custom-manifests/serverless/knativeserving-istio.yaml
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
~~~

## Generate wildcard cert for a gateway using OpenSSL
~~~
export BASE_DIR=/tmp/kserve
export BASE_CERT_DIR=${BASE_DIR}/certs
export DOMAIN_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}' | awk -F'.' '{print $(NF-1)"."$NF}')
export COMMON_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}'|sed 's/apps.//')

mkdir ${BASE_DIR}
mkdir ${BASE_CERT_DIR}

./scripts/generate-wildcard-certs.sh ${BASE_CERT_DIR} ${DOMAIN_NAME} ${COMMON_NAME}
~~~

## Create the Knative gateways
~~~
oc create secret tls wildcard-certs --cert=${BASE_CERT_DIR}/wildcard.crt --key=${BASE_CERT_DIR}/wildcard.key -n istio-system
oc apply -f custom-manifests/serverless/gateways.yaml
~~~

## Apply Istio monitoring resources 
~~~
oc apply -f ./custom-manifests/service-mesh/istiod-monitor.yaml 
oc apply -f ./custom-manifests/service-mesh/istio-proxies-monitor.yaml 
~~~

## Apply Cluster Role to allow prometheus access 
~~~
oc apply -f ./custom-manifests/metrics/kserve-prometheus-k8s.yaml
~~~
## Deploy KServe
We will now deploy KServe with Open Data Hub Operator 2.0.
~~~
oc create ns ${TARGET_OPERATOR_NS}
oc create -f custom-manifests/opendatahub/${TARGET_OPERATOR}-operators-2.0.yaml

# For preview RHODS in brew registry, uncomment the command below
# oc apply -f custom-manifests/opendatahub/brew-operators-2.0.yaml

sleep 10
oc wait --for=condition=ready pod -l name=rhods-operator -n ${TARGET_OPERATOR_NS} --timeout=300s 

oc create -f custom-manifests/opendatahub/kserve-dsc.yaml
~~~
## (optional) Brew Registry
**Note:** If you don't use brew regsitry, you can ignore this part.

Brew is a registry where WIP images are published. Please look for the desired/correct brew tag, as it changes with every build. We will create a catalogSource for brew registry.
~~~
export BREW_TAG=554186
sed "s/<%brew_tag%>/$BREW_TAG/g" custom-manifests/brew/catalogsource.yaml |oc apply -f -
oc wait --for=condition=ready pod -l olm.catalogSource=rhods-catalog-dev -n openshift-marketplace --timeout=300s  
~~~

## (optional) Deploy KServe with OpenDataHub manifests for testing purposes
We will use KServe KFDef.
~~~
git clone git@github.com:opendatahub-io/odh-manifests.git
rm -rf  custom-manifests/opendatahub/.cache  custom-manifests/opendatahub/kustomize /tmp/odh-manifests.gzip
tar czvf /tmp/odh-manifests.gzip odh-manifests
kfctl build -V -f custom-manifests/opendatahub/kfdef-kserve.yaml -d | oc create -n kserve -f -
~~~
