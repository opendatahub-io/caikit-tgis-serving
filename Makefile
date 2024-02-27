CAIKIT_IMAGE=caikit-tgis-serving
ENGINE ?= podman
export DOCKER_DEFAULT_PLATFORM=linux/amd64
.PHONY: default refresh-poetry-lock-files

default:
	$(ENGINE) build \
		-t $(CAIKIT_IMAGE):dev \
		-t $(CAIKIT_IMAGE):$$(git rev-parse --short HEAD) \
		.


shell: default
	$(ENGINE) run -it --rm \
		--name caikit-tgis-serving-test-$$(git rev-parse --short HEAD) \
		$(CAIKIT_IMAGE):dev \
		/bin/bash
