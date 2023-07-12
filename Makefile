TGIS_IMAGE=quay.io/opendatahub/text-generation-inference:fast-ec05689

.PHONY: default

default:
	podman build -t caikit-tgis-serving:$$(git rev-parse --short HEAD) .


.PHONY: refresh-piplock-files

refresh-piplock-files:
	podman run --user root -it \
		--rm -v $$(pwd)/caikit:/app/caikit:z \
		$(TGIS_IMAGE) \
		/bin/bash -c " \
			cd caikit && \
			yum -y install git && pip install pipenv && \
			pipenv lock --pre \
		"
	

.PHONY: docker-test

docker-test: default
	podman run -it --rm \
		-e DTYPE_STR=float32 \
		--name caikit-tgis-serving-test-$$(git rev-parse --short HEAD) \
		--volume $$(pwd)/test:/tmp/test:z --volume $$(pwd)/utils:/tmp/utils:z \
		caikit-tgis-serving:$$(git rev-parse --short HEAD) \
		/tmp/test/smoke-test.sh


.PHONY: shell

shell: default
	podman run -it --rm \
		-e DTYPE_STR=float32 \
		--name caikit-tgis-serving-test-$$(git rev-parse --short HEAD) \
		--volume $$(pwd)/test:/tmp/test:z --volume $$(pwd)/utils:/tmp/utils:z \
		caikit-tgis-serving:$$(git rev-parse --short HEAD) \
		/bin/bash
