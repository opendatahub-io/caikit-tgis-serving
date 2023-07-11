.PHONY: default

default:
	podman build -t caikit-tgis-serving:$$(git rev-parse --short HEAD) .


.PHONY: refresh-piplock-files
refresh-piplock-files:
	cd caikit && pipenv lock
