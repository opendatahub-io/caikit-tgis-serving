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
"""This module implements a TGIS backend configuration
"""

# Standard
from threading import Lock
from typing import Dict, Optional
import os

# Third Party
import grpc

# First Party
from caikit.core.module_backends.backend_types import register_backend_type
from caikit.core.module_backends.base import BackendBase
from caikit.core.toolkit.errors import error_handler
import alog

# Local
from .managed_tgis_subprocess import ManagedTGISSubprocess
from .protobufs import generation_pb2_grpc

log = alog.use_channel("TGISBKND")
error = error_handler.get(log)

# pylint: disable=too-many-instance-attributes
class TGISBackend(BackendBase):
    """Caikit backend with a connection to the TGIS server. If no connection
    details are given, this backend will manage an instance of the TGIS as a
    subprocess for the lifecycle of the model that needs it.

    NOTE: Currently TGIS does not support multiple models, so calls to get a
        client for a model _other_ than the first one will fail!

    TODO: To handle multi-model TGIS, we can maintain an independent process for
        each model. To do this, we'd need to dynamically generate the port and
        then yield the right client connection when a given model is requested.
    """

    TGIS_LOCAL_GRPC_PORT = 50055
    TGIS_LOCAL_HTTP_PORT = 3000

    ## Backend Interface ##

    backend_type = "TGIS"

    # TODO: consider potential refactor with TGIS connection class for
    # the many instance attributes
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)

        # NOTE: Needs to be set before any possible errors since it's used in
        #   the destructor
        self._mutex = Lock()
        self._local_tgis = None
        self._managed_tgis = None

        # Parse the config to see if we're managing a connection to a remote
        # TGIS instance or running a local copy
        connection_cfg = self.config.get("connection") or {}
        error.type_check("<TGB20235229E>", dict, connection=connection_cfg)

        local_cfg = self.config.get("local") or {}
        error.type_check("<TGB20235225E>", dict, local=local_cfg)

        if not connection_cfg or not connection_cfg.get("hostname"):
            log.info("<TGB20235227I>", "Managing local TGIS instance")
            self._local_tgis = True

            # Members that are only used when booting TGIS locally
            self._grpc_port = local_cfg.get("grpc_port") or self.TGIS_LOCAL_GRPC_PORT
            self._http_port = local_cfg.get("http_port") or self.TGIS_LOCAL_HTTP_PORT
            self._health_poll_delay = local_cfg.get("health_poll_delay", 1.0)
            self._health_poll_timeout = local_cfg.get("health_poll_timeout", 10)
            self._load_timeout = local_cfg.get("load_timeout", 30)
            self._num_gpus = local_cfg.get("num_gpus", 1)
            log.debug("Managing local TGIS with %d GPU(s)", self._num_gpus)

            # the local TGIS subprocess will be created later
            self._managed_tgis = None
        else:
            log.info("<TGB20235226I>", "Managing remote TGIS connection")
            self._local_tgis = False
            self._hostname = connection_cfg.get("hostname")
            error.type_check("<TGB20235230E>", str, hostname=self._hostname)
            error.value_check(
                "<TGB20235231E>",
                ":" in self._hostname,
                "Invalid hostname: %s",
                self._hostname,
            )

            # Pull TLS config if present
            self._ca_cert = self._load_tls_file(connection_cfg.get("ca_cert_file"))
            self._client_cert = self._load_tls_file(
                connection_cfg.get("client_cert_file")
            )
            self._client_key = self._load_tls_file(
                connection_cfg.get("client_key_file")
            )

        # Placeholder for the client
        self._client = None

    def __del__(self):
        # TODO: When adding multi-model support, we'll need to call this for
        #   each loaded model
        self.unload_model("")

    # pylint: disable=unused-argument
    def register_config(self, config: Dict) -> None:
        """Function to merge configs with existing configurations"""
        error(
            "<TGB20236213E>",
            AssertionError(
                f"{self.backend_type} backend does not support this operation"
            ),
        )

    def start(self):
        """Start backend, initializing the client"""
        self._setup_client()
        self._started = True

    def stop(self):
        """Stop backend and unload all models"""
        self._started = False
        self._client = None
        self.unload_model("")  # TODO: Clear all models for multi-model

    ## Backend user interface ##

    def get_client(self, model_path: str) -> generation_pb2_grpc.GenerationServiceStub:
        if self.local_tgis:
            # TODO: This will need to change for multi-model / multi-client support.
            # With local TGIS, limit the backend to a single managed TGIS process. This is to
            # simplify tracking of loads/unloads needed to support Model Mesh dynamics.
            with self._mutex:
                # ValueError if a TGIS process is already running
                error.value_check(
                    "<TGB27123275E>",
                    self._managed_tgis is None,
                    "TODO: The TGIS backend running with a local TGIS process "
                    + "only supports a single client currently",
                )

                self._managed_tgis = ManagedTGISSubprocess(
                    model_path=model_path,
                    grpc_port=self._grpc_port,
                    http_port=self._http_port,
                    bootup_poll_delay=self._health_poll_delay,
                    health_poll_timeout=self._health_poll_timeout,
                    load_timeout=self._load_timeout,
                    num_gpus=self._num_gpus,
                )
                log.debug2("Launching TGIS subprocess")
                self._managed_tgis.launch()

            log.debug2("Waiting for TGIS subprocess to become ready")
            self._managed_tgis.wait_until_ready()

        if not self._client:
            self._setup_client()

        # Make sure the server itself is running
        self.start()

        # Return the client to the server
        return self._client

    # pylint: disable=unused-argument
    def unload_model(self, model_path: str):
        """Unload the model from TGIS"""
        if self.local_tgis:
            with self._mutex:
                if self._managed_tgis:
                    self._managed_tgis.terminate()
                    self._managed_tgis = None
                    # reset the client so the connection is re-created
                    # the next time TGIS is launched
                    self._client = None

    @property
    def tls_enabled(self) -> bool:
        return self._ca_cert is not None

    @property
    def mtls_enabled(self) -> bool:
        return None not in [self._ca_cert, self._client_cert, self._client_key]

    @property
    def local_tgis(self) -> bool:
        return self._local_tgis

    @property
    def model_loaded(self) -> bool:
        return not self.local_tgis or (
            self._managed_tgis is not None and self._managed_tgis.is_ready()
        )

    ## Impl ##

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

    def _setup_client(self):
        if self._client is not None:
            return

        if self._local_tgis:
            self._client = self._managed_tgis.get_client()
        else:
            log.info(
                "<TGB20236231I>",
                "Initializing TGIS connection to [%s]. TLS enabled? %s. mTLS Enabled? %s",
                self._hostname,
                self.tls_enabled,
                self.mtls_enabled,
            )
            if not self.tls_enabled:
                log.debug("Connecting to TGIS at [%s] INSECURE", self._hostname)
                channel = grpc.insecure_channel(self._hostname)
            else:
                log.debug("Connecting to TGIS at [%s] SECURE", self._hostname)
                creds_kwargs = {"root_certificates": self._ca_cert}
                if self.mtls_enabled:
                    log.debug("Enabling mTLS for TGIS connection")
                    creds_kwargs["certificate_chain"] = self._client_cert
                    creds_kwargs["private_key"] = self._client_key
                credentials = grpc.ssl_channel_credentials(**creds_kwargs)
                channel = grpc.secure_channel(self._hostname, credentials=credentials)
            self._client = generation_pb2_grpc.GenerationServiceStub(channel)


# Register local backend
register_backend_type(TGISBackend)
