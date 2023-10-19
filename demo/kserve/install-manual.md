# Step-by-step command installation of Kserve and dependencies

Note: You have the alternative option of installing the KServe/Caikit/TGIS stack by using [Script-based installation](/demo/kserve/scripts/README.md).

**Prerequisites**

- To support Inferencing, your cluster needs a node with 4 CPUs and 16 GB memory.
- You have cluster administrator permissions.
- You have installed the OpenShift CLI (`oc`).

**Procedure**

1. Specify the data science operator by setting the `TARGET_OPERATOR` environment variable to either `odh` or `rhods`.

   For the Red Had OpenShift Data Science Operator:

   ```bash
   export TARGET_OPERATOR=rhods
   ```

   For the OpenDataHub Operator:

   ```bash
   export TARGET_OPERATOR=odh
   ```

2. Clone the repo and set up the environment.

   ```bash
   git clone https://github.com/opendatahub-io/caikit-tgis-serving

   cd caikit-tgis-serving/demo/kserve

   source ./scripts/env.sh
   source ./scripts/utils.sh
   export TARGET_OPERATOR_TYPE=$(getOpType $TARGET_OPERATOR)
   export TARGET_OPERATOR_NS=$(getOpNS)
   export KSERVE_OPERATOR_NS=$(getKserveNS)
   ```

3. Install the Service Mesh operators.

   ```bash
   oc apply -f custom-manifests/service-mesh/operators.yaml
   sleep 10
   oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s
   ```

4. Create an Istio instance.

   ```bash
   oc create ns istio-system
   oc apply -f custom-manifests/service-mesh/smcp.yaml
   sleep 10
   wait_for_pods_ready "app=istiod" "istio-system"
   wait_for_pods_ready "app=istio-ingressgateway" "istio-system"
   wait_for_pods_ready "app=istio-egressgateway" "istio-system"

   oc wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
   oc wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s
   oc wait --for=condition=ready pod -l app=istio-egressgateway -n istio-system --timeout=300s
   ```

5. Install Knative Serving.

   ```bash
   oc create ns ${KSERVE_OPERATOR_NS}
   oc create ns knative-serving
   oc -n istio-system apply -f custom-manifests/service-mesh/default-smmr.yaml

   oc apply -f custom-manifests/serverless/operators.yaml
   sleep 10
   wait_for_csv_installed serverless-operator openshift-serverless
   oc wait --for=condition=ready pod -l name=knative-openshift -n openshift-serverless --timeout=300s
   oc wait --for=condition=ready pod -l name=knative-openshift-ingress -n openshift-serverless --timeout=300s
   oc wait --for=condition=ready pod -l name=knative-operator -n openshift-serverless --timeout=300s
   ```

6. Create a KnativeServing Instance.

   ```bash
   oc apply -f custom-manifests/serverless/knativeserving-istio.yaml
   sleep 15
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
   ```

7. Generate a wildcard certification for a gateway using OpenSSL.

   ```bash
   export BASE_DIR=/tmp/kserve
   export BASE_CERT_DIR=${BASE_DIR}/certs
   export DOMAIN_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}' | awk -F'.' '{print $(NF-1)"."$NF}')
   export COMMON_NAME=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}')

   mkdir ${BASE_DIR}
   mkdir ${BASE_CERT_DIR}

   ./scripts/generate-wildcard-certs.sh ${BASE_CERT_DIR} ${DOMAIN_NAME} ${COMMON_NAME}
   export TARGET_CUSTOM_CERT=${BASE_CERT_DIR}/wildcard.crt
   export TARGET_CUSTOM_KEY=${BASE_CERT_DIR}/wildcard.key
   ```

   **(Note)**
   If you want to use your own cert, you can set these 2 variables instead of following the step 7 above.

   ```bash
   export TARGET_CUSTOM_CERT=/path/to/custom.crt
   export TARGET_CUSTOM_KEY=/path/to/custom.key
   ```

8. Create the Knative gateway.

   ```bash
   oc create secret tls wildcard-certs --cert=${TARGET_CUSTOM_CERT} --key=${TARGET_CUSTOM_KEY} -n istio-system
   oc apply -f custom-manifests/serverless/gateways.yaml
   ```

9. Apply the Istio monitoring resources.

   ```bash
   oc apply -f ./custom-manifests/service-mesh/istiod-monitor.yaml
   oc apply -f ./custom-manifests/service-mesh/istio-proxies-monitor.yaml
   ```

10. Apply the cluster role to allow Prometheus access.

    ```bash
    oc apply -f ./custom-manifests/metrics/kserve-prometheus-k8s.yaml
    ```

11. Deploy KServe with Open Data Hub Operator 2.0.

    ```bash
    OPERATOR_LABEL="control-plane=controller-manager"
    if [[ ${TARGET_OPERATOR_TYPE} == "rhods" ]];
    then
      OPERATOR_LABEL="name=rhods-operator"
    fi
    oc create ns ${TARGET_OPERATOR_NS}
    oc create -f custom-manifests/opendatahub/${TARGET_OPERATOR}-operators-2.x.yaml

    sleep 10
    wait_for_pods_ready "${OPERATOR_LABEL}" "${TARGET_OPERATOR_NS}"

    oc create -f custom-manifests/opendatahub/kserve-dsc.yaml
    ```

12. (optional) Deploy KServe with OpenDataHub manifests for testing purposes by using KServe KFDef.
    ```bash
    git clone git@github.com:opendatahub-io/odh-manifests.git
    rm -rf  custom-manifests/opendatahub/.cache  custom-manifests/opendatahub/kustomize /tmp/odh-manifests.gzip
    tar czvf /tmp/odh-manifests.gzip odh-manifests
    kfctl build -V -f custom-manifests/opendatahub/kfdef-kserve.yaml -d | oc create -n kserve -f -
    ```
