CAIKIT_IMAGE=caikit-tgis-serving
ENGINE ?= podman
ARCH ?= $(shell uname -m)
PLATFORM = linux/$(ARCH)

ifeq ($(ARCH),s390x)
	DOCKERFILE = Dockerfile.s390x
else
	DOCKERFILE = Dockerfile
endif

export DOCKER_DEFAULT_PLATFORM = $(PLATFORM)

.PHONY: default refresh-poetry-lock-files

default:
	$(ENGINE) build \
		--platform=$(PLATFORM) \
		-f $(DOCKERFILE) \
		-t $(CAIKIT_IMAGE):dev \
		-t $(CAIKIT_IMAGE):$$(git rev-parse --short HEAD) \
		.


shell: default
	$(ENGINE) run -it --rm \
		--platform=$(PLATFORM) \
		--name caikit-tgis-serving-test-$$(git rev-parse --short HEAD) \
		$(CAIKIT_IMAGE):dev \
		/bin/bash
