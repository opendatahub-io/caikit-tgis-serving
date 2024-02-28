#!/bin/bash
set -o pipefail
set -o nounset
set -o errtrace
# set -x   #Uncomment this to debug script.

# Deploys model for HTTP (default) or gRPC if "grpc" is passed as argument

# Check if at most one argument is passed
if [ "$#" -gt 1 ]; then
    echo "Error: at most a single argument ('http' or 'grpc') or no argument, default protocol being 'http'"
    exit 1
fi

# Default values that fit the default 'http' protocol:
INF_PROTO=""

# If we have an argument, check that it is either "http" or "grpc"
if [ "$#" -eq 1 ]; then
    if [ "$1" = "http" ]; then
	:  ### nothing to be done
    elif [ "$1" = "grpc" ]; then
	INF_PROTO="-grpc"
    else
	echo "Error: Argument must be either 'http' or 'grpc'."
	exit 1
    fi
fi

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

if ! oc get ns ${TEST_NS}
then
    oc new-project ${TEST_NS}
else
  echo "* ${TEST_NS} already exists."
fi

ISVC_NAME=caikit-tgis-isvc"${INF_PROTO}"

if oc get isvc ${ISVC_NAME} --no-headers >/dev/null; then
  echo "* The ISVC ${ISVC_NAME} already exists. Please remove it."
  exit 1
fi

echo "Creating ISVC ${ISVC_NAME}"
oc apply -f ./custom-manifests/caikit/caikit-tgis/caikit-tgis-servingruntime"${INF_PROTO}".yaml -n ${TEST_NS}

oc apply -f ${BASE_DIR}/minio-secret-current.yaml -n ${TEST_NS}
oc apply -f ${BASE_DIR}/serviceaccount-minio-current.yaml -n ${TEST_NS}

###  create the isvc
oc apply -f ./custom-manifests/caikit/caikit-tgis/"$ISVC_NAME".yaml -n ${TEST_NS}

# Resources needed to enable metrics for the model
# The metrics service needs the correct label in the `matchLabel` field. The expected value of this label is `<isvc-name>-predictor-default`
# The metrics service in this repo is configured to work with the example model. If you are deploying a different model or using a different model name, change the label accordingly.

### TBD: Following 2 line should take into account the changed names
# oc apply -f custom-manifests/metrics/caikit-metrics-service.yaml -n ${TEST_NS}
# oc apply -f custom-manifests/metrics/caikit-metrics-servicemonitor.yaml -n ${TEST_NS}
