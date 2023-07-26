# Copyright The Caikit Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Encapsulate the creation of a TGIS Connection"""

# Standard
from dataclasses import dataclass
from typing import Optional
import os

# Third Party
import grpc

# First Party
from caikit.core.toolkit.errors import error_handler
import alog

# Local
from .protobufs import generation_pb2_grpc

log = alog.use_channel("TGCONN")
error = error_handler.get(log)


@dataclass
class TLSFilePair:
    cert_file: str
    key_file: str


@dataclass
class TGISConnection:

    # Class members
    hostname: str
    ca_cert_file: Optional[str] = None
    client_tls: Optional[TLSFilePair] = None
    _client: Optional[generation_pb2_grpc.GenerationServiceStub] = None

    # Class constants
    HOSTNAME_KEY = "hostname"
    HOSTNAME_TEMPLATE_MODEL_ID = "model_id"
    CA_CERT_FILE_KEY = "ca_cert_file"
    CLIENT_CERT_FILE_KEY = "client_cert_file"
    CLIENT_KEY_FILE_KEY = "client_key_file"

    @classmethod
    def from_config(cls, model_id: str, config: dict) -> Optional["TGISConnection"]:
        """Create an instance from a connection template and a model_id"""
        hostname = config.get(cls.HOSTNAME_KEY)
        if hostname:
            hostname = hostname.format(
                **{
                    cls.HOSTNAME_TEMPLATE_MODEL_ID: model_id,
                }
            )
            log.debug("Resolved hostname [%s] for model %s", hostname, model_id)

            # Pull out the TLS info
            ca_cert = config.get(cls.CA_CERT_FILE_KEY) or None
            client_cert = config.get(cls.CLIENT_CERT_FILE_KEY) or None
            client_key = config.get(cls.CLIENT_KEY_FILE_KEY) or None
            log.debug2("CA Cert File: %s", ca_cert)
            log.debug2("Client Cert File: %s", client_cert)
            log.debug2("Client Key File: %s", client_key)
            error.type_check(
                "<TGB73210861E>",
                str,
                allow_none=True,
                **{cls.CA_CERT_FILE_KEY: ca_cert},
            )
            error.type_check(
                "<TGB73210862E>",
                str,
                allow_none=True,
                **{cls.CLIENT_CERT_FILE_KEY: client_cert},
            )
            error.type_check(
                "<TGB73210863E>",
                str,
                allow_none=True,
                **{cls.CLIENT_KEY_FILE_KEY: client_key},
            )
            error.value_check(
                "<TGB73210864E>", ca_cert is None or os.path.isfile(ca_cert)
            )
            error.value_check(
                "<TGB73210865E>", client_cert is None or os.path.isfile(client_cert)
            )
            error.value_check(
                "<TGB73210866E>", client_key is None or os.path.isfile(client_key)
            )
            error.value_check(
                "<TGB79518571E>",
                ca_cert or (not client_cert and not client_key),
                "Cannot set client TLS ({}/{}) without CA ({})",
                cls.CLIENT_CERT_FILE_KEY,
                cls.CLIENT_KEY_FILE_KEY,
                cls.CA_CERT_FILE_KEY,
            )
            error.value_check(
                "<TGB79518572E>",
                (client_cert and client_key) or (not client_cert and not client_key),
                "Must set both {} and {} or neither",
                cls.CLIENT_CERT_FILE_KEY,
                cls.CLIENT_KEY_FILE_KEY,
            )
            client_tls = (
                TLSFilePair(cert_file=client_cert, key_file=client_key)
                if client_cert
                else None
            )
            return cls(hostname=hostname, ca_cert_file=ca_cert, client_tls=client_tls)

    @property
    def tls_enabled(self) -> bool:
        return self.ca_cert_file is not None

    @property
    def mtls_enabled(self) -> bool:
        return None not in [self.ca_cert_file, self.client_tls]

    def get_client(self) -> generation_pb2_grpc.GenerationServiceStub:
        """Get a grpc client for the connection"""
        if self._client is None:
            log.info(
                "<TGB20236231I>",
                "Initializing TGIS connection to [%s]. TLS enabled? %s. mTLS Enabled? %s",
                self.hostname,
                self.tls_enabled,
                self.mtls_enabled,
            )
            if not self.tls_enabled:
                log.debug("Connecting to TGIS at [%s] INSECURE", self.hostname)
                channel = grpc.insecure_channel(self.hostname)
            else:
                log.debug("Connecting to TGIS at [%s] SECURE", self.hostname)
                creds_kwargs = {
                    "root_certificates": self._load_tls_file(self.ca_cert_file)
                }
                if self.mtls_enabled:
                    log.debug("Enabling mTLS for TGIS connection")
                    creds_kwargs["certificate_chain"] = self._load_tls_file(
                        self.client_tls.cert_file
                    )
                    creds_kwargs["private_key"] = self._load_tls_file(
                        self.client_tls.key_file
                    )
                credentials = grpc.ssl_channel_credentials(**creds_kwargs)
                channel = grpc.secure_channel(self.hostname, credentials=credentials)
            self._client = generation_pb2_grpc.GenerationServiceStub(channel)
        return self._client

    @staticmethod
    def _load_tls_file(file_path: Optional[str]) -> Optional[bytes]:
        error.type_check(
            "<TGB20235227E>",
            str,
            allow_none=True,
            file_path=file_path,
        )
        if file_path is not None:
            error.value_check(
                "<TGB20235228E>",
                os.path.isfile(file_path),
                "Invalid TLS file path: {}",
                file_path,
            )
            with open(file_path, "rb") as handle:
                return handle.read()
