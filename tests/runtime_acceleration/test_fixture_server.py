from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from experiments.runtime_acceleration.fixture_server import fixture_server


def test_fixture_server_static_redirect_and_error_routes():
    with fixture_server() as base_url:
        static = urlopen(base_url + "/static", timeout=2)
        body = static.read().decode()
        assert static.status == 200
        assert "deterministic-marker" in body
        redirected = urlopen(base_url + "/redirect", timeout=2)
        assert redirected.geturl().endswith("/static")
        with pytest.raises(HTTPError) as exc:
            urlopen(base_url + "/error", timeout=2)
        assert exc.value.code == 500
