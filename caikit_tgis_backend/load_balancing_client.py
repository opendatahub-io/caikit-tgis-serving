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

"""Provides a grpc client which:
- Sets client-side load-balancing options
- Polls DNS and triggers channel re-connection when new endpoints are detected
"""
# Standard
from threading import RLock
from typing import Generic, List, Optional, Set, Tuple, Type, TypeVar
import socket
import threading

# Third Party
import grpc

# First Party
from caikit.core.exceptions import error_handler
import alog

T = TypeVar("T")

log = alog.use_channel("TGCONN")
error = error_handler.get(log)


# pylint: disable=too-many-instance-attributes
class GRPCLoadBalancer(Generic[T]):
    """Wraps a grpc client class T, rebuilding the client when new IPs are available"""

    def __init__(
        self,
        client_class: Type[T],
        target: str,
        policy: str = "round_robin",
        poll_interval_s: float = 10,
        credentials: Optional[str] = None,
        channel_options: Optional[List[Tuple[str, str]]] = None,
    ):
        self.client_class = client_class
        self.target = target

        error.value_check(
            "<TGB54435438E>",
            target.count(":") == 1,
            "Target must be provided in {host}:{port} format",
        )
        self.options = channel_options or []
        self.options.append(("grpc.lb_policy_name", policy))
        self.credentials = credentials
        self._client = None
        self._client_lock = RLock()

        # Get initial IP set
        self._ip_set: Set[Tuple[str, int]] = set()

        self.poll_interval = poll_interval_s
        self._timer: Optional[threading.Timer] = None
        self._poll_for_ips()

    def __del__(self):
        if hasattr(self, "_timer") and self._timer is not None and self._timer.is_alive():
            self._timer.cancel()

    def get_client(self) -> T:
        """Returns the client. The result should not be cached as the client will be rebuilt
        periodically"""
        with self._client_lock:
            if self._client is None:
                self._rebuild_client()
            return self._client

    def _poll_for_ips(self):
        try:
            log.debug3("Polling DNS for updates to service: %s", self.target)
            new_ip_set = self._get_ip_set()

            # Create a new client only if new IP/port pairs are found
            if len(new_ip_set - self._ip_set) > 0:
                self._rebuild_client()

            self._ip_set = new_ip_set
        except Exception:  # pylint: disable=broad-exception-caught
            log.warning("Failed to poll DNS for updates", exc_info=True)

        # Cancel any duplicate timers
        if self._timer is not None and self._timer.is_alive():
            self._timer.cancel()

        # Schedule next poll
        log.debug3("Scheduling next DNS poll in %s seconds", self.poll_interval)
        self._timer = threading.Timer(self.poll_interval, self._poll_for_ips)
        self._timer.daemon = True
        self._timer.start()

    def _rebuild_client(self):
        log.debug3("Rebuilding client for service: %s", self.target)
        if self.credentials:
            channel = grpc.secure_channel(
                target=self.target, credentials=self.credentials, options=self.options
            )
        else:
            channel = grpc.insecure_channel(target=self.target, options=self.options)
        with self._client_lock:
            self._client = self.client_class(channel)

    def _get_ip_set(self) -> Set[Tuple[str, int]]:
        host, port = self.target.split(":")
        hosts = socket.getaddrinfo(host, port)
        ip_set = {host[4] for host in hosts}
        log.debug3("IPs for target: %s, %s", self.target, ip_set)
        return ip_set
