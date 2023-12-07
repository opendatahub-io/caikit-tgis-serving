#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

# Usage: a single! arg: "http" or "grpc" - the protocol to be used 

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
export TEST_NS=${TEST_NS}"-$INF_PROTO"

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
  
  oc apply -f ./custom-manifests/caikit/caikit-tgis-servingruntime-"$INF_PROTO".yaml -n ${TEST_NS}

  oc apply -f ${BASE_DIR}/minio-secret-current.yaml -n ${TEST_NS} 
  oc apply -f ${BASE_DIR}/serviceaccount-minio-current.yaml -n ${TEST_NS}

  ###  create the isvc.   First step: create the yaml file
  ISVC_NAME=caikit-tgis-isvc-"$INF_PROTO"
  sed "s/<protocol>/$INF_PROTO/g" ./custom-manifests/caikit/caikit-tgis-isvc-template.yaml > ./custom-manifests/caikit/"$ISVC_NAME".yaml
  oc apply -f ./custom-manifests/caikit/"$ISVC_NAME".yaml -n ${TEST_NS}

  # Resources needed to enable metrics for the model 
  # The metrics service needs the correct label in the `matchLabel` field. The expected value of this label is `<isvc-name>-predictor-default`
  # The metrics service in this repo is configured to work with the example model. If you are deploying a different model or using a different model name, change the label accordingly.

  ### TBD: Following 2 line should take into account the changed names 
  # oc apply -f custom-manifests/metrics/caikit-metrics-service.yaml -n ${TEST_NS}
  # oc apply -f custom-manifests/metrics/caikit-metrics-servicemonitor.yaml -n ${TEST_NS}
else
  echo 
  echo "* ${TEST_NS} exist. Please remove the namespace or use another namespace name"
fi
