# KServe with Caikit + TGIS runtime

## Prerequisite
- Openshift Cluster 
  - This doc is written based on ROSA cluster
  - many of the tasks in this tutorial require cluster-admin permission level (e.g., install operators, set service-mesh configuration, enable http2, etc)
- CLI tools
  - oc cli
- To enable metrics
  - cluster-admin is needed to enable User Workload Monitoring on the cluster
  - [Enable User Workload Monitoring](#enable-user-workload-monitoring)
  - [Configure User Workload Monitoring](#configure-user-workload-monitoring)

- http2 enabled in the cluster

- [Installed operators](#prerequisite-installation)
  - [Kiali](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
  - [Red Hat OpenShift distributed tracing platform](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
  - [Red Hat OpenShift Service Mesh](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
    - ServiceMeshControlPlan
  - [Openshift Serverless](https://docs.openshift.com/serverless/1.29/install/install-serverless-operator.html)
  - [OpenDataHub](https://opendatahub.io/docs/quick-installation/)

#### Enable User Workload Monitoring
~~~
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
~~~
#### Configure User Workload Monitoring
~~~
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-workload-monitoring-config
  namespace: openshift-user-workload-monitoring
data:
  config.yaml: |
    prometheus:
      logLevel: debug 
      retention: 15d #Change as needed
~~~

## Reference
- https://github.com/ReToCode/knative-kserve#installation-with-istio--mesh
- https://knative.dev/docs/install/operator/knative-with-operators/#create-the-knative-serving-custom-resource
  
## Prerequisite installation
~~~
git clone https://github.com/opendatahub-io/caikit-tgis-serving
cd caikit-tgis-serving/demo/kserve

# Install Service Mesh operators
oc apply -f custom-manifests/service-mesh/operators.yaml
sleep 30
oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=jaeger-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=kiali-operator -n openshift-operators --timeout=300s

# Create an istio instance
oc create ns istio-system
oc apply -f custom-manifests/service-mesh/smcp.yaml
sleep 30
oc wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=prometheus -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-egressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=jaeger -n istio-system --timeout=300s

# kserve/knative
oc create ns kserve
oc create ns knative-serving
oc -n istio-system apply -f custom-manifests/service-mesh/smmr.yaml 
oc apply -f custom-manifests/service-mesh/peer-authentication.yaml
# we need this because of https://access.redhat.com/documentation/en-us/openshift_container_platform/4.12/html/serverless/serving#serverless-domain-mapping-custom-tls-cert_domain-mapping-custom-tls-cert

oc apply -f custom-manifests/serverless/operators.yaml
sleep 30
oc wait --for=condition=ready pod -l name=knative-openshift -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-openshift-ingress -n openshift-serverless --timeout=300s
oc wait --for=condition=ready pod -l name=knative-operator -n openshift-serverless --timeout=300s

# Create a Knative Serving installation
oc apply -f custom-manifests/serverless/knativeserving-istio.yaml
sleep 15
oc wait --for=condition=ready pod -l app=controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-controller -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=net-istio-webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler-hpa -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=domain-mapping -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=webhook -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=activator -n knative-serving --timeout=300s
oc wait --for=condition=ready pod -l app=autoscaler -n knative-serving --timeout=300s

# Generate wildcard cert for a gateway.
export BASE_DIR=/tmp/certs
export DOMAIN_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}' | awk -F'.' '{print $(NF-1)"."$NF}')
export COMMON_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}'|sed 's/apps.//')

mkdir ${BASE_DIR}

## Generate wildcard cert using openssl
./scripts/generate-wildcard-certs.sh ${BASE_DIR} ${DOMAIN_NAME} ${COMMON_NAME}

# Create the Knative gateways
oc create secret tls wildcard-certs --cert=${BASE_DIR}/wildcard.crt --key=${BASE_DIR}/wildcard.key -n istio-system
oc apply -f custom-manifests/serverless/gateways.yaml
~~~

## Deploy KServe with OpenDataHub Operator
~~~
oc create -f custom-manifests/opendatahub/operators.yaml
sleep 30
oc create -f custom-manifests/opendatahub/kfdef-kserve-op.yaml
~~~


## Deploy Minio for example LLM model

If you have your model in another S3-like object storage (e.g., AWS S3), you can skip this step.
~~~
ACCESS_KEY_ID=THEACCESSKEY
SECRET_ACCESS_KEY=$(openssl rand -hex 32)
MINIO_NS=minio

oc new-project ${MINIO_NS}
sed "s/<accesskey>/$ACCESS_KEY_ID/g"  ./custom-manifests/minio/minio.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" | tee ./minio-current.yaml | oc -n ${MINIO_NS} apply -f -
sed "s/<accesskey>/$ACCESS_KEY_ID/g" ./custom-manifests/minio/minio-secret.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" |sed "s/<minio_ns>/$MINIO_NS/g" | tee ./minio-secret-current.yaml | oc -n ${MINIO_NS} apply -f - 

sed "s/<minio_ns>/$MINIO_NS/g" ./custom-manifests/minio/serviceaccount-minio.yaml | tee ./serviceaccount-minio-current.yaml 
~~~

## Deploy flan-t5-small model with Caikit+TGIS Serving runtime

If you have installed prerequisites(servicemesh,serverless,kserve and minio), you can start here.

### Setup ISTIO configuration for the test demo namespace

~~~
export TEST_NS=kserve-demo
oc new-project ${TEST_NS}
sed "s/<test_ns>/$TEST_NS/g" custom-manifests/service-mesh/smmr-test-ns.yaml | tee ./smmr-current.yaml | oc -n istio-system apply -f -
oc patch smmr/default -n istio-system --type='json' -p="[{'op': 'add', 'path': '/spec/members/-', 'value': \"$TEST_NS\"}]"
~~~
To enable metrics, the PeerAuthentication needs the appropriate service label for `matchLabel`. The expected service label is `<isvc-name>-predictor-default`
The existing file has been configured to work with the example isvc in this repo.
~~~
sed "s/<test_ns>/$TEST_NS/g" custom-manifests/service-mesh/peer-authentication-test-ns.yaml | tee ./peer-authentication-test-ns-current.yaml | oc apply -f -
# we need this because of https://access.redhat.com/documentation/en-us/openshift_container_platform/4.12/html/serverless/serving#serverless-domain-mapping-custom-tls-cert_domain-mapping-custom-tls-cert
# oc apply -f custom-manifests/metrics/networkpolicy-uwm.yaml -n ${TEST_NS}
~~~

### Create Caikit ServingRuntime
Before running the next line: if you are going to serve the model using CPU and not GPU, you need to set the following parameter in the runtime config (you find a comment in the YAML file too):
```
- name: DTYPE_STR
  value: float32
```
~~~
oc apply -f ./custom-manifests/caikit/caikit-servingruntime.yaml -n ${TEST_NS}
~~~

### Deploy example model(flan-t5-samll)
You have your model in another S3-like object storage (e.g., AWS S3), you can change according the connection data in the minio-secret.yaml and serviceaccount-minio.yaml from caikit-tgis-serving/demo/kserve/custom-manifests/minio/ path
~~~
oc apply -f ./minio-secret-current.yaml -n ${TEST_NS} 
oc create -f ./serviceaccount-minio-current.yaml -n ${TEST_NS}

oc apply -f ./custom-manifests/caikit/caikit-isvc.yaml -n ${TEST_NS}

# Resources needed to enable metrics for the model 
# The metrics service needs the correct label in the `matchLabel` field. The expected value of this label is `<isvc-name>-predictor-default`
# The metrics service in this repo is configured to work with the example model. If you are deploying a different model or using a different model name, change the label accordingly. 
oc apply -f custom-manifests/metrics/caikit-metrics-service.yaml -n ${TEST_NS}
oc apply -f custom-manifests/metrics/caikit-metrics-servicemonitor.yaml -n ${TEST_NS}
~~~

### gRPC Test
Ensure http2 protocol is enabled in the cluster
~~~
oc get ingresses.config/cluster -ojson | grep ingress.operator.openshift.io/default-enable-http2
~~~

If the annotation is either set to false or not present, enable it:
~~~
oc annotate ingresses.config/cluster ingress.operator.openshift.io/default-enable-http2=true
~~~

If everything is set fine, you can run the following grpcurl command:
~~~
export KSVC_HOSTNAME=$(oc get ksvc caikit-example-isvc-predictor-default -n ${TEST_NS} -o jsonpath='{.status.url}' | cut -d'/' -f3)
grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
~~~
The expected answer is something similar to:
~~~
{
  "generated_token_count": "5",
  "text": "74 degrees F",
  "stop_reason": "EOS_TOKEN",
  "producer_id": {
    "name": "Text Generation",
    "version": "0.1.0"
  }
}
~~~


## Verifying Caikit Metrics

[Prerequisites](#enable-metrics-for-caikit-serving)

- Navigate to Openshift Console --> Observe --> Targets
  - Search by Label `namespace=kserve-demo`
  - Verify `caikit-example-isvc-predictor-default-sm` has `status : up`
- Navigate to Openshift Console --> Observe --> Metrics
  - Search for `predict_caikit_library_duration_seconds_created` and verify metric values exist

All caikit produced metrics should successfully show up in Openshift UserWorkload Monitoring now

---
**Tip.**

*Deploy KServe with OpenDataHub manifests for test purpose.*
~~~
# KServe Kfdef
git clone git@github.com:opendatahub-io/odh-manifests.git
rm -rf  custom-manifests/opendatahub/.cache  custom-manifests/opendatahub/kustomize /tmp/odh-manifests.gzip
tar czvf /tmp/odh-manifests.gzip odh-manifests
kfctl build -V -f custom-manifests/opendatahub/kfdef-kserve.yaml -d | oc create -n kserve -f -
~~~
