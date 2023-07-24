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

# First Party
from caikit.core.module_backends.backend_types import register_backend_type
from caikit.core.module_backends.base import BackendBase
from caikit.core.toolkit.errors import error_handler
import alog

# Local
from .managed_tgis_subprocess import ManagedTGISSubprocess
from .protobufs import generation_pb2_grpc
from .tgis_connection import TGISConnection

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
        self._model_connections = {}

        # Parse the config to see if we're managing a connection to a remote
        # TGIS instance or running a local copy
        connection_cfg = self.config.get("connection") or {}
        error.type_check("<TGB20235229E>", dict, connection=connection_cfg)
        remote_models_cfg = self.config.get("remote_models") or {}
        error.type_check("<TGB20235338E>", dict, connection=remote_models_cfg)
        local_cfg = self.config.get("local") or {}
        error.type_check("<TGB20235225E>", dict, local=local_cfg)

        # The base connection config is valid IFF there's a hostname
        conn_hname = connection_cfg.get("hostname")
        self._base_connection_cfg = connection_cfg if conn_hname else None
        error.value_check(
            "<TGB20235231E>",
            not conn_hname or ":" in self._base_connection_cfg.get("hostname", ""),
            "Invalid base configuration: {}",
            self._base_connection_cfg,
        )
        error.value_check(
            "<TGB45582311E>",
            self._base_connection_cfg is None
            or TGISConnection.from_config("__TEST__", self._base_connection_cfg)
            is not None,
            "Invalid base connection: {}",
            self._base_connection_cfg,
        )

        # Parse connection objects for all model-specific connections
        for model_id, model_conn_cfg in remote_models_cfg.items():
            model_conn = TGISConnection.from_config(model_id, model_conn_cfg)
            error.value_check(
                "<TGB90377847E>",
                model_conn is not None,
                "Invalid connection config for {}",
                model_id,
            )
            self._model_connections[model_id] = model_conn

        # We manage a local TGIS instance if there are no remote connections
        # specified as either a valid base connection or remote_connections
        self._local_tgis = not self._base_connection_cfg and not self._model_connections
        log.info("Running %s TGIS backend", "LOCAL" if self._local_tgis else "REMOTE")

        if self._local_tgis:
            log.info("<TGB20235227I>", "Managing local TGIS instance")
            self._managed_tgis = ManagedTGISSubprocess(
                grpc_port=local_cfg.get("grpc_port") or self.TGIS_LOCAL_GRPC_PORT,
                http_port=local_cfg.get("http_port") or self.TGIS_LOCAL_HTTP_PORT,
                bootup_poll_delay=local_cfg.get("health_poll_delay", 1.0),
                health_poll_timeout=local_cfg.get("health_poll_timeout", 10),
                load_timeout=local_cfg.get("load_timeout", 30),
                num_gpus=local_cfg.get("num_gpus", 1),
            )

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
        self._started = True

    def stop(self):
        """Stop backend and unload all models"""
        self._started = False
        for model_id in list(self._model_connections.keys()):
            log.debug("Unloading model %s on stop", model_id)
            self.unload_model(model_id)

    ## Backend user interface ##

    def get_connection(
        self, model_id: str, create: bool = True
    ) -> Optional[TGISConnection]:
        """Get the TGISConnection object for the given model"""
        model_conn = self._model_connections.get(model_id)
        if (
            not model_conn
            and create
            and not self.local_tgis
            and self._base_connection_cfg
        ):
            with self._mutex:
                model_conn = self._model_connections.setdefault(
                    model_id,
                    TGISConnection.from_config(model_id, self._base_connection_cfg),
                )
        return model_conn

    def get_client(self, model_id: str) -> generation_pb2_grpc.GenerationServiceStub:
        model_conn = self.get_connection(model_id)
        if model_conn is None and self.local_tgis:
            with self._mutex:
                log.debug2("Launching TGIS subprocess")
                self._managed_tgis.launch(model_id)

            log.debug2("Waiting for TGIS subprocess to become ready")
            self._managed_tgis.wait_until_ready()
            model_conn = self._managed_tgis.get_connection()
            self._model_connections[model_id] = model_conn
        error.value_check(
            "<TGB09142406E>",
            model_conn is not None,
            "Unknown model_id: {}",
            model_id,
        )

        # Mark the backend as started
        self.start()

        # Return the client to the server
        return model_conn.get_client()

    # pylint: disable=unused-argument
    def unload_model(self, model_id: str):
        """Unload the model from TGIS"""
        # If running locally, shut down the managed instance
        if self.local_tgis:
            with self._mutex:
                if self._managed_tgis:
                    self._managed_tgis.terminate()

        # Remove the connection for this model
        self._model_connections.pop(model_id, None)

    @property
    def local_tgis(self) -> bool:
        return self._local_tgis

    @property
    def model_loaded(self) -> bool:
        return not self.local_tgis or (
            self._managed_tgis is not None and self._managed_tgis.is_ready()
        )


# Register local backend
register_backend_type(TGISBackend)
