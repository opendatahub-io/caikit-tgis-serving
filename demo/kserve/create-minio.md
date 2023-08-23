If you want to create your own minio image, what you can do is:

1. fork https://github.com/kserve/modelmesh-minio-examples
2. clone your fork
3. cd modelmesh-minio-examples
4. mkdir <yourmodeldirectory> && cd <yourmodeldirectory>
5. (previously download the model file somewhere on your machine. ) 
paste the downloaded model in this directory
6. Edit the Dockerfile to add lines for your directory following the pattern here and here
7. built the image with quay.io/<username>/modelmesh-minio-examples:<yourtag>
8. push to quay