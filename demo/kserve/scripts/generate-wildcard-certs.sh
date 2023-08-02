#!/bin/bash
export BASE_DIR=$1
export DOMAIN_NAME=$2
export COMMON_NAME=$3

openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 \
-subj "/O=Example Inc./CN=${DOMAIN_NAME}" \
-keyout $BASE_DIR/root.key \
-out $BASE_DIR/root.crt

openssl req -nodes -newkey rsa:2048 \
-subj "/CN=*.${COMMON_NAME}/O=Example Inc." \
-keyout $BASE_DIR/wildcard.key \
-out $BASE_DIR/wildcard.csr

openssl x509 -req -days 365 -set_serial 0 \
-CA $BASE_DIR/root.crt \
-CAkey $BASE_DIR/root.key \
-in $BASE_DIR/wildcard.csr \
-out $BASE_DIR/wildcard.crt

openssl x509 -in ${BASE_DIR}/wildcard.crt -text
