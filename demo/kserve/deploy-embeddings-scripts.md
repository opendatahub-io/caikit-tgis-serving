## Using scripts to deploy an embeddings model with the Caikit Standalone Serving Runtime
You can deploy and test a embedding model by running the scripts provided in the the   `caikit-tgis-serving` repo. These scripts deploy a all-MiniLM-L12-v2 model with the Caikit Standalone Serving runtime. This model has already been containerized into an S3 MinIO bucket.

**Prerequisites**
- You installed the Caikit-TGIS-Serving image as described in the Caikit-TGIS-Serving README file.

- You installed the scripts as described in Script-based Installation.

- Your current working directory is the /caikit-tgis-serving/demo/kserve/ directory.

**Procedure**
1. Deploy a sample embeddings model

   Replace the default value of `image` in `custom-manifests/minio/minio.yaml` with the contanerized embeddings model.

   ```
   .
   .
   .
        image: quay.io/christinaexyou/modelmesh-minio-examples:embedding-models
   ```

   Replace all instances of `tgis` with `standalone` in `scripts/test/deploy-model.sh`

   ```
   sed 's/tgis/standalone/g' ./scripts/test/deploy-model.sh | tee ./scripts/test/deploy-model-standalone.sh
   ```

   For HTTP:

   ```
   ./scripts/test/deploy-model-standalone.sh
   ```

   For grPC:

   ```
   ./scripts/test/deploy-model-standalone.sh grpc
   ```
2. Perform inference

   For HTTP:

   ```
   ./scripts/test/http-call-embeddings.sh
   ```

   For grPC:
   ```
   ./scripts/test/grpc-call-embeddings.sh
   ```

4. Delete the sample model

    ```
    tests/scripts/delete-model.sh
    ```
