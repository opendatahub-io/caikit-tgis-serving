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
import datetime
# Standard
from concurrent import futures
from socket import AddressFamily, SocketKind
from typing import List
from unittest import mock
import contextlib

# Third Party
import grpc
import pytest

# Local
from caikit_tgis_backend.load_balancing_client import GRPCLoadBalancer
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
def mock_tgis_server(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    generation_pb2_grpc.add_GenerationServiceServicer_to_server(
        TGISTestServer(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    yield
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
    with mock_tgis_server(9000):
        wrapper = GRPCLoadBalancer(client_class=generation_pb2_grpc.GenerationServiceStub, target="localhost:9000")
        client = wrapper.get_client()

        response = client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())
        assert response.responses[0].token_count == 5


def test_target_validation():
    """Targets must be in host:port format"""
    with pytest.raises(ValueError, match="Target must be provided in .* format"):
        GRPCLoadBalancer(client_class=generation_pb2_grpc.GenerationServiceStub, target="localhost")

    with pytest.raises(ValueError, match="Target must be provided in .* format"):
        GRPCLoadBalancer(client_class=generation_pb2_grpc.GenerationServiceStub, target="9001")

    with pytest.raises(ValueError, match="Target must be provided in .* format"):
        # NB: dns targets not supported
        GRPCLoadBalancer(client_class=generation_pb2_grpc.GenerationServiceStub, target="dns://foo.bar/localhost:9001")


def test_client_rebuilds_on_ip_change():
    """If a new pod in the target service appears, the grpc load balancer won't have any trigger
    to re-query DNS. Forcing a new client with a new channel will pick up the new pod."""

    poll_interval = 0.0001  # 0.1 ms
    with mock_tgis_server(9000):
        with mock_ip_set([8080]):
            wrapper = GRPCLoadBalancer(client_class=generation_pb2_grpc.GenerationServiceStub,
                                       target="localhost:9000",
                                       poll_interval_s=poll_interval)
            client = wrapper.get_client()
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())

        with mock_ip_set([8080, 9090]):
            then = datetime.datetime.now()
            while client is wrapper.get_client():
                assert datetime.datetime.now() - then < datetime.timedelta(milliseconds=100), "Client did not update"

            # new client still works
            new_client = wrapper.get_client()
            new_client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())


def test_client_does_not_rebuild_when_ips_do_not_change():
    """Make sure we're not churning a ton of clients"""
    with mock_tgis_server(9000):
        with mock_ip_set([8080, 9090]):
            wrapper = GRPCLoadBalancer(client_class=generation_pb2_grpc.GenerationServiceStub,
                                       target="localhost:9000")
            client = wrapper.get_client()
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())

            # Force poll which would update the client
            wrapper._poll_for_ips()
            assert client is wrapper.get_client()


def test_client_does_not_rebuild_when_ips_drop_out():
    """If a pod in the target service terminates, we don't need to bother rebuilding a client.
    The grpc load balancing policy should close the sub-channel and re-query DNS anyway."""
    poll_interval = 0.0001  # 0.1 ms
    with mock_tgis_server(9000):
        with mock_ip_set([8080, 9090]):
            wrapper = GRPCLoadBalancer(client_class=generation_pb2_grpc.GenerationServiceStub,
                                       target="localhost:9000",
                                       poll_interval_s=poll_interval)
            client = wrapper.get_client()
            client.Tokenize(request=generation_pb2.BatchedTokenizeRequest())

        with mock_ip_set([8080]):
            # Force poll which would update the client
            wrapper._poll_for_ips()
            assert client is wrapper.get_client()
