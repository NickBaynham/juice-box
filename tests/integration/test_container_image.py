import subprocess
import time

import httpx
import pytest

IMAGE = "juice-box:test"
CONTAINER = "juice-box-test-container"


@pytest.mark.integration
def test_container_serves_health():
    subprocess.run(["docker", "build", "-t", IMAGE, "."], check=True)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            CONTAINER,
            "-p",
            "8001:8000",
            IMAGE,
        ],
        check=True,
    )

    try:
        deadline = time.monotonic() + 30
        response = None
        while time.monotonic() < deadline:
            try:
                response = httpx.get("http://localhost:8001/health", timeout=1)
                if response.status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(1)

        assert response is not None
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0"}
    finally:
        subprocess.run(["docker", "rm", "-f", CONTAINER], check=False)
