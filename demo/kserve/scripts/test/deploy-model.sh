#!/bin/bash
source "$(dirname "$(realpath "$0")")/../env.sh"

# Deploy Minio
ACCESS_KEY_ID=THEACCESSKEY

## Check if ${MINIO_NS} exist
oc get ns ${MINIO_NS}
if [[ $? ==  1 ]]
then
  oc new-project ${MINIO_NS}
  SECRET_ACCESS_KEY=$(openssl rand -hex 32)
  sed "s/<accesskey>/$ACCESS_KEY_ID/g"  ./custom-manifests/minio/minio.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" | tee ${BASE_DIR}/minio-current.yaml | oc -n ${MINIO_NS} apply -f -
  sed "s/<accesskey>/$ACCESS_KEY_ID/g" ./custom-manifests/minio/minio-secret.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" |sed "s/<minio_ns>/$MINIO_NS/g" | tee ${BASE_DIR}/minio-secret-current.yaml | oc -n ${MINIO_NS} apply -f - 
else
  SECRET_ACCESS_KEY=$(oc get pod minio  -n minio -ojsonpath='{.spec.containers[0].env[1].value}')
  sed "s/<accesskey>/$ACCESS_KEY_ID/g"  ./custom-manifests/minio/minio.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" | tee ${BASE_DIR}/minio-current.yaml 
  sed "s/<accesskey>/$ACCESS_KEY_ID/g" ./custom-manifests/minio/minio-secret.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" |sed "s/<minio_ns>/$MINIO_NS/g" | tee ${BASE_DIR}/minio-secret-current.yaml 
fi
sed "s/<minio_ns>/$MINIO_NS/g" ./custom-manifests/minio/serviceaccount-minio.yaml | tee ${BASE_DIR}/serviceaccount-minio-current.yaml 

# Deploy a sample model
oc get ns ${TEST_NS}
if [[ $? ==  1 ]]
then
  oc new-project ${TEST_NS}
  oc patch smmr/default -n istio-system --type='json' -p="[{'op': 'add', 'path': '/spec/members/-', 'value': \"$TEST_NS\"}]"

  oc apply -f ./custom-manifests/caikit/caikit-servingruntime.yaml -n ${TEST_NS}

  oc apply -f ${BASE_DIR}/minio-secret-current.yaml -n ${TEST_NS} 
  oc apply -f ${BASE_DIR}/serviceaccount-minio-current.yaml -n ${TEST_NS}

  oc apply -f ./custom-manifests/caikit/caikit-isvc.yaml -n ${TEST_NS}

  # Resources needed to enable metrics for the model 
  # The metrics service needs the correct label in the `matchLabel` field. The expected value of this label is `<isvc-name>-predictor-default`
  # The metrics service in this repo is configured to work with the example model. If you are deploying a different model or using a different model name, change the label accordingly. 
  oc apply -f custom-manifests/metrics/caikit-metrics-service.yaml -n ${TEST_NS}
  oc apply -f custom-manifests/metrics/caikit-metrics-servicemonitor.yaml -n ${TEST_NS}
else
  echo 
  echo "* ${TEST_NS} exist. Please remove the namespace or use another namespace name"
fi
