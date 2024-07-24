import io
import logging
import os
from http.server import HTTPServer
from unittest.mock import ANY, Mock, PropertyMock, patch, MagicMock

import pytest

from dpypi.serve import HandlerConfig, HTTPHandler, make_connections, serve
from dpypi.wheel import Wheel


class StrMock(Mock):
    def __str__(self):
        return self.name


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
def mock_connection():
    """Create a more complete mock connection."""
    connection = Mock()
    connection.name = "test_repo"
    connection.get_repo = Mock(return_value=Mock(name="test_repo"))
    connection.list_release_assets = Mock(
        return_value=[
            Mock(name="package-1.0.0-py3-none-any.whl"),
            Mock(name="package-2.0.0-py3-none-any.whl"),
        ]
    )
    connection.get_release_asset = Mock()
    return connection


@pytest.fixture
def handler(mock_config, mock_connection):
    """Create a mock HTTPHandler instance with correct connection setup."""
    handler = create_mock_handler(
        mock_config, {}, "/simple/test_repo/package-1.0.0-py3-none-any.whl"
    )

    # Use MagicMock for repo_2_connection to allow for key access
    handler.repo_2_connection = MagicMock()
    handler.repo_2_connection.get.return_value = mock_connection

    # Ensure _split_path returns the correct distribution name
    handler._split_path = Mock(return_value=("test_repo", ".whl"))

    return handler


def test_artifact_download(handler, mock_config, mock_connection, caplog):
    """Test if artifacts are 'downloaded' (mocked) to the correct location."""
    caplog.set_level(logging.DEBUG)
    distribution_name = "test_repo"
    os.makedirs(mock_config.artifact_dir, exist_ok=True)

    mock_wheel = Mock(
        distribution_name=distribution_name,
        version="1.0.0",
        full_name="package-1.0.0-py3-none-any.whl",
    )

    with patch("dpypi.serve.Wheel.from_path", return_value=mock_wheel) as mock_wheel_from_path:
        mock_asset = Mock()
        mock_asset.name = "package-1.0.0-py3-none-any.whl"
        mock_asset.local_path = os.path.join(
            mock_config.artifact_dir, distribution_name, "package-1.0.0-py3-none-any.whl"
        )
        mock_connection.get_release_asset.return_value = mock_asset

        with patch("os.path.abspath", return_value=mock_config.base_path) as mock_abspath:
            handler.do_GET()

        # Print debug information
        print(f"Handler path: {handler.path}")
        print(f"Handler repo_2_connection: {handler.repo_2_connection}")
        print(f"Mock wheel_from_path called: {mock_wheel_from_path.called}")
        print(f"Mock wheel_from_path call count: {mock_wheel_from_path.call_count}")
        print(f"Mock wheel_from_path call args: {mock_wheel_from_path.call_args_list}")
        print(f"Mock get_release_asset called: {mock_connection.get_release_asset.called}")
        print(f"Mock get_release_asset call count: {mock_connection.get_release_asset.call_count}")
        print(
            f"Mock get_release_asset call args: {mock_connection.get_release_asset.call_args_list}"
        )
        print(f"Mock abspath called: {mock_abspath.called}")
        print(f"Mock abspath call count: {mock_abspath.call_count}")
        print(f"Mock abspath call args: {mock_abspath.call_args_list}")

        # Print the captured logs
        print("Captured logs:")
        for record in caplog.records:
            print(f"{record.levelname}: {record.message}")

        # Check if Wheel.from_path was called
        assert mock_wheel_from_path.called, "Wheel.from_path was not called"

        # Check if get_release_asset was called
        assert mock_connection.get_release_asset.called, "get_release_asset was not called"

    # Check if the artifact directory and file exist
    assert os.path.exists(
        mock_config.artifact_dir
    ), f"Artifact directory does not exist: {mock_config.artifact_dir}"
    assert os.path.exists(
        os.path.join(mock_config.artifact_dir, distribution_name)
    ), f"Distribution artifact directory does not exist: {os.path.join(mock_config.artifact_dir, distribution_name)}"
    assert os.path.exists(
        mock_asset.local_path
    ), f"Artifact file does not exist: {mock_asset.local_path}"


if __name__ == "__main__":
    pytest.main([__file__])
