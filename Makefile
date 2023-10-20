CAIKIT_IMAGE=quay.io/opendatahub/caikit-tgis-serving

.PHONY: default refresh-poetry-lock-files

default:
	podman build \
		-t $(CAIKIT_IMAGE):dev \
		-t $(CAIKIT_IMAGE):$$(git rev-parse --short HEAD) \
		.


refresh-poetry-lock-files: default
	podman run --user root -it --rm \
		--volume $$(pwd):/app:z \
		--workdir /app  \
		$(CAIKIT_IMAGE):dev \
		/bin/bash -c " \
			pip install poetry && \
			poetry update \
		"

shell: default
	podman run -it --rm \
		--name caikit-tgis-serving-test-$$(git rev-parse --short HEAD) \
		$(CAIKIT_IMAGE):dev \
		/bin/bash
