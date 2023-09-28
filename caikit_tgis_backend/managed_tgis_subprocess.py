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

"""Provides the ManagedTGISSubprocess class"""

# Standard
from enum import Enum
from threading import Lock
from typing import Optional
import os
import shlex
import subprocess
import threading
import time

# Third Party
import grpc
import requests

# First Party
from caikit.core.exceptions import error_handler
import alog

# Local
from .protobufs import generation_pb2_grpc
from .tgis_connection import TGISConnection

log = alog.use_channel("TGISPROC")
error = error_handler.get(log)


class _TGISState(Enum):
    STOPPED = 0  # subprocess does not exist
    BOOTING = 1  # attempting to load the model
    READY = 2  # ready for inference requests


# pylint: disable=too-many-instance-attributes
class ManagedTGISSubprocess:
    """Managed TGIS subprocess with automatic failure recovery

    Creates a wrapped gRPC client that knows that the gRPC server is managed as a
    subprocess. When the client observes errors, it can trigger a restart of the
    subprocess.
    """

    def __init__(
        self,
        grpc_port: int = 50055,
        http_port: int = 3000,
        health_poll_timeout: float = 1,
        bootup_poll_delay: float = 1,
        load_timeout: float = 30,
        num_gpus: int = 1,
        prompt_dir: Optional[str] = None,
    ):
        """Create a ManagedTGISSubprocess

        Args:
            grpc_port (int, optional): port TGIS will listen on for gRPC requests.
                Defaults to 50055.
            http_port (int, optional): port TGIS will listen on for HTTP requests.
                Defaults to 3000.
            health_poll_timeout (float, optional): number of seconds to wait for a
                health check request. Defaults to 1.
            bootup_poll_delay (float, optional): number of seconds between health
                checks during bootup. Defaults to 1.
            load_timeout (float, optional): number of seconds to wait for TGIS to
                boot before cancelling. Defaults to 30.
            num_gpus (int): The number of GPUs to use for this instance
            prompt_dir (Optional[str]): A directory with write access to use as
                the prompt cache for this instance
        """
        # parameters of the TGIS subprocess
        self._model_id = None
        self._grpc_port = grpc_port
        self._http_port = http_port
        self._bootup_poll_delay = bootup_poll_delay
        self._health_poll_timeout = health_poll_timeout
        self._load_timeout = load_timeout
        self._num_gpus = num_gpus
        self._prompt_dir = prompt_dir
        error.value_check(
            "<TGB54435438E>", prompt_dir is None or os.path.isdir(prompt_dir)
        )
        log.debug("Managing local TGIS with %d GPU(s)", self._num_gpus)

        self._hostname = f"localhost:{self._grpc_port}"
        self._mutex = Lock()
        self._tgis_state: _TGISState = _TGISState.STOPPED
        self._tgis_proc = None
        self._tgis_client = None
        self._wrapped_client = None
        self._bootup_thread = None
        self._bootup_exc = None

    def __del__(self):
        self.terminate()

    def is_ready(self) -> bool:
        """Return true if a request can be propagated to the subprocess"""
        return self._tgis_state == _TGISState.READY and self._tgis_client

    def get_connection(self):
        """Get the TGISConnection object for this local connection"""
        return TGISConnection(
            hostname=self._hostname,
            model_id=self._model_id,
            prompt_dir=self._prompt_dir,
            _client=self.get_client(),
        )

    def get_client(self):
        """Creates a gRPC client to the subprocess

        Returns None if the subprocess is not ready and doesn't have an internal client
        """
        if self._wrapped_client:
            return self._wrapped_client

        if self._tgis_client:
            # create a wrapped gRPC client stub that defers to self._tgis_client
            self._wrapped_client = AutoRecoveringGenerationServiceStub(self)
            return self._wrapped_client

        log.warning("<MTS7717800W>", "get_client called with _tgis_client set to None")
        return None

    def launch(self, model_path: Optional[str] = None):
        """Launch the subprocess or restart it if it already exists"""
        with self._mutex:
            if model_path:
                self._model_id = model_path
            self._launch()

    def wait_until_ready(self, timeout: float = None):
        """Wait for TGIS to be ready or raise an exception

        Args:
            timeout (float, optional): maximum duration to wait for. Defaults to the load_timeout.

        Raises:
            Exception: If TGIS is detected to be down, the exception that caused
                the most recent TGIS restart
            TimeoutError: If the timeout is reached
        """
        if timeout is None:
            timeout = self._load_timeout

        start_t = time.time()

        if self._bootup_thread:
            self._bootup_thread.join(timeout=timeout)

        while True:
            log.debug("wait_until_ready saw state [%s]", self._tgis_state)
            if self._tgis_state == _TGISState.READY:
                return

            if self._tgis_state == _TGISState.STOPPED:
                # raise the bootup exception if we captured one
                if self._bootup_exc:
                    raise self._bootup_exc
                return

            if time.time() - start_t >= timeout:
                raise TimeoutError

            time.sleep(self._bootup_poll_delay)

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
                # disown the bootup thread
                # (but keep self._bootup_exc if one is captured)
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
                f"--num-shard {self._num_gpus}",
                f"--model-name {self._model_id}",
                f"--port {self._http_port}",
            ]
        )
        log.debug2("Launching TGIS with command: [%s]", launch_cmd)
        env = os.environ.copy()
        env["GRPC_PORT"] = str(self._grpc_port)
        if self._prompt_dir is not None:
            env["PREFIX_STORE_PATH"] = self._prompt_dir

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
            time.sleep(self._bootup_poll_delay)

            # if we are not still booting, exit
            # another thread could have caused a state transition
            if self._tgis_state != _TGISState.BOOTING:
                return

            # check if the process stopped/crashed
            with self._mutex:
                if self._tgis_proc is None:
                    exc = RuntimeError(
                        "TGIS process terminated while waiting for it to boot with the model"
                    )
                    self._bootup_exc = exc
                    error("<MTS26557152E>", exc)

                if self._tgis_proc.poll() is not None:
                    self._ensure_terminated()
                    exc = RuntimeError(
                        "TGIS failed to boot up with the model. See logs for details"
                    )
                    self._bootup_exc = exc
                    error("<MTS11752287E>", exc)

            # see if we can get a passing health check request
            try:
                if self._health_check():
                    with self._mutex:
                        # double check that we are still in the booting state
                        if self._tgis_state != _TGISState.BOOTING:
                            return
                        # if the health check passes, we are good to go
                        self._create_grpc_client()
                        log.debug("_monitor_bootup setting state to READY")
                        self._tgis_state = _TGISState.READY
                        log.debug("TGIS booted for model [%s]", self._model_id)
                        return
            except requests.exceptions.RequestException as e:
                # Ignore ConnectionErrors that are expected during boot up
                if isinstance(e, requests.exceptions.ConnectionError):
                    log.debug2("Ignoring ConnectionError from _health_check")
                    continue

                log.warning(
                    "<MTS96271549W>",
                    "TGIS health check failed in _monitor_bootup: %s",
                    repr(e),
                )

            # limit how long we wait before giving up
            if time.time() - start_t >= self._load_timeout:
                with self._mutex:
                    # double check that we are still in the booting state
                    if self._tgis_state != _TGISState.BOOTING:
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

        log.debug2(
            "sending health probe request with timeout [%s]", self._health_poll_timeout
        )
        resp = requests.get(
            f"http://localhost:{self._http_port}/health",
            timeout=self._health_poll_timeout,
        )
        log.debug2("_health_check result [code=%s]", resp.status_code)

        return resp.status_code == 200

    def _create_grpc_client(self):
        """Creates a new grpc client for TGIS"""
        log.debug("Connecting to TGIS at [%s] INSECURE", self._hostname)
        channel = grpc.insecure_channel(self._hostname)
        self._tgis_client = generation_pb2_grpc.GenerationServiceStub(channel)

    def _handle_autorecovery(self):
        """Check if the subprocess is unhealthy and restart it"""

        # if we are booting, do nothing
        if self._tgis_state == _TGISState.BOOTING:
            log.debug("Autorecovery skipped because the process is booting")
            return

        # if the health check passes, do nothing
        try:
            if self._health_check():
                log.debug("Autorecovery skipped because health check is passing")
                return
        except requests.exceptions.RequestException as e:
            log.debug("Autorecovery health check failed: %s", repr(e))
            # handle recovery below

        # restart the process
        with self._mutex:
            # double check that we aren't already booting
            if self._tgis_state == _TGISState.BOOTING:
                log.debug(
                    "Autorecovery (in mutex) skipped because the process is booting"
                )
                return

            log.warning("Autorecovery is restarting TGIS")
            self._launch()


class _MockRPCError(grpc.RpcError):
    """Mocks an RpcError but is generated outside the gRPC code"""

    def __init__(self, code):
        self._code = code

    def code(self):
        return self._code


# used to create closures over the subprocess that can be called like a
# client stub, but have a auto-recovering client to the subprocess
class _FaultDetectingRPC:
    """Wrap a generated gRPC client to restart the gRPC server if there are errors

    Raises:
        _MockRPCError: A grpc.RpcError with a code
        grpc.RPcError: An error generated from the wrapped gRPC client
    """

    def __init__(self, managed_tgis: ManagedTGISSubprocess, rpc_name: str):
        self.managed_tgis = managed_tgis
        self.rpc_name = rpc_name

    def __call__(self, request, context=None):
        """Send a gRPC request

        Args:
            request (gRPC message): message to send
            context (gRPC context, optional): gRPC request context. Defaults to None.

        Raises:
            _MockRPCError: _description_
            grpc.RPcError: An error generated from the wrapped gRPC client

        Returns:
            gRPC response
        """

        if not self.managed_tgis.is_ready():
            # TODO: should wait for the subprocess up until the deadline if booting?
            raise _MockRPCError(grpc.StatusCode.UNAVAILABLE)

        try:
            log.debug3("Calling wrapped RPC [%s]", self.rpc_name)
            return getattr(self.managed_tgis._tgis_client, self.rpc_name).__call__(
                request, context
            )
        except grpc.RpcError as rpc_error:
            log.warning(
                "<MTS52181395W>", "Handling RPC error with code [%s]:", rpc_error.code()
            )

            # error codes that trigger an auto-recovery check
            if rpc_error.code() in [
                grpc.StatusCode.ABORTED,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                grpc.StatusCode.INTERNAL,
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.UNKNOWN,
            ]:
                log.debug("Triggering an auto-recovery check")
                threading.Thread(
                    target=self.managed_tgis._handle_autorecovery, daemon=True
                ).start()

            raise rpc_error


class AutoRecoveringGenerationServiceStub:
    """GenerationServiceStub that will restart TGIS if it is unhealthy"""

    def __init__(self, managed_tgis: ManagedTGISSubprocess):
        # use the attributes of the Servicer to discover the names of the RPCs
        # the Stub creates its rpcs as attributes in __init__, so we can't use that
        rpc_names = [
            func
            for func in dir(generation_pb2_grpc.GenerationServiceServicer)
            if callable(getattr(generation_pb2_grpc.GenerationServiceServicer, func))
            and not func.startswith("__")
        ]

        # create closures over the ManagedTGISSubprocess that act as RPCs
        for rpc_name in rpc_names:
            log.debug3("Creating wrapped RPC call for [%s]", rpc_name)
            setattr(self, rpc_name, _FaultDetectingRPC(managed_tgis, rpc_name))
