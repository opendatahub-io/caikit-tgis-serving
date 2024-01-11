#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

source "$(dirname "$(realpath "$0")")/../env.sh"

# Check if at most one argument is passed
if [ "$#" -gt 1 ]; then
    echo "Error: at most a single argument ('http' or 'grpc') or no argument, default protocol being 'http'"
    exit 1
fi

# Default values that fit the default 'http' protocol:
INF_PROTO="http"

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

# Test if ${TEST_NS} namespace already exists:
oc get ns ${TEST_NS}
if [[ $? ==  1 ]]
then
    echo "Create test namespace: ${TEST_NS}"
    oc new-project ${TEST_NS}    
else
  echo 
  echo "* ${TEST_NS} exist. Please remove the namespace or use another namespace name"
fi

oc get isvc caikit-tgis-isvc --no-headers >/dev/null
if [[ $? ==  1 ]] 
then
  echo "HTTP ISVC is creating"

  oc apply -f ./custom-manifests/caikit/caikit-tgis-servingruntime-${INF_PROTO}.yaml -n ${TEST_NS}

  oc apply -f ${BASE_DIR}/minio-secret-current.yaml -n ${TEST_NS} 
  oc apply -f ${BASE_DIR}/serviceaccount-minio-current.yaml -n ${TEST_NS}

  ###  create the isvc.   First step: create the yaml file
  ISVC_NAME=caikit-tgis-isvc-${INF_PROTO}
  oc apply -f ./custom-manifests/caikit/$ISVC_NAME.yaml -n ${TEST_NS}

  # Resources needed to enable metrics for the model 
  # The metrics service needs the correct label in the `matchLabel` field. The expected value of this label is `<isvc-name>-predictor-default`
  # The metrics service in this repo is configured to work with the example model. If you are deploying a different model or using a different model name, change the label accordingly.

  ### TBD: Following 2 line should take into account the changed names 
  # oc apply -f custom-manifests/metrics/caikit-metrics-service.yaml -n ${TEST_NS}
  # oc apply -f custom-manifests/metrics/caikit-metrics-servicemonitor.yaml -n ${TEST_NS}
else
  echo "* The ISVC already exist. Please remove the isvc or create other isvc"
fi
