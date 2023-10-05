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
"""Test the load-balancing client wrapper"""
# Standard
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from socket import AddressFamily, SocketKind
from typing import List
from unittest import mock
import contextlib
import datetime
import random
import socket
import threading
import time

# Third Party
import grpc
import pytest
import tls_test_tools

# Local
from caikit_tgis_backend.load_balancing_proxy import GRPCLoadBalancerProxy
from caikit_tgis_backend.protobufs import generation_pb2, generation_pb2_grpc

# 🌶️🌶️🌶️ These tests don't actually flex the real grpc load balancing between remotes.
# It may be possible to run a local DNS server during testing, but it seems very difficult
# to spin up multiple servers on localhost and somehow return DNS records that mimic what
# kubedns does while still routing all traffic back to the local mocks.


class TGISTestServer(generation_pb2_grpc.GenerationServiceServicer):
    def Tokenize(self, request, context):
        return generation_pb2.BatchedTokenizeResponse(
            responses=[
                generation_pb2.TokenizeResponse(
                    token_count=5, tokens=["hello ", "world ", "I ", "am ", "Zod."]
                )
            ]
        )


@contextlib.contextmanager
def mock_tgis_server() -> int:
    port = tls_test_tools.open_port()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    generation_pb2_grpc.add_GenerationServiceServicer_to_server(
        TGISTestServer(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    yield port
    server.stop(grace=0)


@contextlib.contextmanager
def mock_ip_set(ports: List[int]):
    with mock.patch("socket.getaddrinfo") as socket_mock:
        response_list = []
        for port in ports:
            response_list.extend(
                [
                    (
                        AddressFamily.AF_INET,
                        SocketKind.SOCK_STREAM,
                        6,
                        "",
                        ("127.0.0.1", port),
                    ),
                    (
                        AddressFamily.AF_INET,
                        SocketKind.SOCK_DGRAM,
                        17,
                        "",
                        ("127.0.0.1", port),
                    ),
                    (
                        AddressFamily.AF_INET,
                        SocketKind.SOCK_RAW,
                        0,
                        "",
                        ("127.0.0.1", port),
                    ),
                ]
            )
        socket_mock.return_value = response_list
        yield


def test_client_works():
    """Basic test- does it turn on"""
    with mock_tgis_server() as port:
        client = GRPCLoadBalancerProxy(
            client_class=generation_pb2_grpc.GenerationServiceStub,
            target=f"localhost:{port}",
        )

        response = client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())
        assert response.responses[0].token_count == 5
        client.shutdown_dns_poll()


def test_dns_poll_shutdown():
    """Make sure the polling isn't totally runaway"""
    # NB: I hate sleeps in tests!
    # But, I don't know of a different way to properly deal with timers :(

    # little sleep first to let other threads die...
    time.sleep(0.01)
    initial_thread_count = threading.active_count()

    client = GRPCLoadBalancerProxy(
        client_class=generation_pb2_grpc.GenerationServiceStub,
        target=f"localhost:80",
        # NOTE: poll interval needs to be a bit in tune with the range and sleep below
        # otherwise the test would fail since we would spin up more
        # threads
        poll_interval_s=0.01,
    )

    # We should have at least another thread for the dns poll
    assert threading.active_count() > initial_thread_count

    # Ping the poll method a bunch ourselves
    for i in range(100):
        client._dns_poll()

    time.sleep(0.1)
    # We should not have a ton more threads
    assert threading.active_count() < initial_thread_count + 10

    # Shut it down and ensure we no longer have poll threads
    client.shutdown_dns_poll()
    time.sleep(0.1)
    assert threading.active_count() <= initial_thread_count


def test_target_validation():
    """Targets must be in host:port format"""
    with pytest.raises(ValueError, match="Target must be provided in .* format"):
        GRPCLoadBalancerProxy(
            client_class=generation_pb2_grpc.GenerationServiceStub, target="localhost"
        )

    with pytest.raises(ValueError, match="Target must be provided in .* format"):
        GRPCLoadBalancerProxy(
            client_class=generation_pb2_grpc.GenerationServiceStub, target="9001"
        )

    with pytest.raises(ValueError, match="Target must be provided in .* format"):
        # NB: dns targets not supported
        GRPCLoadBalancerProxy(
            client_class=generation_pb2_grpc.GenerationServiceStub,
            target="dns://foo.bar/localhost:9001",
        )


def test_client_rebuilds_on_ip_change():
    """If a new pod in the target service appears, the grpc load balancer won't have any trigger
    to re-query DNS. Forcing a new client with a new channel will pick up the new pod."""

    poll_interval = 0.0001  # 0.1 ms
    with mock_tgis_server() as port:
        with mock_ip_set([8080]):
            client = GRPCLoadBalancerProxy(
                client_class=generation_pb2_grpc.GenerationServiceStub,
                target=f"localhost:{port}",
                poll_interval_s=poll_interval,
            )
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())
            first_tokenize_method = client.Tokenize

        with mock_ip_set([8080, 9090]):
            then = datetime.datetime.now()
            # On re-connect, each method on the client is replaced with a new method pointer
            while client.Tokenize is first_tokenize_method:
                assert datetime.datetime.now() - then < datetime.timedelta(
                    milliseconds=100
                ), "Client did not update"

            # client still works
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())

            client.shutdown_dns_poll()


def test_client_does_not_rebuild_when_ips_do_not_change():
    """Make sure we're not churning a ton of clients"""
    with mock_tgis_server() as port:
        with mock_ip_set([8080, 9090]):
            client = GRPCLoadBalancerProxy(
                client_class=generation_pb2_grpc.GenerationServiceStub,
                target=f"localhost:{port}",
            )
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())
            tokenize_ptr = client.Tokenize

            # Force poll which would update the client
            client._dns_poll()
            assert client.Tokenize is tokenize_ptr

            client.shutdown_dns_poll()


def test_client_does_not_rebuild_when_ips_drop_out():
    """If a pod in the target service terminates, we don't need to bother rebuilding a client.
    The grpc load balancing policy should close the sub-channel and re-query DNS anyway."""
    with mock_tgis_server() as port:
        with mock_ip_set([8080, 9090]):
            client = GRPCLoadBalancerProxy(
                client_class=generation_pb2_grpc.GenerationServiceStub,
                target=f"localhost:{port}",
            )
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())
            tokenize_ptr = client.Tokenize

        with mock_ip_set([8080]):
            # Force poll which would update the client
            client._dns_poll()
            assert client.Tokenize is tokenize_ptr
            client.shutdown_dns_poll()


def test_client_handles_socket_errors():
    """Polling will still continue happily even if socket errors occur"""
    poll_interval = 0.0001  # 0.1 ms
    with mock_tgis_server() as port:
        with mock_ip_set([8080, 9090]):
            client = GRPCLoadBalancerProxy(
                client_class=generation_pb2_grpc.GenerationServiceStub,
                target=f"localhost:{port}",
                poll_interval_s=poll_interval,
            )
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())
            original_tokenize = client.Tokenize

            failing_mock = mock.Mock()
            failing_mock.side_effect = socket.gaierror
            with mock.patch("socket.getaddrinfo", new=failing_mock):
                # Ensure new socket mock is called, and that everything is fine
                then = datetime.datetime.now()
                while failing_mock.call_count == 0:
                    assert datetime.datetime.now() - then < datetime.timedelta(
                        milliseconds=100
                    ), "Client did not poll"
                # Client still okay
                client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())

            # no more socket errors, now force poll and ensure nothing changed
            client._dns_poll()
            assert client.Tokenize == original_tokenize
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())
            client.shutdown_dns_poll()


def test_client_reconnect_under_load():
    """Test that the channel can be re-constructed while clients are running in other threads.
    NB: The target cna only resolve to a single server, so this does not re-route the client
    on the fly as the channel changes"""
    pool = ThreadPoolExecutor(max_workers=20)

    with mock_tgis_server() as port:
        client = GRPCLoadBalancerProxy(
            client_class=generation_pb2_grpc.GenerationServiceStub,
            target=f"localhost:{port}",
        )

        def do_work():
            return client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())

        num_calls = 1000
        futures = []
        for i in range(num_calls):
            future = pool.submit(do_work)
            futures.append(future)

        stride = 50
        for i in range(int(num_calls / stride)):
            with mock_ip_set([8000 + i]):
                # force re-poll to reconnect the client running in the pool
                client._dns_poll()
                # Let some of the work happen
                [f.result() for f in futures[i * stride : (i + 1) * stride]]
        client.shutdown_dns_poll()


@pytest.mark.skip("sanity check only")
def test_channel_reconfig():
    """Sanity check that clients can be reinitialized on the fly.
    NB: This does not test any code from this package. This is here to illustrate that a client
    can be given a new channel at runtime, while calls are being made."""
    pool = ThreadPoolExecutor(max_workers=20)

    with mock_tgis_server() as port1:
        with mock_tgis_server() as port2:
            with mock_tgis_server() as port3:

                chan1 = grpc.insecure_channel(f"localhost:{port1}")
                chan2 = grpc.insecure_channel(f"localhost:{port2}")
                chan3 = grpc.insecure_channel(f"localhost:{port3}")

                the_client = generation_pb2_grpc.GenerationServiceStub(chan1)
                chans = [chan1, chan2, chan3]

                def do_work(client, i):
                    # Randomly swap out the channel that the one client uses
                    if i % 100 == 0:
                        generation_pb2_grpc.GenerationServiceStub.__init__(
                            self=client, channel=random.choice(chans)
                        )
                    return client.Tokenize(
                        request=generation_pb2.BatchedTokenizeRequest()
                    )

                num_calls = 1000
                futures = []
                for i in range(num_calls):
                    future = pool.submit(do_work, the_client, i)
                    futures.append(future)

                # Will raise if any do_work raised
                [f.result() for f in futures]
