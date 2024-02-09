#!/bin/bash
exec bash "$(dirname "$(realpath "$0")")/deploy-model.sh" grpc
