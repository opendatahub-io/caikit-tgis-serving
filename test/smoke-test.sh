#!/bin/sh
set -euxo pipefail

CAIKIT_LOG_FILE=$(mktemp)
cd /caikit
./start-serving.sh &>$CAIKIT_LOG_FILE &
timeout --signal=SIGINT 30 bash -c "grep -m1 'Caikit Runtime is serving on port' <(tail -f $CAIKIT_LOG_FILE)"

cat $CAIKIT_LOG_FILE

grpcurl -plaintext -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-small-caikit" localhost:8085 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
rc=$?

kill %1
exit $rc
