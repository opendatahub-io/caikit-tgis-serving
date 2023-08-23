# Deploy LLM model with Caikit+TGIS Serving runtime
In this example we will be deploying a [flan-t5-small](https://huggingface.co/google/flan-t5-small) model with Caikit+TGIS Serving runtime. The model has already been containerized into S3 minio bucket.
Before proceding, please ensure you have [installed](/docs/README.md) all pre-requisites, required operators and components.
If you would like to use short scrips instead of following step-by-step manual, please see [here](#script-based-deployment-and-removal).

Before proceeding, please make sure you are in the `/caikit-tgis-serving/demo/kserve/` directory.

## Deploy Minio containing flan-t5-small model

If you have your model in another S3-like object storage (e.g., AWS S3), you can skip this step.
We will create a new project/namespace for minio and deploy it together with service account and data connection (secret with generated access key ID and secret access key). 
~~~
ACCESS_KEY_ID=THEACCESSKEY
SECRET_ACCESS_KEY=$(openssl rand -hex 32)
MINIO_NS=minio

oc new-project ${MINIO_NS}
sed "s/<accesskey>/$ACCESS_KEY_ID/g"  ./custom-manifests/minio/minio.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" | tee ./minio-current.yaml | oc -n ${MINIO_NS} apply -f -
sed "s/<accesskey>/$ACCESS_KEY_ID/g" ./custom-manifests/minio/minio-secret.yaml | sed "s+<secretkey>+$SECRET_ACCESS_KEY+g" |sed "s/<minio_ns>/$MINIO_NS/g" | tee ./minio-secret-current.yaml | oc -n ${MINIO_NS} apply -f - 

sed "s/<minio_ns>/$MINIO_NS/g" ./custom-manifests/minio/serviceaccount-minio.yaml | tee ./serviceaccount-minio-current.yaml | oc -n ${MINIO_NS} apply -f - 
~~~
Instructions above deploy an already containerized LLM model. To containerize your own LLM model into a minio bucket for testing, follow instructions [here](/docs/create-minio.md).
## Deploy flan-t5-small model with Caikit+TGIS Serving runtime
We will first create a new namespace and patch ServiceMesh related object.
~~~
export TEST_NS=kserve-demo
oc new-project ${TEST_NS}
oc patch smmr/default -n istio-system --type='json' -p="[{'op': 'add', 'path': '/spec/members/-', 'value': \"$TEST_NS\"}]"
~~~
We will create a caikit ServingRuntime. It requests 4CPU and 8Gi of memory - please adjust if necessary.
~~~
oc apply -f ./custom-manifests/caikit/caikit-servingruntime.yaml -n ${TEST_NS}
~~~
We will deploy the minio data connectoin and service account. 
If you have your model in another S3-like object storage (e.g., AWS S3), you can change the connection data in the `minio-secret.yaml` and `serviceaccount-minio.yaml` accordingly [here](/demo/kserve/custom-manifests/minio/).
~~~
oc apply -f ./minio-secret-current.yaml -n ${TEST_NS} 
oc create -f ./serviceaccount-minio-current.yaml -n ${TEST_NS}
~~~
Here we will deploy the inference service. It will point to the model located at `modelmesh-example-models/llm/models` directory of minio.
~~~
oc apply -f ./custom-manifests/caikit/caikit-isvc.yaml -n ${TEST_NS}
~~~
Ensure that the inference service's `READY` state is `True`:
~~~
oc get isvc/caikit-example-isvc -n ${TEST_NS}
~~~

## Perform Inference with a gRPC call
In order to make a gRPC call, check if HTTP2 protocol is enabled in the cluster.
~~~
oc get ingresses.config/cluster -ojson | grep ingress.operator.openshift.io/default-enable-http2
~~~

If the annotation is either set to false or not present, enable it:
~~~
oc annotate ingresses.config/cluster ingress.operator.openshift.io/default-enable-http2=true
~~~

You can run the following grpcurl command for all tokens in a single call:
~~~
export KSVC_HOSTNAME=$(oc get ksvc caikit-example-isvc-predictor -n ${TEST_NS} -o jsonpath='{.status.url}' | cut -d'/' -f3)
grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
~~~
The expected response should be similar to:
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

### Streams of token
 You can run the following grpcurl command for streams of token:
~~~
grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/ServerStreamingTextGenerationTaskPredict
~~~
The expected response should be similar to:
~~~
{
  "details": {
    
  }
}
{
  "tokens": [
    {
      "text": "▁",
      "logprob": -1.599083423614502
    }
  ],
  "details": {
    "generated_tokens": 1
  }
}
{
  "generated_text": "74",
  "tokens": [
    {
      "text": "74",
      "logprob": -3.3622500896453857
    }
  ],
  "details": {
    "generated_tokens": 2
  }
}
....
~~~


## Remove/undeploy LLM model

To remove/undeploy a model, you can simply delete the Inference Service:

~~~
oc delete isvc --all -n ${TEST_NS} --force --grace-period=0
~~~
If necessary, delete the Minio resources by deleting the Minio namespace:
~~~
oc delete ns ${TEST_NS} ${MINIO_NS}
~~~

# Script-based model deployment and removal

## Deploy a sample LLM model

~~~
./scripts/test/deploy-model.sh
~~~

## Perform inference with a gRPC call
~~~
./scripts/test/grpc-call.sh
~~~

## Delete a sample model and Minio
~~~
./scripts/test/delete-model.sh