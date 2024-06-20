## Deploying an LLM embeddings model with the Caikit Standalone Serving Runtime

In this procedure you will deploy an example embeddings, [all-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2), with the Caikit-Standalone Serving runtime.

Note: The **all-MiniLM-L12-v2** has been containerized into an S3 MinIO bucket.

**Prerequisites**
- You installed the **Caikit-TGIS-Serving** stack as described in [Caikit-TGIS-Serving README file](/docs/README.md)

- Your current working directory is the `/caikit-tgis-serving/demo/kserve/` directory.

- If your embeddings model is already in an S3-like object storage (for example, AWS S3), change the connection data in the `minio-secret.yaml` and `serviceaccount-minio.yaml` as shown [here](/demo/kserve/custom-manifests/minio/). Please note that the model should be converted to a `caikit`-compatible format, see [here](/demo/kserve/built-tip.md) for instructions.

**Procedure**

1. Deploy the MinIO image that contains the embeddings model.

    Note: If your model is already in an S3-like object storage (for example, AWS S3), you can skip this step.

    Before using it, replace the default value of `image` in `custom-manifests/minio/minio.yaml` with the contanerized embeddings model.

    ```
    .
    .
    .
        image: quay.io/christinaexyou/modelmesh-minio-examples:embedding-models
    ```

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

2. Deploy the LLM embeddings model with Caikit Standalone Serving Runtime
    a. Choose a protocol to be used to invoke inferecences:
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

    ```bash
    oc apply -f ./custom-manifests/caikit/caikit-standalone/caikit-standalone-servingruntime"$INF_PROTO".yaml -n ${TEST_NS}
    ```

    d. Deploy the MinIO data connection and service account.

    ```bash
    oc apply -f ./minio-secret-current.yaml -n ${TEST_NS}
    oc create -f ./serviceaccount-minio-current.yaml -n ${TEST_NS}
    ```

    e. Deploy the inference service.

    The [ISVC template file](/demo/kserve/custom-manifests/caikit/caikit-standalone/caikit-standalone-isvc-template.yaml) shown below contains all that is needed to set up the Inference Service
    (or [gRPC ISVC template file](/demo/kserve/custom-manifests/caikit/caikit-standalone/caikit-standalone-isvc-grpc-template.yaml) for gRPC)

    Before using it, the following details have to be added:

    - `<caikit-standalone-isvc-name>` should be replaced by the name of the inference service
    - `<NameOfAServiceAccount>` should be replaced by the actual name of the Service Account
    - `proto://path/to/model` should be replaced by the actual path to the model that will run the inferences
    - `<NameOfTheServingRuntime` should be replaced by the name of the ServingRuntime

   Note:  If you followed all the steps to this point, the following code will
   create the needed Inference Service using the Minio with the all-MiniLM-L12-v2
   model and the service account that have been created in the previous steps.

   ```bash
   ISVC_NAME=caikit-standalone-isvc$INF_PROTO
   oc apply -f ./custom-manifests/caikit/caikit-standalone/"$ISVC_NAME".yaml -n ${TEST_NS}
   ```

    f. Verify the inference service's `READY` state is `True`.

    ```bash
    oc get isvc/$ISVC_NAME -n ${TEST_NS}
    ```

3. Perfrom inference using either HTTP or gRPC.

    Get ISVC_HOSTNAME:

    ```bash
    export ISVC_URL=$(oc get isvc "$ISVC_NAME" -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}')
    ```

    - http only. Perform inference with HTTP. This example uses cURL.

        a. Run the following `curl` command to transform the input sentence into an embedding vector.

        ```bash
        curl -kL -H 'Content-Type: application/json' -d '{"model_id": "all-MiniLM-L12-v2-caikit", "inputs": "first sentence"}' ${ISVC_URL}/api/v1/task/embedding
        ```

        The response should be similar to the following:

        ```json
        {
        "result": {
            "data": {
            "values": [
                -0.016814380884170532,
                0.035150256007909775,
                0.02774782106280327,
                ...
            ]
            }
        },
        "producer_id": {
            "name": "EmbeddingModule",
            "version": "0.0.1"
        },
        "input_token_count": 4
        }
        ```

        b. Run `curl` to calculate the similarity between a source sentence and a list of sentences.

        ```bash
        curl -kL -H 'Content-Type: application/json' -d '{"model_id": "all-MiniLM-L12-v2-caikit", "inputs": {
                 "source_sentence": "first sentence",
                 "sentences": ["first sentence", "another test sentence"]
                }
        }' ${ISVC_URL}/api/v1/task/sentence-similarity
        ```

        The response should be similar to the following:

        ```json
        {
        "result": {
            "scores": [
            1.0000001192092896,
            0.539454460144043
            ]
        },
        "producer_id": {
            "name": "EmbeddingModule",
            "version": "0.0.1"
        },
        "input_token_count": 13
        }
        ```
        c. Run `curl` to rerank documents according to relevance to a query sentence.

        ```bash
         curl -kL -H 'Content-Type: application/json' -d '{"model_id": "all-MiniLM-L12-v2-caikit", "inputs": {
                 "documents": [
                    {"text": "first sentence", "title": "first title"},
                    {"text": "another sentence", "more": "more attributes here"},
                    {"text": "a doc with a nested metadata", "meta": {"foo": "bar", "i": 999, "f": 12.34}}
                ],
                 "query": "first sentence"
                }}' ${ISVC_URL}/api/v1/task/rerank
        ```

        The response should be simlar to the following:

        ```json
        {
        "result": {
            "query": "first sentence",
            "scores": [
            {
                "document": {
                "text": "first sentence",
                "title": "first title"
                },
                "index": 0,
                "score": 1,
                "text": "first sentence"
            },
            {
                "document": {
                "text": "another sentence",
                "more": "more attributes here"
                },
                "index": 1,
                "score": 0.6929947137832642,
                "text": "another sentence"
            },
            {
                "document": {
                "text": "a doc with a nested metadata",
                "meta": {
                    "foo": "bar",
                    "i": 999,
                    "f": 12.34
                }
                },
                "index": 2,
                "score": 0.0041141449473798275,
                "text": "a doc with a nested metadata"
            }
            ]
        },
        "producer_id": {
            "name": "EmbeddingModule",
            "version": "0.0.1"
        },
        "input_token_count": 21
        }
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

        c. Run the following `grpcurl` command to transform the input sentence into an embedding vector.

        ```bash
        export ISVC_HOSTNAME=$(oc get isvc "$ISVC_NAME" -n ${TEST_NS} -o jsonpath='{.status.components.predictor.url}' | cut -d'/' -f 3-)

        grpcurl -insecure -d '{"text": "first sentence"}' -H "mm-model-id: all-MiniLM-L12-v2-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/EmbeddingTaskPredict
        ```

        The response should be similar to the following:

        ```json
        {
        "result": {
            "data": {
            "values": [
                -0.016814380884170532,
                0.035150256007909775,
                0.02774782106280327,
                ...
            ]
            }
        },

        ```

        d. Run the following `grpcurl` command to calculate the similarity between a source sentence and a list of sentences.

        ```bash
        grpcurl -insecure -d '{"source_sentence": "first sentence", "sentences": ["first sentence", "another test sentence"]}' -H "mm-model-id: all-MiniLM-L12-v2-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/SentenceSimilarityTaskPredict
        ```

        The response should be similar to the following:

        ```json
        {
        "result": {
            "scores": [
            1.0000001192092896,
            0.539454460144043
            ]
        },
        "producer_id": {
            "name": "EmbeddingModule",
            "version": "0.0.1"
        },
        "input_token_count": 13
        }
        ```

        e. Run `grpcurl` to rerank documents according to relevance to a query sentence.

        ```bash
        grpcurl -insecure -d '{"documents": [
                    {"text": "first sentence", "title": "first title"},
                    {"text": "another sentence", "more": "more attributes here"},
                    {"text": "a doc with a nested metadata", "meta": {"foo": "bar", "i": 999, "f": 12.34}}
                ],
                 "query": "first sentence"}' -H "mm-model-id: all-MiniLM-L12-v2-caikit" ${ISVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/RerankTaskPredict
        ```

        The response should be similar to the following:

        ```json
        {
        "result": {
            "query": "first sentence",
            "scores": [
            {
                "document": {
                "text": "first sentence",
                "title": "first title"
                },
                "index": 0,
                "score": 1,
                "text": "first sentence"
            },
            {
                "document": {
                "text": "another sentence",
                "more": "more attributes here"
                },
                "index": 1,
                "score": 0.6929947137832642,
                "text": "another sentence"
            },
            {
                "document": {
                "text": "a doc with a nested metadata",
                "meta": {
                    "foo": "bar",
                    "i": 999,
                    "f": 12.34
                }
                },
                "index": 2,
                "score": 0.0041141449473798275,
                "text": "a doc with a nested metadata"
            }
            ]
        },
        "producer_id": {
            "name": "EmbeddingModule",
            "version": "0.0.1"
        },
        "input_token_count": 21
        }
        ```