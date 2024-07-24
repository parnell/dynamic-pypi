import io
import os
from http.server import HTTPServer
from unittest.mock import ANY, Mock, patch

import pytest

from dpypi.serve import HandlerConfig, HTTPHandler, make_connections, serve


class MockRequest:
    def __init__(self, path="/"):
        self.rfile = io.BytesIO(f"GET {path} HTTP/1.1\r\n\r\n".encode("ascii"))
        self.wfile = io.BytesIO()
        self.request_version = "HTTP/1.1"
        self.requestline = f"GET {path} HTTP/1.1"
        self.command = "GET"
        self.path = path

    def makefile(self, *args, **kwargs):
        return self.rfile

    def sendall(self, *args, **kwargs):
        pass


def create_mock_handler(config, connections, path="/"):
    class MockServer(HTTPServer):
        def __init__(self):
            self.base_path = ""

    request = MockRequest(path)
    client_address = ("127.0.0.1", 8000)
    server = MockServer()

    handler = HTTPHandler(
        Mock(), config, connections, request, client_address, server  # index_config
    )

    handler.rfile = request.rfile
    handler.wfile = request.wfile
    handler.request_version = request.request_version
    handler.requestline = request.requestline
    handler.command = request.command
    handler.path = request.path

    return handler


@pytest.fixture
def mock_config():
    return HandlerConfig(
        artifact_dir="test_artifacts", html_dir="test_html", warn_empty_index=False
    )


@pytest.fixture
def mock_connections():
    return {"test_repo": Mock()}


@pytest.fixture
def handler(mock_config, mock_connections):
    return create_mock_handler(mock_config, mock_connections)


def test_make_connections(mocker):
    test_config = {
        "index": [
            {"uri": "https://github.com/test/repo", "repos": ["repo1", "repo2"]},
            {"uri": "/local/path", "repos": ["repo3"]},
        ]
    }

    mock_github = mocker.patch("dpypi.serve.GithubConnection")
    mock_local = mocker.patch("dpypi.serve.LocalConnection")

    connections = make_connections(test_config)

    assert len(connections) == 3
    assert isinstance(connections["repo1"], mock_github.return_value.__class__)
    assert isinstance(connections["repo2"], mock_github.return_value.__class__)
    assert isinstance(connections["repo3"], mock_local.return_value.__class__)


def test_http_handler(handler: HTTPHandler, mock_connections):
    print("handler.repo_2_connection:", handler.repo_2_connection)
    print("mock_connections:", mock_connections)
    assert handler.config.artifact_dir == "test_artifacts"
    assert handler.config.html_dir == "test_html"
    assert list(handler.repo_2_connection.keys()) == list(mock_connections.keys())
    assert all(isinstance(conn, Mock) for conn in handler.repo_2_connection.values())


def test_serve():
    mock_config = {
        "port": 8083,
        "base_path": "",
        "artifact_dir": "test_artifacts",
        "html_dir": "test_html",
        "cache": False,
    }

    with patch("dpypi.serve.BaseHTTPServer") as mock_server, patch(
        "dpypi.serve.make_connections", return_value={"test_repo": Mock()}
    ):

        serve(mock_config) #type: ignore

        mock_server.assert_called_once_with(("", 8083), ANY)
        mock_server.return_value.serve_forever.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
