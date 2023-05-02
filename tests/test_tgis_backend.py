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
Unit tests for TGIS backend
"""

# Standard
from contextlib import contextmanager
from typing import Optional
from unittest import mock

# Third Party
import pytest

# First Party
import caikit

# Local
from caikit_tgis_backend import TGISBackend
from caikit_tgis_backend.protobufs import generation_pb2
from tests.tgis_mock import (
    tgis_mock_insecure,
    tgis_mock_insecure_health_delay,
    tgis_mock_mtls,
    tgis_mock_tls,
)

## Helpers #####################################################################


@contextmanager
def mock_tgis_proc(poll_return: Optional[int] = None):
    with mock.patch("subprocess.Popen") as mock_proc:
        process_mock = mock.Mock()
        process_mock.configure_mock(**{"poll.return_value": poll_return})
        mock_proc.return_value = process_mock
        yield mock_proc


@pytest.fixture
def mock_tgis_proc_ok():
    with mock_tgis_proc() as proc:
        yield proc


@pytest.fixture
def mock_tgis_proc_fail():
    with mock_tgis_proc(123) as proc:
        yield proc


## Happy Path Tests ############################################################


def test_tgis_backend_is_registered():
    """Make sure that the TGIS backend is correctly registered with caikit"""
    assert (
        TGISBackend.backend_type
        in caikit.core.module_backends.backend_types.MODULE_BACKEND_TYPES
    )


def test_tgis_backend_config_valid_insecure(tgis_mock_insecure):
    """Make sure that the TGIS backend can be configured with a valid config
    blob for an insecure server
    """
    tgis_be = TGISBackend({"connection": {"hostname": tgis_mock_insecure.hostname}})
    tgis_be.get_client("").Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert tgis_be.is_started
    assert not tgis_be.tls_enabled
    assert not tgis_be.mtls_enabled


def test_tgis_backend_config_valid_tls(tgis_mock_tls):
    """Make sure that the TGIS backend can be configured with a valid config
    blob for a TLS server
    """
    tgis_be = TGISBackend(
        {
            "connection": {
                "hostname": tgis_mock_tls.hostname,
                "ca_cert_file": tgis_mock_tls.ca_cert_file,
            },
        }
    )
    tgis_be.get_client("").Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert tgis_be.is_started
    assert tgis_be.tls_enabled
    assert not tgis_be.mtls_enabled


def test_tgis_backend_config_valid_mtls(tgis_mock_mtls):
    """Make sure that the TGIS backend can be configured with a valid config
    blob for an mTLS server
    """
    tgis_be = TGISBackend(
        {
            "connection": {
                "hostname": tgis_mock_mtls.hostname,
                "ca_cert_file": tgis_mock_mtls.ca_cert_file,
                "client_cert_file": tgis_mock_mtls.client_cert_file,
                "client_key_file": tgis_mock_mtls.client_key_file,
            },
        }
    )
    tgis_be.get_client("").Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert tgis_be.is_started
    assert tgis_be.tls_enabled
    assert tgis_be.mtls_enabled


def test_stop():
    """Make sure that a working backend instance can be stopped (cov!)"""
    tgis_be = TGISBackend({"connection": {"hostname": "localhost:12345"}})
    assert not tgis_be.is_started
    tgis_be.start()
    assert tgis_be.is_started
    assert tgis_be._client is not None
    tgis_be.stop()
    assert not tgis_be.is_started
    assert tgis_be._client is None


def test_construct_run_local():
    """Make sure that when constructed without a connection, it runs in TGIS
    local mode
    """
    assert TGISBackend({}).local_tgis
    assert TGISBackend({"connection": {}}).local_tgis

    # When setting the connection to empty via the env, this is what it looks
    # like, so we want to make sure this doesn't error
    assert TGISBackend({"connection": ""}).local_tgis


def test_local_tgis_run(mock_tgis_proc_ok, tgis_mock_insecure_health_delay):
    """Test that a "local tgis" (mocked) can be booted and maintained"""
    tgis_be = TGISBackend(
        {
            "local": {
                "grpc_port": int(
                    tgis_mock_insecure_health_delay.hostname.split(":")[-1]
                ),
                "http_port": tgis_mock_insecure_health_delay.http_port,
                "health_poll_delay": 0.01,
                "health_poll_timeout": 0.01,
            },
        }
    )
    assert tgis_be.local_tgis
    assert not mock_tgis_proc_ok.called

    # Get a client handle and make sure that the server has launched
    tgis_be.get_client("").Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert mock_tgis_proc_ok.called


def test_local_tgis_unload(mock_tgis_proc_ok, tgis_mock_insecure):
    """Test that a "local tgis" (mocked) can unload and reload itself"""
    tgis_be = TGISBackend(
        {
            "local": {
                "grpc_port": int(tgis_mock_insecure.hostname.split(":")[-1]),
                "http_port": tgis_mock_insecure.http_port,
            },
        }
    )
    assert tgis_be.local_tgis
    assert not mock_tgis_proc_ok.called

    # Boot up the client
    model_id = "foobar"
    tgis_be.get_client(model_id)
    assert mock_tgis_proc_ok.called
    assert tgis_be.model_loaded

    # Unload the model
    tgis_be.unload_model(model_id)
    assert tgis_be.local_tgis
    assert not tgis_be.model_loaded

    # Load the model again by getting the client
    tgis_be.get_client(model_id)
    assert tgis_be.local_tgis
    assert tgis_be.model_loaded


def test_local_tgis_fail_start(mock_tgis_proc_fail):
    """Test that when tgis fails to boot, an exception is raised"""
    tgis_be = TGISBackend({})
    with pytest.raises(RuntimeError):
        tgis_be.get_client("")


def test_local_tgis_load_timeout(mock_tgis_proc_ok, tgis_mock_insecure_health_delay):
    """Test that if a local tgis model takes too long to load, it fails
    gracefully
    """
    tgis_be = TGISBackend(
        {
            "local": {
                "grpc_port": int(
                    tgis_mock_insecure_health_delay.hostname.split(":")[-1]
                ),
                "http_port": tgis_mock_insecure_health_delay.http_port,
                "health_poll_delay": 0.01,
                "health_poll_timeout": 0.01,
                "load_timeout": 0.05,
            },
        }
    )
    assert tgis_be.local_tgis
    assert not mock_tgis_proc_ok.called

    # (For coverage!) make sure the health probe doesn't actually run
    assert not tgis_be._tgis_proc_health_check()

    # Get a client handle and make sure that the server has launched
    with pytest.raises(RuntimeError):
        tgis_be.get_client("")
    assert mock_tgis_proc_ok.called
    assert tgis_be.local_tgis
    assert not tgis_be.model_loaded


## Failure Tests ###############################################################


def test_no_updated_config():
    """Make sure that the config for a TGISBackend cannot be updated"""
    tgis_be = TGISBackend({"connection": {"hostname": "localhost:12345"}})
    with pytest.raises(AssertionError):
        tgis_be.register_config({"connection": {"hostname": "localhost:54321"}})


def test_invalid_connection():
    """Make sure that invalid connections cause errors"""
    # All forms of invalid hostname
    with pytest.raises(TypeError):
        TGISBackend({"connection": "not a dict"})
    with pytest.raises(ValueError):
        TGISBackend({"connection": {"hostname": "localhost"}})

    # All forms of invalid TLS paths
    with pytest.raises(TypeError):
        TGISBackend(
            {
                "connection": {
                    "hostname": "localhost:12345",
                    "ca_cert_file": 12345,
                },
            }
        )
    with pytest.raises(ValueError):
        TGISBackend(
            {
                "connection": {
                    "hostname": "localhost:12345",
                    "ca_cert_file": "not there",
                },
            }
        )
