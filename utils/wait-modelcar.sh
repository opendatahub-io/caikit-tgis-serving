#!/bin/bash

if [ "${MODEL_INIT_MODE}" = "async" ] ; then
  echo "Waiting for model files (modelcar) to be present..."
  until test -e /mnt/models; do
    sleep 1
  done

  echo "Model files are now available."
fi

echo "Starting model server..."
eval $@

