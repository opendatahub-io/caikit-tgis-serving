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
from functools import partial
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
class GRPCLoadBalancerProxy(Generic[T]):
    """Proxies a grpc client class T, reconnecting the client when new IPs are available"""

    def __init__(
        self,
        client_class: Type[T],
        target: str,
        policy: str = "round_robin",
        poll_interval_s: Optional[float] = 10,
        credentials: Optional[str] = None,
        channel_options: Optional[List[Tuple[str, str]]] = None,
    ):
        # Ensure that self._client always exists. It is required by the __getattr__ proxying
        self._client = None
        self.client_class = client_class
        self.target = target

        error.value_check(
            "<TGB54435438E>",
            target.count(":") == 1,
            "Target must be provided in {host}:{port} format",
        )

        error.value_check(
            "<TGB01133969E>",
            poll_interval_s is None or poll_interval_s >= 0,
            "poll_interval_s should be > 0",
        )

        channel_options = channel_options or []
        # pylint: disable=line-too-long
        # Cite: https://grpc.github.io/grpc/core/group__grpc__arg__keys.html#ga72c2b475e218ecfd36bb7d3551d0295b
        channel_options.append(("grpc.lb_policy_name", policy))

        # Save a partial for re-constructing channels later
        if credentials:
            log.debug3("Creating load-balancing client with secure channel")
            self.channel_partial = partial(
                grpc.secure_channel,
                target=self.target,
                options=channel_options,
                credentials=credentials,
            )
        else:
            log.debug3("Creating load-balancing client with insecure channel")
            self.channel_partial = partial(
                grpc.insecure_channel, target=self.target, options=channel_options
            )

        # Build the client once
        self._client = self.client_class(self.channel_partial())

        # Get initial IP set
        self._ip_set: Set[Tuple[str, int]] = set()

        self.poll_interval = poll_interval_s
        self._timer: Optional[threading.Timer] = None
        self._poll_lock = threading.Lock()
        self._shutdown = False
        if self.poll_interval:
            log.debug2(
                "Enabling DNS poll interval every %f seconds", self.poll_interval
            )
            self._dns_poll()

    def __del__(self):
        """Attempt a bit of cleanup on GC"""
        self.shutdown_dns_poll()

    def __getattr__(self, item):
        """Proxies self._client so that self is the grpc client"""
        return getattr(self._client, item)

    @property
    def client(self) -> T:
        """Syntactic sugar to assert that we are in fact a type T.

        Returns the client instance (self). The channel that this client holds will periodically be
        replaced when DNS polling indicates new hosts are available."""
        return self

    def shutdown_dns_poll(self):
        """Shuts down the internal DNS poll.
        This should happen on garbage collection, and is exposed here to explicitly control the
        polling lifecycle if needed."""
        self._shutdown = True
        if (
            hasattr(self, "_timer")
            and self._timer is not None
            and self._timer.is_alive()
        ):
            self._timer.cancel()

    def _dns_poll(self):
        """Run the internal DNS poll. This method re-schedules itself until shutdown_dns_poll
        is called."""
        if self._shutdown:
            return
        # Lock for both _ip_set and _timer
        with self._poll_lock:
            try:
                log.debug3("Polling DNS for updates to service: %s", self.target)

                new_ip_set = self._get_ip_set()

                # Create a new client only if new IP/port pairs are found
                if new_ip_set - self._ip_set:
                    self._reconnect()

                self._ip_set = new_ip_set
            except (socket.gaierror, socket.herror):
                log.warning("Failed to poll DNS for updates", exc_info=True)

            except Exception as ex:  # pylint: disable=broad-exception-caught
                log.warning(
                    "<TGB58023131W>",
                    "Unhandled exception caught during polling DNS for updates: %s",
                    ex,
                    exc_info=True,
                )

            # Cancel any duplicate timers
            if self._timer is not None and self._timer.is_alive():
                self._timer.cancel()

            # Schedule next poll
            log.debug3("Scheduling next DNS poll in %s seconds", self.poll_interval)
            self._timer = threading.Timer(self.poll_interval, self._dns_poll)
            self._timer.daemon = True
            self._timer.start()

    def _reconnect(self):
        """Force-reconnect the client by re-invoking the initializer with a new channel"""
        log.debug3("Reconnecting channel for service: %s", self.target)
        # 🌶️🌶️🌶️ We don't want to rebuild a new client, since that would require that all users
        # update any client references that they're holding.
        # This __init__ call re-initializes the client instance that many things may be holding.
        # This should be safe since the grpc client classes are "dumb" wrappers around channels.
        # pylint: disable=unnecessary-dunder-call
        self.client_class.__init__(self=self._client, channel=self.channel_partial())

    def _get_ip_set(self) -> Set[Tuple[str, int]]:
        """Uses `socket` to attempt a DNS lookup.
        Returns a set of (ip address, port) tuples that self.target resolves to
        """
        host, port = self.target.split(":")
        hosts = socket.getaddrinfo(host, port)
        # socket.getaddrinfo returns a tuple containing information
        # about socket, where 4th index contains sockaddr containing
        # ip address and port
        ip_set = {host[4] for host in hosts}
        log.debug3("IPs for target: %s, %s", self.target, ip_set)
        return ip_set
