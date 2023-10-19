#!/bin/bash
set -euo pipefail

function command_required() {
	local cmd
	cmd=$1
	if ! command -v $cmd &>/dev/null; then
		echo "This requires $cmd" 2>&1
		exit 1
	fi
}

command_required python3
command_required docker-compose
command_required git-lfs

if [[ ! -d .venv ]]; then
	python -m venv .venv || (echo "Failed to create venv. Quitting." >&2 && exit 1)
fi
source .venv/bin/activate || (echo "Could not source venv. Quitting" >&2 && exit 1)

pip install git+https://github.com/caikit/caikit-nlp
if [[ ! -d flan-t5-small ]]; then
	git clone https://huggingface.co/google/flan-t5-small
fi

mkdir -p models/
../utils/convert.py --model-path flan-t5-small --model-save-path models/flan-t5-small-caikit/

echo "Saved caikit model to ./models/"

docker-compose up -d

max_retries=10
until grpcurl -plaintext \
	-d '{"text": "At what temperature celsius does Nitrogen boil?"}' \
	-H "mm-model-id: flan-t5-small-caikit" \
	127.0.0.1:8085 \
	caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict; do
	sleep 3
	max_retries=$((max_retries - 1))
	if [[ $max_retries -le 0 ]]; then
		echo "Failed to query grpc service" >&2
		docker-compose down
		exit 1
	fi
done

docker-compose down
echo "👍 Test successful!"
