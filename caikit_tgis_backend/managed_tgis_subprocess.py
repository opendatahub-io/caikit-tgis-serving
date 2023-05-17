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

"""Managed TGIS subprocess with automatic fault recovery

Creates a wrapped gRPC client that knows that the gRPC server is managed as a
subprocess.
"""

# Standard
from datetime import timedelta
from enum import Enum
from threading import Lock
import os
import shlex
import subprocess
import time

# Third Party
import grpc
import requests

# First Party
from caikit.core.toolkit.errors import error_handler
import alog

# Local
from .protobufs import generation_pb2_grpc

log = alog.use_channel("TGISPROC")
error = error_handler.get(log)

class _TGISState(Enum):
    UNKNOWN = 0
    STOPPED = 1 # subprocess does not exist
    BOOTING = 2 # attempting to load the model
    READY = 3 # ready for inference requests

# pylint: disable=too-many-instance-attributes
class ManagedTGISSubprocess():
    # TODO: consider potential refactor with TGIS connection class for
    # the many instance attributes
    def __init__(self,
        model_path: str,
        grpc_port: int = 50055,
        http_port: int = 3000,
        health_poll_delay: timedelta = None,
        health_poll_timeout: timedelta = None,
        load_timeout: timedelta = None,
    ):
        # NOTE: Needs to be set before any possible errors since it's used in
        #   the destructor
        self._mutex = Lock()
        self._tgis_proc = None
        self._tgis_state: _TGISState = _TGISState.STOPPED

        if not health_poll_delay:
            health_poll_delay = timedelta(seconds=1)
        if not health_poll_timeout:
            health_poll_timeout = timedelta(seconds=1)
        if not load_timeout:
            load_timeout = timedelta(seconds=30)

        # parameters of the TGIS subprocess
        self._model_path = model_path
        self._grpc_port = grpc_port
        self._http_port = http_port
        self._health_poll_delay = health_poll_delay
        self._health_poll_timeout = health_poll_timeout
        self._load_timeout = load_timeout

        self._hostname = f"localhost:{self._grpc_port}"

        self._client = None

    def __del__(self):
        self.terminate()

    def is_ready(self) -> bool:
        return self._tgis_state == _TGISState.READY

    def get_client(self):
        """Creates a gRPC client to the subprocess

        Returns None if the subprocess is not ready and doesn't have an internal client
        """
        if self._client:
            # create a wrapped gRPC client stub that defers to self._client
            return GenerationServiceStubWrapper(self)

        log.warning("<MTS7717800W>", "get_client called with _client set to None")
        return None

    def launch(self):
        """Launch the subprocess or restart it if it exists"""
        with self._mutex:
            self._launch()

    def terminate(self):
        """Terminate the subprocess, wait for it to exit"""
        with self._mutex:
            self._ensure_terminated()

    def _launch(self):
        """Launch the subprocess or restart if it exists

        _proc_mutex should be locked before calling
        """
        self._ensure_terminated()

        log.debug("Launching TGIS subprocess for model [%s]", self._model_path)

        # Launch TGIS
        launch_cmd = " ".join(
            [
                "text-generation-launcher",
                f"--num-shard 1",
                f"--model-name {self._model_path}",
                f"--port {self._http_port}",
            ]
        )
        log.debug2("TGIS command: [%s]", launch_cmd)
        env = os.environ.copy()
        env["GRPC_PORT"] = str(self._grpc_port)
        # Long running process
        # pylint: disable=consider-using-with
        self._tgis_proc = subprocess.Popen(shlex.split(launch_cmd), env=env)
        self._tgis_state = _TGISState.BOOTING
        self._create_grpc_client()

    def _monitor_bootup():
        pass

    def _ensure_terminated(self):
        """Terminate the subprocess if it exists

        _proc_mutex should be locked before calling this
        """
        if self._tgis_state != _TGISState.STOPPED:
            self._tgis_proc.terminate()
            self._tgis_proc = None
            self._tgis_state = _TGISState.STOPPED

    def _poll_until_ready(self):
        """Polls the TGIS process until if finishes booting

        The polling is guarded with a timeout.
        """
        # Wait for the server to be ready
        start_t = time.time()
        while True:
            time.sleep(self._health_poll_delay.total_seconds())

            # check if the process stopped while waiting
            try:
                if self._tgis_proc.poll() is not None:
                    error(
                        "<MTS11752287E>",
                        RuntimeError(
                            "TGIS failed to boot up with the model. See logs for details"
                        ),
                    )
            except AttributeError:
                error(
                    "<MTS26557152E>",
                    RuntimeError(
                        "TGIS process removed while waiting for it to boot with the model"
                    ),
                )

            # see if we can get a passing health check request
            try:
                if self._health_check():
                    # TODO: should lock mutex during this state transition?
                    # if the health check passes, we are good to go
                    log.debug("TGIS booted for model [%s]", self._model_path)
                    self._tgis_state = _TGISState.READY
                    break
            except requests.exceptions.RequestException as e:
                # Ignore ConnectionErrors that are expected during boot up
                if isinstance(e, requests.exceptions.ConnectionError):
                    continue

                log.warning("<MTS96271549W>", "TGIS health check failed in _poll_until_ready: %s", e)


            # limit how long we wait before giving up
            if time.time() - start_t >= self._load_timeout.total_seconds():
                self.terminate
                error(
                    "<MTS23188245E>",
                    RuntimeError(
                        "TGIS failed to boot up with the model within the timeout"
                    ),
                )

    def _health_check(self):
        """Health check to a TGIS server"""
        if self._tgis_proc is None:
            return False

        resp = requests.get(
            f"http://localhost:{self._http_port}/health",
            timeout=self._health_poll_timeout.total_seconds(),
        )

        return resp.status_code == 200

    def _create_grpc_client(self):
        log.debug("Connecting to TGIS at [%s] INSECURE", self._hostname)
        channel = grpc.insecure_channel(self._hostname)
        self._client = generation_pb2_grpc.GenerationServiceStub(channel)

# used to create closures over the subprocess that can be called like a
# client stub, but have a auto-recovering client to the subprocess
class _wrapped_rpc():
    def __init__(self, subprocess, rpc_name):
        self.subprocess = subprocess
        self.rpc_name = rpc_name

    def __call__(self, *args, **kwargs):
        # TODO: Error handling that re-launches the subprocess if calls fail
        log.debug3("Calling wrapped RPC [%s]", self.rpc_name)
        return getattr(self.subprocess._client, self.rpc_name).__call__(*args, **kwargs)


class GenerationServiceStubWrapper():
    def __init__(self, subprocess: ManagedTGISSubprocess):
        # use the attributes of the Servicer to discover the names of the RPCs
        # the Stub creates its rpcs in __init__, so we can't use that
        rpc_names = [func for func in dir(generation_pb2_grpc.GenerationServiceServicer) if callable(getattr(generation_pb2_grpc.GenerationServiceServicer, func)) and not func.startswith("__")]

        for rpc in rpc_names:
            log.debug3("Creating wrapped RPC call for [%s]", rpc)
            setattr(self, rpc, _wrapped_rpc(subprocess, rpc))
