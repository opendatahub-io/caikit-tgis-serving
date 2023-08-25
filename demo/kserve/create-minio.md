# Create your own Minio image

If you would to create your own minio image with a desired model, first fork https://github.com/kserve/modelmesh-minio-examples.

1. Clone the repo (update `<YOUR-USERNAME>`) and navigate to the correct directory.
~~~
git clone https://github.com/<YOUR-USERNAME>/modelmesh-minio-examples.git
cd modelmesh-minio-examples
~~~

2. Create your model directory (update `<yourmodeldirectory>`) 
~~~
mkdir <yourmodeldirectory> && cd <yourmodeldirectory>
~~~
and place your model there.


3. Edit the Dockerfile (located in the main directory) to add lines for your directory following the pattern [here](https://github.com/kserve/modelmesh-minio-examples/blob/main/Dockerfile#L36) and [here](https://github.com/kserve/modelmesh-minio-examples/blob/main/Dockerfile#L59).

4. Build the image:
~~~
podman build -t quay.io/`<YOUR_QUAY_USERNAME>`/modelmesh-minio-examples:`<YOUR_TAG>` .
~~~
5. Push the image to quay:
~~~
podman push quay.io/`<YOUR_QUAY_USERNAME>`/modelmesh-minio-examples:`<YOUR_TAG>`
~~~