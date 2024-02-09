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


async def test_grpc():
    res = wait_until(
        lambda: caikit_nlp_client.GrpcClient(
            "localhost", 8085, insecure=True
        ).generate_text(
            "flan-t5-small-caikit", "At what temperature does liquid Nitrogen boil?"
        )
    )
    assert res, "Nothing was returned from the server"
    print(f"grpc connection success: {res=}")


async def test_http():
    client = caikit_nlp_client.HttpClient("http://localhost:8080")
    res = wait_until(
        lambda: client.generate_text(
            "flan-t5-small-caikit", "At what temperature does liquid Nitrogen boil?"
        )
    )
    assert res, "Nothing was returned from the server"
    print(f"http connection success: {res=}")


async def main():
    await asyncio.gather(test_grpc(), test_http())


if __name__ == "__main__":
    asyncio.run(main())
