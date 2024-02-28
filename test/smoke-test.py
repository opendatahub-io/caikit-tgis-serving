import os

import asyncio
import time

import caikit_nlp_client


def wait_until(
    pred,
    timeout: float = 15,
    pause: float = 1,
):
    start = time.perf_counter()
    exc = None
    while (time.perf_counter() - start) < timeout:
        try:
            value = pred()
        except Exception as e:
            exc = e
        else:
            return value
        time.sleep(pause)

    raise TimeoutError("timed out waiting") from exc


async def test_grpc(
    host: str = "localhost",
    port: int = 8085,
    model: str = "flan-t5-small-caikit",
):
    res = wait_until(
        lambda: caikit_nlp_client.GrpcClient(host, port, insecure=True).generate_text(
            "flan-t5-small-caikit", "At what temperature does liquid Nitrogen boil?"
        )
    )
    assert res, "Nothing was returned from the server"
    print(f"grpc connection success: {res=}")


async def test_http(
    url: str = "http://localhost:8080",
    model: str = "flan-t5-small-caikit",
):
    client = caikit_nlp_client.HttpClient(url)
    res = wait_until(
        lambda: client.generate_text(
            model,
            "At what temperature does liquid Nitrogen boil?",
        )
    )
    assert res, "Nothing was returned from the server"
    print(f"http connection success: {res=}")


async def main():
    inference_service_url = os.getenv("ISVC_URL")

    if not inference_service_url:
        print("No inference service, assuming docker-compose test")
        return await asyncio.gather(
            test_grpc(),
            test_http(),
        )

    print(f"Testing {inference_service_url=}")
    await test_http(url=inference_service_url)
    # TODO: handle grpc


if __name__ == "__main__":
    asyncio.run(main())
