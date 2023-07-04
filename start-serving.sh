#!/bin/sh

# This script is necessary to set the hostname for TGIS

# In the case where it's local, having TGIS_HOSTNAME env variable
# unset will cause it to attempt to start TGIS locally to the
# container

TGIS_CONFIG_TEMPLATE='/caikit/config/caikit-tgis.template.yml'
TGIS_CONFIG_FILE='/caikit/config/caikit-tgis.yml'

sed "s/TGIS_HOSTNAME/${TGIS_HOSTNAME}/" "${TGIS_CONFIG_TEMPLATE}" > "${TGIS_CONFIG_FILE}"
export CONFIG_FILES="${TGIS_CONFIG_FILE}"

exec python3 -m caikit.runtime.grpc_server