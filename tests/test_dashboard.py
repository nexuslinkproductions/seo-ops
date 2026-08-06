"""Acceptance F: loopback dashboard, seven views, client context required."""

from __future__ import annotations

import threading
import urllib.request
import urllib.error

import pytest

from ops.serve import make_server
from ops.clients import list_clients


@pytest.fixture
def server(data_root, populated_store, client_a):
    httpd = make_server(data_root, port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    thread.join(timeout=5)


def _get(server, path: str) -> tuple[int, str]:
    port = server.server_address[1]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _post(server, path: str, form: dict) -> tuple[int, str]:
    import urllib.parse

    port = server.server_address[1]
    payload = urllib.parse.urlencode(form).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=payload, method="POST"
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")

def test_binds_loopback_only(server):
    host, _port = server.server_address
    assert host == "127.0.0.1"


def test_all_seven_views_serve(server, client_a):
    for view in ("overview", "trends", "evidence", "audits", "changes", "scorecards", "backlog"):
        status, body = _get(server, f"/clients/{client_a.id}/{view}")
        assert status == 200, view
        assert len(body) > 200, view


def test_no_global_data_view(server):
    status, _ = _get(server, "/overview")
    assert status == 404
    status, _ = _get(server, "/clients/does-not-exist/overview")
    assert status == 404


def test_index_lists_clients(server, client_a, client_b):
    status, body = _get(server, "/")
    assert status == 200
    assert client_a.name in body
    assert client_b.name in body


def test_create_client_via_form(data_root, server):
    status, _ = _post(server, "/clients/add", {"name": "Gamma Store"})
    assert status == 303
    assert any(c.name == "Gamma Store" for c in list_clients(data_root))
