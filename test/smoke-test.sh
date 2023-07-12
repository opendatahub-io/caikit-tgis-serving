#!/bin/sh

tempdir="$(mktemp -d)"

cd ${tempdir}

curl -sL https://github.com/fullstorydev/grpcurl/releases/download/v1.8.7/grpcurl_1.8.7_linux_x86_64.tar.gz | tar zxvf - grpcurl && \

grpcurl="${tempdir}/grpcurl"

git clone https://huggingface.co/google/flan-t5-small

/tmp/utils/convert.py --model-path flan-t5-small --model-save-path flan-t5-small-caikit

mv flan-t5-small-caikit /opt/models/

CAIKIT_LOG_FILE=$(mktemp)
cd /caikit
./start-serving.sh &>$CAIKIT_LOG_FILE &
# timeout --signal=SIGINT 30 bash -c "tail -f -n0 $CAIKIT_LOG_FILE | grep 'Caikit Runtime is serving on port'"
timeout --signal=SIGINT 30 bash -c "grep -m1 'Caikit Runtime is serving on port' <(tail -f $CAIKIT_LOG_FILE)"

cat $CAIKIT_LOG_FILE

${grpcurl} -plaintext -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" localhost:8085 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
rc=$?

kill %1

exit $rc