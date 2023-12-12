# Using scripts to deploy an LLM model with the Caikit+TGIS Serving runtime

You can deploy and remove a Large Learning Model (LLM) model by running the scripts provided in the the `caikit-tgis-serving` repo. These scripts deploy a [flan-t5-small](https://huggingface.co/google/flan-t5-small) model with the Caikit+TGIS Serving runtime. This model has already been containerized into an S3 MinIO bucket. 

Note: If you prefer to deploy and remove an LLM model by using step-by-step commands (instead of scripts), see [Deploying an LLM model with the Caikit+TGIS Serving runtime](deploy-remove.md).

**Prerequisites**

* You installed the **Caikit-TGIS-Serving** image as described in the [Caikit-TGIS-Serving README file](/docs/README.md).

* You installed the scripts as described in [Script-based Installation](./scripts/README.md).

* Your current working directory is the `/caikit-tgis-serving/demo/kserve/` directory.

**Procedure**

1. Deploy a sample LLM model 

   For HTTP:
   ~~~
   ./scripts/test/deploy-model.sh
   ~~~

   For gRPC:
   ~~~
   ./scripts/test/deploy-model.sh grpc
   ~~~

2. Perform inference:

   For HTTP:
   ~~~
   ./scripts/test/http-call.sh
   ~~~

   For gRPC:
   ~~~
   ./scripts/test/grpc-call.sh
   ~~~

3. Delete the sample model:

   ~~~
   ./scripts/test/delete-model.sh
   ~~~
