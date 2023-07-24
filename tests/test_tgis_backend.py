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
from unittest import mock
import os
import time

# Third Party
import grpc
import pytest

# First Party
import caikit

# Local
from caikit_tgis_backend import TGISBackend
from caikit_tgis_backend.protobufs import generation_pb2
from tests.tgis_mock import (
    TGISMock,
    tgis_mock_insecure,
    tgis_mock_insecure_health_delay,
    tgis_mock_mtls,
    tgis_mock_tls,
)

## Helpers #####################################################################

# for convenience in managing the multiple parts of the fixture
class MockTGISFixture:
    def __init__(
        self,
        mock_popen: mock.MagicMock,
        mock_proc: mock.Mock,
        mock_tgis_server: TGISMock,
    ):
        self.mock_poppen = mock_popen
        self.mock_proc = mock_proc
        self.mock_tgis_server = mock_tgis_server
        self._configure_mock_proc()

    def server_launched(self) -> bool:
        return self.mock_poppen.called

    def set_poll_return(self, poll_return):
        self._configure_mock_proc(poll_return)

    def _configure_mock_proc(self, poll_return=None):
        self.mock_proc.configure_mock(
            **{
                "poll.return_value": poll_return,
                # calls to terminate stop the mock server
                # NOTE: return value of terminate is not used
                "terminate.side_effect": self.mock_tgis_server.stop,
            }
        )


def _launch_mock_tgis_proc_as_side_effect(mock_tgis_server: TGISMock):
    # function is passed the same args as the mock
    def side_effect(*args, **kwargs):
        mock_tgis_server.start()
        return mock.DEFAULT

    return side_effect


@pytest.fixture
def mock_tgis_fixture():
    mock_tgis = TGISMock(tls=False, mtls=False)
    with mock.patch("subprocess.Popen") as mock_popen_func:
        # when called, launch the mock_tgis server
        mock_popen_func.side_effect = _launch_mock_tgis_proc_as_side_effect(mock_tgis)
        process_mock = mock.Mock()
        mock_popen_func.return_value = process_mock
        yield MockTGISFixture(mock_popen_func, process_mock, mock_tgis)
    mock_tgis.stop()


## Conn Config #################################################################


def test_tgis_backend_is_registered():
    """Make sure that the TGIS backend is correctly registered with caikit"""
    assert hasattr(caikit.core.module_backends.backend_types, TGISBackend.backend_type)


def test_tgis_backend_config_valid_insecure(tgis_mock_insecure):
    """Make sure that the TGIS backend can be configured with a valid config
    blob for an insecure server
    """
    tgis_be = TGISBackend({"connection": {"hostname": tgis_mock_insecure.hostname}})
    model_id = "test-model"
    tgis_be.get_client(model_id).Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert tgis_be.is_started
    conn = tgis_be.get_connection(model_id)
    assert conn
    assert not conn.tls_enabled
    assert not conn.mtls_enabled


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
    model_id = "test-model"
    tgis_be.get_client(model_id).Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert tgis_be.is_started
    conn = tgis_be.get_connection(model_id)
    assert conn
    assert conn.tls_enabled
    assert not conn.mtls_enabled


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
    model_id = "test-model"
    tgis_be.get_client(model_id).Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert tgis_be.is_started
    conn = tgis_be.get_connection(model_id)
    assert conn
    assert conn.tls_enabled
    assert conn.mtls_enabled


def test_stop():
    """Make sure that a working backend instance can be stopped"""
    tgis_be = TGISBackend({"connection": {"hostname": "foo.bar.{model_id}:12345"}})
    assert not tgis_be.is_started

    # Add two models with get_client
    model_id1 = "foo"
    model_id2 = "bar"
    tgis_be.get_client(model_id1)
    tgis_be.get_client(model_id2)
    assert tgis_be.is_started
    assert tgis_be.get_connection(model_id1, False)
    assert tgis_be.get_connection(model_id2, False)

    # Stop the backend and make sure both models get removed
    tgis_be.stop()
    assert not tgis_be.is_started
    assert not tgis_be.get_connection(model_id1, False)
    assert not tgis_be.get_connection(model_id2, False)


## Local Subprocess ############################################################


def test_construct_run_local():
    """Make sure that when constructed without a connection, it runs in TGIS
    local mode
    """
    assert TGISBackend({}).local_tgis
    assert TGISBackend({"connection": {}}).local_tgis
    assert TGISBackend({"remote_models": {}}).local_tgis

    # When setting the connection to empty via the env, this is what it looks
    # like, so we want to make sure this doesn't error
    assert TGISBackend({"connection": ""}).local_tgis


def test_local_tgis_run(mock_tgis_fixture: MockTGISFixture):
    """Test that a "local tgis" (mocked) can be booted and maintained"""
    mock_tgis_server: TGISMock = mock_tgis_fixture.mock_tgis_server
    tgis_be = TGISBackend(
        {
            "local": {
                "grpc_port": int(mock_tgis_server.hostname.split(":")[-1]),
                "http_port": mock_tgis_server.http_port,
                "health_poll_delay": 0.1,
            },
        }
    )
    assert tgis_be.local_tgis
    assert not mock_tgis_fixture.server_launched()

    # Get a client handle and make sure that the server has launched
    tgis_be.get_client("").Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )
    assert mock_tgis_fixture.server_launched()


def test_local_tgis_unload(mock_tgis_fixture: MockTGISFixture):
    """Test that a "local tgis" (mocked) can unload and reload itself"""
    mock_tgis_server: TGISMock = mock_tgis_fixture.mock_tgis_server
    tgis_be = TGISBackend(
        {
            "local": {
                "grpc_port": int(mock_tgis_server.hostname.split(":")[-1]),
                "http_port": mock_tgis_server.http_port,
            },
        }
    )
    assert tgis_be.local_tgis
    assert not mock_tgis_fixture.server_launched()

    # Boot up the client
    model_id = "foobar"
    tgis_be.get_client(model_id)
    assert mock_tgis_fixture.server_launched()
    assert tgis_be.model_loaded

    # Unload the model
    tgis_be.unload_model(model_id)
    assert tgis_be.local_tgis
    assert not tgis_be.model_loaded

    # Load the model again by getting the client
    tgis_be.get_client(model_id)
    assert tgis_be.local_tgis
    assert tgis_be.model_loaded


def test_local_tgis_fail_start(mock_tgis_fixture: MockTGISFixture):
    """Test that when tgis fails to boot, an exception is raised"""
    tgis_be = TGISBackend({})
    mock_tgis_fixture.set_poll_return(1)
    with pytest.raises(RuntimeError):
        tgis_be.get_client("")


def test_local_tgis_load_timeout(mock_tgis_fixture: MockTGISFixture):
    """Test that if a local tgis model takes too long to load, it fails
    gracefully
    """
    mock_tgis_server: TGISMock = mock_tgis_fixture.mock_tgis_server
    # increase the health poll delay to greater than the load timeout
    mock_tgis_server.health_delay = 1
    tgis_be = TGISBackend(
        {
            "local": {
                "grpc_port": int(mock_tgis_server.hostname.split(":")[-1]),
                "http_port": mock_tgis_server.http_port,
                "health_poll_delay": 0.1,
                "load_timeout": 0.05,
            },
        }
    )
    assert tgis_be.local_tgis
    assert not mock_tgis_fixture.server_launched()

    # TODO: health check for coverage?
    # # (For coverage!) make sure the health probe doesn't actually run
    # assert not tgis_be._tgis_health_check()

    # Get a client handle and make sure that the server has launched
    with pytest.raises(TimeoutError):
        tgis_be.get_client("")
    assert mock_tgis_fixture.server_launched()
    assert tgis_be.local_tgis
    assert not tgis_be.model_loaded


def test_local_tgis_autorecovery(mock_tgis_fixture: MockTGISFixture):
    """Test that the backend can automatically restart the TGIS subprocess if it
    crashes
    """
    # mock the subprocess to be our mock server and to come up working
    mock_tgis_server: TGISMock = mock_tgis_fixture.mock_tgis_server
    tgis_be = TGISBackend(
        {
            "local": {
                "grpc_port": int(mock_tgis_server.hostname.split(":")[-1]),
                "http_port": mock_tgis_server.http_port,
                "health_poll_delay": 0.1,
                "health_poll_timeout": 1,
            },
        }
    )
    assert tgis_be.local_tgis

    # Get a client handle and make sure that the server has launched
    tgis_client = tgis_be.get_client("")

    assert mock_tgis_fixture.server_launched()

    # requests should succeed
    tgis_client.Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )

    # "kill" the mock server
    mock_tgis_server.stop()

    # request should fail, which triggers the auto-recovery
    with pytest.raises(grpc.RpcError):
        tgis_client.Generate(
            generation_pb2.BatchedGenerationRequest(
                requests=[
                    generation_pb2.GenerationRequest(text="Hello world"),
                ],
            ),
        )

    # wait for the server to reboot
    # pause this thread to allow the reboot thread to start
    time.sleep(0.5)
    tgis_be._managed_tgis.wait_until_ready()

    # request should succeed without recreating the client
    tgis_client.Generate(
        generation_pb2.BatchedGenerationRequest(
            requests=[
                generation_pb2.GenerationRequest(text="Hello world"),
            ],
        ),
    )


## Remote Models ###############################################################


def test_tgis_backend_config_remote_models_only():
    """Make sure that config works with only remote models"""
    tgis_be = TGISBackend(
        {
            "remote_models": {
                "foo": {"hostname": "foo:123"},
                "bar": {"hostname": "bar:123"},
            },
        }
    )
    assert not tgis_be.local_tgis
    assert tgis_be.get_connection("foo")
    assert tgis_be.get_connection("bar")
    assert not tgis_be.get_connection("baz")


def test_tgis_backend_config_remote_models_with_connection():
    """Make sure thatconfig works with only remote models and a connection
    template
    """
    tgis_be = TGISBackend(
        {
            "connection": {"hostname": "foobar.{model_id}:123"},
            "remote_models": {
                "foo": {"hostname": "foo:123"},
                "bar": {"hostname": "bar:123"},
            },
        }
    )
    assert not tgis_be.local_tgis
    assert tgis_be.get_connection("foo")
    assert tgis_be.get_connection("bar")
    baz_conn = tgis_be.get_connection("baz")
    assert baz_conn
    assert baz_conn.hostname == "foobar.baz:123"


def test_tgis_multi_model_client():
    """Make sure that TGISBackend can manage multiple simultaneous client
    objects to different running TGIS servers
    """
    prompt = "hello"
    with TGISMock(prompt_responses={prompt: "foo"}) as tgis_foo:
        with TGISMock(prompt_responses={prompt: "bar"}) as tgis_bar:
            tgis_be = TGISBackend(
                {
                    "remote_models": {
                        "foo": {"hostname": f"localhost:{tgis_foo.grpc_port}"},
                        "bar": {"hostname": f"localhost:{tgis_bar.grpc_port}"},
                    },
                }
            )
            assert not tgis_be.local_tgis
            assert tgis_be.get_connection("foo")
            assert tgis_be.get_connection("bar")
            foo_client = tgis_be.get_client("foo")
            bar_client = tgis_be.get_client("bar")
            for client, exp_res in [(foo_client, "foo"), (bar_client, "bar")]:
                resp = client.Generate(
                    generation_pb2.BatchedGenerationRequest(
                        requests=[
                            generation_pb2.GenerationRequest(text=prompt),
                        ],
                    ),
                )
                assert len(resp.responses) == 1
                assert resp.responses[0].text == exp_res


def test_tgis_backend_unload_multi_connection():
    """Make sure that connections can be unloaded individually"""
    tgis_be = TGISBackend(
        {
            "connection": {"hostname": "foobar.{model_id}:123"},
            "remote_models": {
                "foo": {"hostname": "foo:123"},
                "bar": {"hostname": "bar:123"},
            },
        }
    )
    assert tgis_be.get_connection("foo")
    assert tgis_be.get_connection("bar")
    tgis_be.unload_model("foo")
    assert not tgis_be.get_connection("foo", False)
    assert tgis_be.get_connection("bar", False)
    tgis_be.unload_model("bar")
    assert not tgis_be.get_connection("foo", False)
    assert not tgis_be.get_connection("bar", False)


## Failure Tests ###############################################################


def test_no_updated_config():
    """Make sure that the config for a TGISBackend cannot be updated"""
    tgis_be = TGISBackend({"connection": {"hostname": "localhost:12345"}})
    with pytest.raises(AssertionError):
        tgis_be.register_config({"connection": {"hostname": "localhost:54321"}})


@pytest.mark.parametrize(
    "params",
    [
        ("not a dict", TypeError),
        ({"hostname": "localhost"}, ValueError),
        ({"hostname": "foo:123", "ca_cert_file": 1}, TypeError),
        # Missing TLS Files
        ({"hostname": "foo:123", "ca_cert_file": "not there"}, ValueError),
        (
            {
                "hostname": "foo:123",
                "ca_cert_file": __file__,
                "client_cert_file": "not there",
                "client_key_file": __file__,
            },
            ValueError,
        ),
        (
            {
                "hostname": "foo:123",
                "ca_cert_file": __file__,
                "client_cert_file": __file__,
                "client_key_file": "not there",
            },
            ValueError,
        ),
        # TLS Files as dirs
        (
            {"hostname": "foo:123", "ca_cert_file": os.path.dirname(__file__)},
            ValueError,
        ),
        (
            {
                "hostname": "foo:123",
                "ca_cert_file": __file__,
                "client_cert_file": os.path.dirname(__file__),
                "client_key_file": __file__,
            },
            ValueError,
        ),
        (
            {
                "hostname": "foo:123",
                "ca_cert_file": __file__,
                "client_cert_file": __file__,
                "client_key_file": os.path.dirname(__file__),
            },
            ValueError,
        ),
        # Bad TLS File combos
        (
            {
                "hostname": "foo:123",
                "ca_cert_file": __file__,
                "client_cert_file": __file__,
            },
            ValueError,
        ),
        (
            {
                "hostname": "foo:123",
                "ca_cert_file": __file__,
                "client_key_file": __file__,
            },
            ValueError,
        ),
        (
            {
                "hostname": "foo:123",
                "client_cert_file": __file__,
                "client_key_file": __file__,
            },
            ValueError,
        ),
    ],
)
def test_invalid_connection(params):
    """Make sure that invalid connections cause errors"""
    conn, error_type = params
    with pytest.raises(error_type):
        TGISBackend({"connection": conn})
