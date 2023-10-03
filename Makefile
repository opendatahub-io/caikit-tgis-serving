.PHONY: default refresh-poetry-lock-files

default:
	podman build \
		-t opendatahub/caikit:latest \
		-t opendatahub/caikit:$$(git rev-parse --short HEAD) \
		.


refresh-poetry-lock-files: default
	podman run --user root -it --rm \
		--volume $$(pwd):/app:z \
		--workdir /app  \
		opendatahub/caikit:latest \
		/bin/bash -c " \
			pip install poetry && \
			poetry update \
		"

shell: default
	podman run -it --rm \
		--name caikit-tgis-serving-test-$$(git rev-parse --short HEAD) \
		opendatahub/caikit:$$(git rev-parse --short HEAD) \
		/bin/bash
