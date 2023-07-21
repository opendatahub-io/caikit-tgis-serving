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
"""
Unit tests for the TGISConnection class
"""

# Third Party
import pytest

# Local
from caikit_tgis_backend.tgis_connection import TGISConnection


def test_happy_path_no_tls():
    conn = TGISConnection.from_config({TGISConnection.HOSTNAME_KEY: "foo.bar:1234"})
    assert conn.hostname == "foo.bar:1234"
    assert conn.ca_cert_file is None
    assert conn.client_tls is None


def test_happy_path_template():
    template_piece = "{{{}}}".format(TGISConnection.HOSTNAME_TEMPLATE_MODEL_ID)
    template = f"foo.{template_piece}.bar.{template_piece}"
    model_id = "some/model"
    conn = TGISConnection.from_template(
        model_id,
        {TGISConnection.HOSTNAME_TEMPLATE_KEY: template},
    )
    assert conn.hostname == template.format(
        **{TGISConnection.HOSTNAME_TEMPLATE_MODEL_ID: model_id}
    )


def test_happy_path_tls():
    conn = TGISConnection.from_config(
        {
            TGISConnection.HOSTNAME_KEY: "foo.bar:1234",
            TGISConnection.CA_CERT_FILE_KEY: "ca.crt",
        }
    )
    assert conn.hostname == "foo.bar:1234"
    assert conn.ca_cert_file is "ca.crt"
    assert conn.client_tls is None


def test_happy_path_mtls():
    conn = TGISConnection.from_config(
        {
            TGISConnection.HOSTNAME_KEY: "foo.bar:1234",
            TGISConnection.CA_CERT_FILE_KEY: "ca.crt",
            TGISConnection.CLIENT_CERT_FILE_KEY: "client.crt",
            TGISConnection.CLIENT_KEY_FILE_KEY: "client.key",
        }
    )
    assert conn.hostname == "foo.bar:1234"
    assert conn.ca_cert_file is "ca.crt"
    assert conn.client_tls
    assert conn.client_tls.cert_file == "client.crt"
    assert conn.client_tls.key_file == "client.key"
