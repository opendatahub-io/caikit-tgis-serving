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
import threading
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
        health_poll_timeout: timedelta = None,
        bootup_poll_delay: timedelta = None,
        load_timeout: timedelta = None,
    ):
        # NOTE: Needs to be set before any possible errors since it's used in
        #   the destructor
        self._mutex = Lock()
        self._tgis_proc = None
        self._tgis_state: _TGISState = _TGISState.STOPPED

        if not bootup_poll_delay:
            bootup_poll_delay = timedelta(seconds=1)
        if not health_poll_timeout:
            health_poll_timeout = timedelta(seconds=1)
        if not load_timeout:
            load_timeout = timedelta(seconds=30)

        # parameters of the TGIS subprocess
        self._model_path = model_path
        self._grpc_port = grpc_port
        self._http_port = http_port
        self._bootup_poll_delay = bootup_poll_delay
        self._health_poll_timeout = health_poll_timeout
        self._load_timeout = load_timeout

        self._hostname = f"localhost:{self._grpc_port}"

        # placeholders
        self._client = None
        self._bootup_thread = None
        self._bootup_exc = None

    def __del__(self):
        self.terminate()

    def is_ready(self) -> bool:
        return self._tgis_state == _TGISState.READY and self._client

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

    def wait_until_ready(self, timeout=None) -> bool:
        start_t = time.time()

        # wait for the boot monitoring thread if we have one
        if self._bootup_thread:
            self._bootup_thread.join(timeout)

        while True:
            log.debug("wait_until_ready saw state [%s]", self._tgis_state)
            if self._tgis_state == _TGISState.READY:
                return True

            if self._tgis_state == _TGISState.STOPPED:
                # raise the bootup exception if we captured one
                if self._bootup_exc:
                    raise self._bootup_exc
                return False

            if time.time() - start_t >= timeout:
                return False

            time.sleep(self._bootup_poll_delay.total_seconds())

    def terminate(self):
        """Terminate the subprocess, wait for it to exit"""
        with self._mutex:
            self._ensure_terminated()

    def _ensure_terminated(self):
        """Terminate the subprocess if it exists

        _mutex should be locked before calling this
        """
        if self._tgis_state != _TGISState.STOPPED:
            if self._tgis_proc:
                self._tgis_proc.terminate()
                self._tgis_proc = None
                # disown the bootup thread (but keep the exception if one was captured)
                self._bootup_thread = None
            log.debug("_ensure_terminated setting the state to STOPPED")
            self._tgis_state = _TGISState.STOPPED


    def _launch(self):
        """Launch the subprocess or restart if it exists

        _mutex should be locked before calling
        """
        self._ensure_terminated()

        # Launch TGIS
        launch_cmd = " ".join(
            [
                "text-generation-launcher",
                f"--num-shard 1",
                f"--model-name {self._model_path}",
                f"--port {self._http_port}",
            ]
        )
        log.debug2("Launching TGIS with command: [%s]", launch_cmd)
        env = os.environ.copy()
        env["GRPC_PORT"] = str(self._grpc_port)
        # Long running process
        # pylint: disable=consider-using-with
        self._tgis_proc = subprocess.Popen(shlex.split(launch_cmd), env=env)
        log.debug("_launch setting state to BOOTING")
        self._tgis_state = _TGISState.BOOTING
        # launch background thread to monitor the boot sequence
        # save a handle to it to record bootup errors
        self._bootup_thread = threading.Thread(target=self._monitor_bootup, daemon=True)
        self._bootup_thread.start()


    def _monitor_bootup(self):
        """Ran in a background thread to complete the BOOTING -> READY transition

        Polls the TGIS process until if finishes booting. The polling is guarded
        with a timeout.
        """
        # Wait for the server to be ready
        start_t = time.time()
        while True:
            time.sleep(self._bootup_poll_delay.total_seconds())

            # if we are not still booting, exit
            # another thread could have caused a state transition
            if self._tgis_state != _TGISState.BOOTING:
                return

            # check if the process stopped/crashed
            with self._mutex:
                try:
                    if self._tgis_proc.poll() is not None:
                        if self._tgis_state != _TGISState.STOPPED:
                            self._ensure_terminated()
                        exc = RuntimeError(
                            "TGIS failed to boot up with the model. See logs for details"
                        )
                        self._bootup_exc = exc
                        error("<MTS11752287E>", exc)
                except AttributeError:
                    if self._tgis_state != _TGISState.STOPPED:
                        self._ensure_terminated()
                    exc = RuntimeError(
                        "TGIS process terminated while waiting for it to boot with the model"
                    )
                    self._bootup_exc = exc
                    error("<MTS26557152E>", exc)

            # see if we can get a passing health check request
            try:
                if self._health_check():
                    with self._mutex:
                        # double check that we are still in the booting state
                        if not self._tgis_state == _TGISState.BOOTING:
                            return
                        # if the health check passes, we are good to go
                        self._create_grpc_client()
                        log.debug("_monitor_bootup setting state to READY")
                        self._tgis_state = _TGISState.READY
                        log.debug("TGIS booted for model [%s]", self._model_path)
                        return
            except requests.exceptions.RequestException as e:
                # Ignore ConnectionErrors that are expected during boot up
                if isinstance(e, requests.exceptions.ConnectionError):
                    continue
                log.warning("<MTS96271549W>", "TGIS health check failed in _monitor_bootup: %s", repr(e))

            # limit how long we wait before giving up
            if time.time() - start_t >= self._load_timeout.total_seconds():
                with self._mutex:
                    # double check that we are still in the booting state
                    if not self._tgis_state == _TGISState.BOOTING:
                        return

                    self._ensure_terminated()
                    exc = RuntimeError(
                        "TGIS failed to boot up with the model within the timeout"
                    )
                    self._bootup_exc = exc
                    error("<MTS23188245E>", exc)

    def _health_check(self):
        """Health check to a TGIS server"""
        if self._tgis_proc is None:
            log.debug2("_health_check called without subprocess running")
            return False

        resp = requests.get(
            f"http://localhost:{self._http_port}/health",
            timeout=self._health_poll_timeout.total_seconds(),
        )
        log.debug2("_health_check result [code=%s]", resp.status_code)

        return resp.status_code == 200

    def _create_grpc_client(self):
        log.debug("Connecting to TGIS at [%s] INSECURE", self._hostname)
        channel = grpc.insecure_channel(self._hostname)
        self._client = generation_pb2_grpc.GenerationServiceStub(channel)

    def _handle_autorecovery(self):
        """Check if the subprocess might be unhealthy and recover"""

        # if we are booting, do nothing
        if self._tgis_state == _TGISState.BOOTING:
            log.debug("Autorecovery skipped because the process is booting")
            return

        # if the health check passes, do nothing
        try:
            if self._health_check():
                log.debug("Autorecovery skipped because health check is passing")
                return
        except:
            # handle recovery below
            pass

        # restart the process
        with self._mutex:
            # double check that we aren't already booting
            if self._tgis_state == _TGISState.BOOTING:
                log.debug("Autorecovery (in mutex) skipped because the process is booting")
                return

            log.warning("Autorecovery is restarting TGIS")
            self._launch()

        return


class _MockRPCError(grpc.RpcError):
    """Mocks an RpcError but is generated outside the gRPC code"""
    def __init__(self, code):
        self.code = code

    def code(self):
        return self.code

# used to create closures over the subprocess that can be called like a
# client stub, but have a auto-recovering client to the subprocess
class _WrappedRPC():
    def __init__(self, subprocess, rpc_name):
        self.subprocess = subprocess
        self.rpc_name = rpc_name

    def __call__(self, request, context=None):
        # TODO: should wait for the subprocess up until the deadline if booting?
        if not self.subprocess.is_ready():
            raise _MockRPCError(grpc.StatusCode.UNAVAILABLE)

        try:
            log.debug3("Calling wrapped RPC [%s]", self.rpc_name)
            return getattr(self.subprocess._client, self.rpc_name).__call__(request, context)
        except grpc.RpcError as rpc_error:
            if rpc_error.code() == grpc.StatusCode.CANCELLED:
                raise rpc_error
            elif rpc_error.code() == grpc.StatusCode.UNAVAILABLE:
                # trigger a check on the process
                threading.Thread(target=self.subprocess._handle_autorecovery, daemon=True).start()
                raise rpc_error
            else:
                exc_chain = RuntimeError("Unhandled RPC error")
                exc_chain.__cause__ = rpc_error
                error("<MTS86992919W>", exc_chain)
                raise rpc_error

class GenerationServiceStubWrapper():
    def __init__(self, subprocess: ManagedTGISSubprocess):
        # use the attributes of the Servicer to discover the names of the RPCs
        # the Stub creates its rpcs as attributes in __init__, so we can't use that
        rpc_names = [func for func in dir(generation_pb2_grpc.GenerationServiceServicer) if callable(getattr(generation_pb2_grpc.GenerationServiceServicer, func)) and not func.startswith("__")]

        for rpc in rpc_names:
            log.debug3("Creating wrapped RPC call for [%s]", rpc)
            setattr(self, rpc, _WrappedRPC(subprocess, rpc))
