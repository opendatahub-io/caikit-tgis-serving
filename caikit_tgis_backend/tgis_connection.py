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

# First Party
from caikit.core.toolkit.errors import error_handler
import alog

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

    # Class constants
    HOSTNAME_KEY = "hostname"
    HOSTNAME_TEMPLATE_KEY = "hostname_template"
    HOSTNAME_TEMPLATE_MODEL_ID = "model_id"
    CA_CERT_FILE_KEY = "ca_cert_file"
    CLIENT_CERT_FILE_KEY = "client_cert_file"
    CLIENT_KEY_FILE_KEY = "client_key_file"

    @classmethod
    def from_config(cls, config: dict) -> Optional["TGISConnection"]:
        """Create an instance from a connection config blob"""
        return cls._from_cfg(config.get(cls.HOSTNAME_KEY), config)

    @classmethod
    def from_template(cls, model_id: str, config: dict) -> Optional["TGISConnection"]:
        """Create an instance from a connection template and a model_id"""
        hostname_template = config.get(cls.HOSTNAME_TEMPLATE_KEY)
        if hostname_template:
            template_raw = f"{cls.HOSTNAME_TEMPLATE_MODEL_ID}"
            error.value_check(
                "<TGB76465562E>",
                template_raw in hostname_template,
                "Template [{}] does not contain [{}] as a template field (e.g. {})",
                hostname_template,
                cls.HOSTNAME_TEMPLATE_MODEL_ID,
                template_raw,
            )
            hostname = hostname_template.format(
                **{
                    cls.HOSTNAME_TEMPLATE_MODEL_ID: model_id,
                }
            )
            log.debug("Resolved hostname [%s] for model %s", hostname, model_id)
            return cls._from_cfg(hostname, config)

    @classmethod
    def _from_cfg(cls, hostname: str, config: dict) -> Optional["TGISConnection"]:
        if hostname:
            ca_cert = config.get(cls.CA_CERT_FILE_KEY) or None
            client_cert = config.get(cls.CLIENT_CERT_FILE_KEY) or None
            client_key = config.get(cls.CLIENT_KEY_FILE_KEY) or None
            log.debug2("CA Cert File: %s", ca_cert)
            log.debug2("Client Cert File: %s", client_cert)
            log.debug2("Client Key File: %s", client_key)

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
