#!/usr/bin/env bash

# Run from the base
cd $(dirname ${BASH_SOURCE[0]})/..

TGIS_BACKEND_DIR="caikit_tgis_backend"

rm -f $TGIS_BACKEND_DIR/protobufs/*_pb2.py $TGIS_BACKEND_DIR/protobufs/*_pb2_grpc.py
python3 -m grpc_tools.protoc \
    -I $TGIS_BACKEND_DIR \
    --python_out=$TGIS_BACKEND_DIR/protobufs/ \
    --grpc_python_out=$TGIS_BACKEND_DIR/protobufs/ \
    ./$TGIS_BACKEND_DIR/*.proto
