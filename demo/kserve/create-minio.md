# Create your own MinIO image

The procedures for installing and deploying the Caikit-TGIS-Serving stack describe how to deploy the [flan-t5-small](https://huggingface.co/google/flan-t5-small) model. If you would like to use your own model for testing purposes, you can create your own MinIO image.

**Prerequisite**

* You created a fork of the https://github.com/kserve/modelmesh-minio-examples GitHub repository.

* You created a model.

* You have a GitHib account.

* You have a Quay account.

**Procedure**

1. Clone the repo (replace `<YOUR-USERNAME>` with your GitHub username).
   ~~~
   git clone https://github.com/<YOUR-USERNAME>/modelmesh-minio-examples.git
   ~~~

2. Navigate to the `modelmesh-minio-examples` directory.
   ~~~
   cd modelmesh-minio-examples
   ~~~

3. Create a model directory (replace `<yourmodeldirectory>` with the name of a directory for your model).
   ~~~
   mkdir <yourmodeldirectory>
   ~~~

4. Copy your model into the `modelmesh-minio-examples/<yourmodeldirectory>` directory.

5. Edit your local `main/Dockerfile` and add lines for your model directory by following the pattern [here](https://github.com/kserve/modelmesh-minio-examples/blob/main/Dockerfile#L36) and [here](https://github.com/kserve/modelmesh-minio-examples/blob/main/Dockerfile#L59).

   For example, add these two lines in the appropriate places and replace `<YOURMODEL>` with the name of your model:
   ~~~
   COPY --chown=1000:0 <YOURMODEL> ${MODEL_DIR}/<YOURMODEL>/
   .
   .
   .
   COPY --chown=1000:0 <YOURMODEL> ${FVT_DIR}/<YOURMODEL>
   ~~~



6. Build the image (replace `<YOUR_TAG>` with a build tag, for example `v1`).
   ~~~
   podman build -t quay.io/`<YOUR_QUAY_USERNAME>`/modelmesh-minio-examples:`<YOUR_TAG>` .
   ~~~

7. Push the image to Quay.
   ~~~
   podman push quay.io/`<YOUR_QUAY_USERNAME>`/modelmesh-minio-examples:`<YOUR_TAG>`
   ~~~