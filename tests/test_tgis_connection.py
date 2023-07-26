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
# Standard
from contextlib import contextmanager
import tempfile

# Third Party
import pytest

# Local
from caikit_tgis_backend.tgis_connection import TGISConnection


@contextmanager
def temp_file():
    with tempfile.NamedTemporaryFile(mode="w") as handle:
        handle.write("stub")
        yield handle.name


@pytest.fixture
def temp_ca_cert():
    with temp_file() as fname:
        yield fname


@pytest.fixture
def temp_client_cert():
    with temp_file() as fname:
        yield fname


@pytest.fixture
def temp_client_key():
    with temp_file() as fname:
        yield fname


## Happy Paths #################################################################


def test_happy_path_no_tls():
    conn = TGISConnection.from_config("", {TGISConnection.HOSTNAME_KEY: "foo.bar:1234"})
    assert conn.hostname == "foo.bar:1234"
    assert conn.ca_cert_file is None
    assert conn.client_tls is None


def test_happy_path_template():
    template_piece = "{{{}}}".format(TGISConnection.HOSTNAME_TEMPLATE_MODEL_ID)
    template = f"foo.{template_piece}.bar.{template_piece}"
    model_id = "some/model"
    conn = TGISConnection.from_config(
        model_id,
        {TGISConnection.HOSTNAME_KEY: template},
    )
    assert conn.hostname == template.format(
        **{TGISConnection.HOSTNAME_TEMPLATE_MODEL_ID: model_id}
    )


def test_happy_path_tls(temp_ca_cert):
    conn = TGISConnection.from_config(
        "",
        {
            TGISConnection.HOSTNAME_KEY: "foo.bar:1234",
            TGISConnection.CA_CERT_FILE_KEY: temp_ca_cert,
        },
    )
    assert conn.hostname == "foo.bar:1234"
    assert conn.ca_cert_file is temp_ca_cert
    assert conn.client_tls is None


def test_happy_path_mtls(temp_ca_cert, temp_client_cert, temp_client_key):
    conn = TGISConnection.from_config(
        "",
        {
            TGISConnection.HOSTNAME_KEY: "foo.bar:1234",
            TGISConnection.CA_CERT_FILE_KEY: temp_ca_cert,
            TGISConnection.CLIENT_CERT_FILE_KEY: temp_client_cert,
            TGISConnection.CLIENT_KEY_FILE_KEY: temp_client_key,
        },
    )
    assert conn.hostname == "foo.bar:1234"
    assert conn.ca_cert_file is temp_ca_cert
    assert conn.client_tls
    assert conn.client_tls.cert_file is temp_client_cert
    assert conn.client_tls.key_file is temp_client_key


# NOTE: All failure cases are exercised by test_invalid_connection in
#   test_tgis_backend.py
