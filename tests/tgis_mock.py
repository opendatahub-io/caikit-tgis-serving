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
TGIS mock
"""

# Standard
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Self
import os
import re
import tempfile
import threading
import time

# Third Party
from flask import Flask
from werkzeug.serving import make_server
import grpc
import pytest
import tls_test_tools

# First Party
import alog

# Local
from caikit_tgis_backend.protobufs import generation_pb2, generation_pb2_grpc

## Helpers #####################################################################

log = alog.use_channel("TGISM")


class FlaskServerThread(threading.Thread):
    """Utility server thread for running the TGIS health checks

    NOTE: no (m)TLS support for now
    """

    def __init__(self, app: Flask, port: int, pass_delay: float):
        super().__init__()
        self.pass_delay = pass_delay
        self.server = make_server("127.0.0.1", port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        if self.pass_delay:
            log.debug("Sleeping HTTP health check for %s", self.pass_delay)
            time.sleep(self.pass_delay)
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class TGISMockServicer(generation_pb2_grpc.GenerationServiceServicer):
    """Mock of the TGIS single-request service that does some canned things with
    the input request
    """

    def __init__(
        self,
        prompt_responses: Optional[Dict[str, str]],
        bos_token: str = "<|startoftext|>",
        sep_token: str = "<|sepoftext|>",
    ):
        """Keep track of a dict of responses for each prompt"""
        self.prompt_responses = prompt_responses or {}
        self.bos_token = bos_token
        self.sep_token = sep_token

    def set_prompt_responses(self, prompt_responses: Optional[Dict[str, str]]):
        self.prompt_responses = prompt_responses or {}

    def Generate(self, request, context):
        """For now Generate will simply add the canned suffix after"""
        return generation_pb2.BatchedGenerationResponse(
            responses=[self._gen_resp(req.text) for req in request.requests],
        )

    def _gen_resp(self, request_text: str) -> generation_pb2.GenerationResponse:
        """Generate a single response"""

        # Split the context and prompt
        request_text = re.sub("^" + re.escape(self.bos_token), "", request_text)
        parts = request_text.split(self.sep_token)
        context, prompt = parts if len(parts) == 2 else ("", request_text)

        # Look up the canned response for this prompt
        response_text = self.prompt_responses.get(prompt, "")

        return generation_pb2.GenerationResponse(
            text=response_text,
            input_token_count=len(context.split()) + len(prompt.split()),
            generated_token_count=len(response_text.split()),
            stop_reason=generation_pb2.StopReason.EOS_TOKEN,
        )


class TGISMock:
    tgis_server: grpc.Server = None
    healtcheck_server: FlaskServerThread = None
    # parameters used to connect to the server(s)
    hostname: str
    http_port: Optional[int] = None
    ca_cert: Optional[str] = None
    ca_cert_file: Optional[str] = None
    client_key: Optional[str] = None
    client_key_file: Optional[str] = None
    client_cert: Optional[str] = None
    client_cert_file: Optional[str] = None
    # holds the temp directory for TLS files
    _tls_dir = Optional[str]

    def __init__(
        self,
        tls: bool = False,
        mtls: bool = False,
        prompt_responses: Optional[Dict[str, str]] = None,
        health_delay: float = 0.0,
    ):
        # create the gRPC server
        self.tgis_server = grpc.server(ThreadPoolExecutor(max_workers=1))
        generation_pb2_grpc.add_GenerationServiceServicer_to_server(
            TGISMockServicer(prompt_responses),
            self.tgis_server,
        )

        grpc_port = tls_test_tools.open_port()
        self.hostname = f"localhost:{grpc_port}"
        if tls or mtls:
            ca_key = tls_test_tools.generate_key()[0]
            self.ca_cert = tls_test_tools.generate_ca_cert(ca_key)
            server_key, server_cert = tls_test_tools.generate_derived_key_cert_pair(ca_key)

            creds_kwargs = {}
            if mtls:
                creds_kwargs["root_certificates"] = self.ca_cert
                creds_kwargs["require_client_auth"] = True

            server_creds = grpc.ssl_server_credentials(
                [(server_key.encode("utf-8"), server_cert.encode("utf-8"))],
                **creds_kwargs,
            )
            log.debug("Adding secure port %d %s mTLS", grpc_port, "WITH" if mtls else "WITHOUT")
            self.tgis_server.add_secure_port(self.hostname, server_creds)
        else:
            self.tgis_server.add_insecure_port(self.hostname)

        # generate these now, write them out to disk in start()
        if mtls:
            self.client_key, self.client_cert = tls_test_tools.generate_derived_key_cert_pair(
                ca_key,
            )

        # create the healthcheck server
        self.http_port = tls_test_tools.open_port()
        app = Flask("tgis-health")
        @app.route("/health")
        def health():
            return "Works!"
        self.healtcheck_server = FlaskServerThread(app, self.http_port, health_delay)

    def start(self):
        self.tgis_server.start()
        self.healtcheck_server.start()

        self._tls_dir = tempfile.TemporaryDirectory()
        if self.ca_cert:
            self.ca_cert_file = os.path.join(self._tls_dir.name, "ca.pem")
            with open(self.ca_cert_file, "w") as handle:
                handle.write(self.ca_cert)

        if self.client_cert:
            self.client_cert_file = os.path.join(self._tls_dir.name, "client_cert.pem")
            with open(self.client_cert_file, "w") as handle:
                handle.write(self.client_cert)

        if self.client_key:
            self.client_key_file = os.path.join(self._tls_dir.name, "client_key.pem")
            with open(self.client_key_file, "w") as handle:
                handle.write(self.client_key)

    def stop(self):
        self.tgis_server.stop(0)
        self.healtcheck_server.shutdown()
        if self._tls_dir:
            self._tls_dir.cleanup()
            self._tls_dir = None

    # implement the context manager interface

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


@pytest.fixture
def tgis_mock_insecure() -> TGISMock:
    with TGISMock(tls=False, mtls=False) as mock:
        yield mock


@pytest.fixture
def tgis_mock_insecure_health_delay() -> TGISMock:
    with TGISMock(tls=False, mtls=False, health_delay=0.1) as mock:
        yield mock


@pytest.fixture
def tgis_mock_tls() -> TGISMock:
    with TGISMock(tls=True) as mock:
        yield mock


@pytest.fixture
def tgis_mock_mtls() -> TGISMock:
    with TGISMock(mtls=True) as mock:
        yield mock
