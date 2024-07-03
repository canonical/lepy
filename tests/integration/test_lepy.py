import os
import subprocess
import time
from typing import Optional

import pytest
import requests
from lepy import run_lego_command

# Set up Go
# Add ~/go/bin to your $PATH, or set GOBIN to a directory that is in your $PATH already,
# One way to do this is to add export PATH=$PATH:$HOME/go/bin to your ~/.profile
# cd pebble
# go install ./cmd/pebble

# temporarily trust /test/certs/pebble.minica.pem
# Root CA certificate is also available at: https://0.0.0.0:15000/roots/0
# export SSL_CERT_FILE=/home/kayra/Documents/work/canonical/lepy/tests/integration/pebble/test/certs/pebble.minica.pem
# run pebble -config ./test/config/pebble-config.json -strict false


@pytest.fixture(scope="session")
def configure_acme_server():
    """Get and install pebble, a lightweight ACME server from letsencrypt."""
    tests_dir = os.path.dirname(__file__)

    # Install and run pebble
    subprocess.check_call(["go", "install", "./cmd/pebble"], cwd=os.path.join(tests_dir, "pebble"))
    pebble = subprocess.Popen(
        ["pebble", "-config", "test/config/pebble-config.json"],
        cwd=os.path.join(tests_dir, "pebble"),
    )

    # Get the CA cert to trust TODO: this doesn't work
    ca_path = os.path.join(tests_dir, "pebble/test/certs/pebble.minica.pem")
    filename = os.path.join(tests_dir, "test_files/test.csr")
    localhost_csr = open(filename).read().encode()

    poll_server("https://0.0.0.0:14000/dir")

    yield {"csr": localhost_csr, "ca_path": ca_path}

    pebble.terminate()


class TestLepy:
    def test_given_request_certificate_when_request_sent_then_certificate_issued(
        self,
        configure_acme_server,
    ):
        response = run_lego_command(
            "something@nowhere.com",
            "https://localhost:14000/dir",
            configure_acme_server.get("csr"),
            "http",
            {"SSL_CERT_FILE": configure_acme_server.get("ca_path")},
        )
        assert response.metadata.get("domain") == "localhost"


def poll_server(url: str, freq: int = 1):
    while True:
        try:
            time.sleep(1)
            response = requests.get(url, verify=False)
            return response
        except requests.RequestException as e:
            print(e)
            pass