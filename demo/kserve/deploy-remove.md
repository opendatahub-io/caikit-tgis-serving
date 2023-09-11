# Deploying an LLM model with the Caikit+TGIS Serving runtime

There are two options for deploying and removing an LLM model:

* By following the step-by-step commands that are described in this document.

* By running short scripts as described in [Using scripts to deploy an LLM model with the Caikit+TGIS Serving runtime](deploy-remove-scripts.md).

In this procedure, you deploy an example Large Learning Model (LLM) model, [flan-t5-small](https://huggingface.co/google/flan-t5-small), with the Caikit+TGIS Serving runtime. 

Note: The **flan-t5-small** LLM model has been containerized into an S3 MinIO bucket. For information on how to containerize your own LLM model into a MinIO bucket for testing purposes, see [Create your own MinIO image](/demo/kserve/create-minio.md).

**Prerequisites**

* You installed the **Caikit-TGIS-Serving** stack as described in the [Caikit-TGIS-Serving README file](/docs/README.md).

* Your current working directory is the `/caikit-tgis-serving/demo/kserve/` directory.

*  If your LLM model is already in an S3-like object storage (for example, AWS S3), change the connection data in the `minio-secret.yaml` and `serviceaccount-minio.yaml` as shown [here](/demo/kserve/custom-manifests/minio/).


**Procedure**


1. Deploy the MinIO image that contains the LLM model.

   Note: If your model is already in an S3-like object storage (for example, AWS S3), you can skip this step.

   Create a new namespace for MinIO and deploy it together with the service account and data connection (a secret with generated access key ID and secret access key). 
   ~~~
   ACCESS_KEY_ID=admin
   SECRET_ACCESS_KEY=password
   MINIO_NS=minio
   
   oc new-project ${MINIO_NS}
   oc apply -f ./custom-manifests/minio/minio.yaml -n ${MINIO_NS}
   sed "s/<minio_ns>/$MINIO_NS/g" ./custom-manifests/minio/minio-secret.yaml | tee ./minio-secret-current.yaml | oc -n ${MINIO_NS} apply -f - 
   sed "s/<minio_ns>/$MINIO_NS/g" ./custom-manifests/minio/serviceaccount-minio.yaml | tee ./serviceaccount-minio-current.yaml | oc -n ${MINIO_NS} apply -f - 
   ~~~


2. Deploy the LLM model with Caikit+TGIS Serving runtime

   a. Create a new namespace and patch ServiceMesh related object.
   ~~~
   export TEST_NS=kserve-demo
   oc new-project ${TEST_NS}
   oc patch smmr/default -n istio-system --type='json' -p="[{'op': 'add', 'path': '/spec/members/-', 'value': \"$TEST_NS\"}]"
   ~~~

   b. Create a caikit ServingRuntime. By default, it requests 4CPU and 8Gi of memory. You can adjust these values as needed.
   ~~~
   oc apply -f ./custom-manifests/caikit/caikit-servingruntime.yaml -n ${TEST_NS}
   ~~~

   c. Deploy the MinIO data connection and service account. 
   ~~~
   oc apply -f ./minio-secret-current.yaml -n ${TEST_NS} 
   oc create -f ./serviceaccount-minio-current.yaml -n ${TEST_NS}
   ~~~

   d. Deploy the inference service. It will point to the model located in the `modelmesh-example-models/llm/models` directory.
   ~~~
   oc apply -f ./custom-manifests/caikit/caikit-isvc.yaml -n ${TEST_NS}
   ~~~

   e. Verify that the inference service's `READY` state is `True`.
   ~~~
   oc get isvc/caikit-example-isvc -n ${TEST_NS}
   ~~~

3. Perform inference with Remote Procedure Call (gPRC) commands.

   a. Determine whether the HTTP2 protocol is enabled in the cluster.
   ~~~
   oc get ingresses.config/cluster -ojson | grep ingress.operator.openshift.io/default-enable-http2
   ~~~
   If the annotation is set to true, skip to Step 3c.

   b. If the annotation is set to either false or not present, enable it.
   ~~~
   oc annotate ingresses.config/cluster ingress.operator.openshift.io/default-enable-http2=true
   ~~~

   c. Run the following `grpcurl` command for all tokens in a single call:
   ~~~
   export KSVC_HOSTNAME=$(oc get ksvc caikit-example-isvc-predictor -n ${TEST_NS} -o jsonpath='{.status.url}' | cut -d'/' -f3)
   grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
   ~~~
   The response should be similar to the following:
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

   d. Run the `grpcurl` command to generate a token stream.
   ~~~
   grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/ServerStreamingTextGenerationTaskPredict
   ~~~
   The response should be similar to the following:
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

4. Remove the LLM model

   a. To remove (undeploy) the LLM model, delete the Inference Service.

   ~~~
   oc delete isvc --all -n ${TEST_NS} --force --grace-period=0
   ~~~

   b. Delete the MinIO resources by deleting the MinIO namespace.

   ~~~
   oc delete ns ${TEST_NS} ${MINIO_NS}
   ~~~