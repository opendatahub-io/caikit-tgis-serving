# Deploying an LLM model with the Caikit+TGIS Serving runtime

There are two options for deploying and removing an LLM model:

- By following the step-by-step commands that are described in this document.

- By running short scripts as described in [Using scripts to deploy an LLM model with the Caikit+TGIS Serving runtime](deploy-remove-scripts.md).

In this procedure, you deploy an example Large Learning Model (LLM) model, [flan-t5-small](https://huggingface.co/google/flan-t5-small), with the Caikit+TGIS Serving runtime.

Note: The **flan-t5-small** LLM model has been containerized into an S3 MinIO bucket. For information on how to containerize your own LLM model into a MinIO bucket for testing purposes, see [Create your own MinIO image](/demo/kserve/create-minio.md).

**Prerequisites**

- You installed the **Caikit-TGIS-Serving** stack as described in the [Caikit-TGIS-Serving README file](/docs/README.md).

- Your current working directory is the `/caikit-tgis-serving/demo/kserve/` directory.

- If your LLM is already in an S3-like object storage (for example, AWS S3), change the connection data in the `minio-secret.yaml` and `serviceaccount-minio.yaml` as shown [here](/demo/kserve/custom-manifests/minio/). Please note that the model should be converted to a `caikit`-compatible format, see [here][/demo/kserve/built-tip.md] for instructions.

**Procedure**

1. Deploy the MinIO image that contains the LLM model.

   Note: If your model is already in an S3-like object storage (for example, AWS S3), you can skip this step.

   Create a new namespace for MinIO and deploy it together with the service account and data connection (a secret with generated access key ID and secret access key).

   ```bash
   ACCESS_KEY_ID=admin
   SECRET_ACCESS_KEY=password
   MINIO_NS=minio
   ```

   ```bash
   oc new-project ${MINIO_NS}
   oc apply -f ./custom-manifests/minio/minio.yaml -n ${MINIO_NS}
   sed "s/<minio_ns>/$MINIO_NS/g" ./custom-manifests/minio/minio-secret.yaml | tee ./minio-secret-current.yaml | oc -n ${MINIO_NS} apply -f -
   sed "s/<minio_ns>/$MINIO_NS/g" ./custom-manifests/minio/serviceaccount-minio.yaml | tee ./serviceaccount-minio-current.yaml | oc -n ${MINIO_NS} apply -f -
   ```

2. Deploy the LLM model with Caikit+TGIS Serving runtime

   a. Choose protocol to be used to invoke inferences:
   Default protocol is HTTP (e.g., curl commands).
   If you want to use gRPC set INF_PROTO to "-grpc" value, either skip the following command lines.

   ```bash
   INF_PROTO="-grpc"
   ```

   b. Create a new namespace.

   ```bash
   export TEST_NS="kserve-demo"
   oc new-project ${TEST_NS}
   ```

   c. Create a caikit `ServingRuntime`.

      By default, it requests 4CPU and 8Gi of memory. You can adjust these values as needed.

   ```bash
   oc apply -f ./custom-manifests/caikit/caikit-tgis/caikit-tgis-servingruntime"$INF_PROTO".yaml -n ${TEST_NS}
   ```

   d. Deploy the MinIO data connection and service account.

   ```bash
   oc apply -f ./minio-secret-current.yaml -n ${TEST_NS}
   oc create -f ./serviceaccount-minio-current.yaml -n ${TEST_NS}
   ```

   e. Deploy the inference service.

   The [ISVC template file](/demo/kserve/custom-manifests/caikit/caikit-tgis/caikit-tgis-isvc-template.yaml) shown below contains all that is needed to set up the Inference Service
   (or [gRPC ISVC template file](/demo/kserve/custom-manifests/caikit/caikit-tgis/caikit-tgis-isvc-grpc-template.yaml) for gRPC)

   Before using it, the following details have to be added: 

   - `<caikit-tgis-isvc-name>` should be replaced by the name of the inference service
   - `<NameOfAServiceAccount>` should be replaced by the actual name of the Service Account
   - `proto://path/to/model` should be replaced by the actual path to the model that will run the inferences
   - `<NameOfTheServingRuntime` should be replaced by the name of the ServingRuntime

   Note:  If you followed all the steps to this point, the following code will
   create the needed Inference Service using the Minio with the flan-t5-small
   model and the service account that have been created in the previous steps.

   ```bash
   ISVC_NAME=caikit-tgis-isvc$INF_PROTO
   oc apply -f ./custom-manifests/caikit/caikit-tgis/"$ISVC_NAME".yaml -n ${TEST_NS}
   ```

   f. Verify that the inference service's `READY` state is `True`.

   ```bash
   oc get isvc/$ISVC_NAME -n ${TEST_NS}
   ```

3. Perform inference using either using HTTP or gRPC

   Compute ISVC_HOSTNAME:

   ```bash
   export ISVC_URL=$(oc get isvc "$ISVC_NAME" -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}')
   ```

   - http only. Perform inference with HTTP. This example uses cURL.

     a. Run the following `curl` command for all tokens in a single call:

     ```bash
     curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' ${ISVC_URL}/api/v1/task/text-generation
     ```

     The response should be similar to the following:

     ```json
     {
       "generated_token_count": "5",
       "text": "74 degrees F",
       "stop_reason": "EOS_TOKEN",
       "producer_id": {
         "name": "Text Generation",
         "version": "0.1.0"
       }
     }
     ```

     b. Run `curl` to generate a token stream.

     ```bash
     curl -kL -H 'Content-Type: application/json' -d '{"model_id": "flan-t5-small-caikit", "inputs": "At what temperature does Nitrogen boil?"}' ${ISVC_URL}/api/v1/task/server-streaming-text-generation
     ```

     The response should be similar to the following:

     ```json
     {
       "details": {

       }
     },
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
     ...
     ```

   - gRPC only. Perform inference with Remote Procedure Call (gPRC) commands. This example uses the [`grpcurl`](https://github.com/fullstorydev/grpcurl) command-line utility.

     a. Determine whether the HTTP2 protocol is enabled in the cluster.

     ```bash
     oc get ingresses.config/cluster -ojson | grep ingress.operator.openshift.io/default-enable-http2
     ```

     If the annotation is set to true, skip to Step 3c.

     b. If the annotation is set to either false or not present, enable it.

     ```bash
     oc annotate ingresses.config/cluster ingress.operator.openshift.io/default-enable-http2=true
     ```

     c. Run the following `grpcurl` command for all tokens in a single call:

     ```bash
     export ISVC_HOSTNAME=$(oc get isvc "$ISVC_NAME" -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}' | cut -d'/' -f 3-)
     grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
     ```

     The response should be similar to the following:

     ```json
     {
       "generated_token_count": "5",
       "text": "74 degrees F",
       "stop_reason": "EOS_TOKEN",
       "producer_id": {
         "name": "Text Generation",
         "version": "0.1.0"
       }
     }
     ```

     d. Run `grpcurl` to generate a token stream.

     ```bash
     grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/ServerStreamingTextGenerationTaskPredict
     ```

     The response should be similar to the following:

     ```json
     {
       "details": {

       }
     },
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
     ...
     ```

4. Remove the LLM model

   a. To remove (undeploy) the LLM model, delete the Inference Service and its containing namespace:

   ```bash
   oc delete isvc --all -n ${TEST_NS} --force --grace-period=0
   oc delete ns ${TEST_NS}
   ```

   b. Delete the MinIO resources by deleting the MinIO namespace.

   ```bash
   oc delete ns ${MINIO_NS}
   ```
