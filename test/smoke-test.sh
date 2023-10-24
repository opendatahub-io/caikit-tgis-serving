#!/bin/bash
set -eo pipefail

function command_required() {
	local cmd
	cmd=$1
	if ! command -v $cmd &>/dev/null; then
		echo "This requires $cmd" 2>&1
		exit 1
	fi
}

command_required docker-compose
command_required git-lfs

if [[ ! -d flan-t5-small ]]; then
	git clone https://huggingface.co/google/flan-t5-small
fi

mkdir -p models/
docker-compose build

# use the container's environment to convert the model to caikit format
docker run --user root \
	-v $PWD/caikit_config:/caikit/config/ \
	-v $PWD/flan-t5-small:/mnt/flan-t5-small \
	-v $PWD/../utils:/utils \
	-v $PWD/models/:/mnt/models quay.io/opendatahub/caikit-tgis-serving:dev \
	/utils/convert.py --model-path /mnt/flan-t5-small --model-save-path /mnt/models/flan-t5-small-caikit/
echo "Saved caikit model to ./models/"

if [[ -n $CI ]]; then # Free up some space on CI
	rm -rf flan-t5-small
fi

docker-compose up -d

if [ -f grpcurl ]; then
	grpcurl=./grpcurl
elif ! command -v grpcurl >/dev/null; then
	grpcurl_version="1.8.7"
	echo "grpcurl not found, downloading v${grpcurl_version}"
	curl -sL https://github.com/fullstorydev/grpcurl/releases/download/v${grpcurl_version}/grpcurl_${grpcurl_version}_linux_x86_64.tar.gz | tar zxvf - grpcurl
	grpcurl=./grpcurl
else
	grpcurl=grpcurl
fi

max_retries=10
until ${grpcurl} -plaintext \
	-d '{"text": "At what temperature celsius does Nitrogen boil?"}' \
	-H "mm-model-id: flan-t5-small-caikit" \
	127.0.0.1:8085 \
	caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict; do
	sleep 3
	max_retries=$((max_retries - 1))
	if [[ $max_retries -le 0 ]]; then
		echo "Failed to query grpc service" >&2
		docker-compose logs
		docker-compose down
		exit 1
	fi
done

docker-compose down
echo "👍 Test successful!"
