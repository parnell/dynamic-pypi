import json
import logging
import os
import sys
import threading
from functools import partial
from http.server import HTTPServer as BaseHTTPServer
from http.server import SimpleHTTPRequestHandler
from logging import getLogger
from typing import Any

from github import Repository as GithubRepository
from pi_conf import Config

from dpypi import cfg
from dpypi.connections.connection import Connection, Repository
from dpypi.connections.github_connection import GithubConnection
from dpypi.connections.local_connection import LocalConnection
from dpypi.web_utils import write_index_html
from dpypi.wheel import Wheel

print(cfg)
log = getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))  ## add stdout handler
log.setLevel(logging.DEBUG)


class HandlerConfig(Config):
    artifact_dir: str
    html_dir: str
    base_path: str = ""
    cache: bool = False
    ## build only works for local connections
    build: bool = False
    ## Warn if the indexes found in the config are empty
    warn_empty_index: bool = True


def make_connections(cfg: dict[str, Any]) -> dict[str, Any]:
    repos: dict[str, Any] = {}
    if not cfg.get("index") or len(cfg["index"]) == 0:
        return repos
    for c in cfg["index"]:
        cls = GithubConnection if c["uri"].startswith("https://") else LocalConnection
        for r in c.get("repos", []):
            log.debug(f"make_connections: {r} = {c}")
            repos[r] = cls(name=r, config=c)

    return repos


class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""

    def __init__(
        self,
        index_config: Config,
        config: HandlerConfig,
        repo_2_connection: dict[str, Connection],
        *args,
        **kwargs,
    ):
        self.config: HandlerConfig = config
        self.repo_2_connection: dict[str, Connection] = repo_2_connection
        if not repo_2_connection:
            if self.config.warn_empty_index:
                raise ValueError("No repositories found in config")
        super().__init__(*args, **kwargs)

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        ext = os.path.splitext(path)[1]
        if ext:
            distribution = path.split("/")[-2]
        else:
            distribution = path.removesuffix("/").split("/")[-1]
        return distribution, ext

    def _make_distribution_html(
        self,
        repo: Repository,
        connection: Connection,
    ) -> str:
        distribution = repo.name
        log.debug(f"_make_distribution_html: distribution: {distribution}, {self.path}")
        html_path = os.path.join(self.config.html_dir, distribution, "index.html")
        if self.config.cache and os.path.exists(html_path):
            log.debug(f"html_path cache exists at {html_path}")
            return html_path

        assets = connection.list_release_assets(repo)
        assets = [a for a in assets if a.name.endswith(".whl")]
        write_index_html(
            project=distribution,
            release_assets=assets,
            html_path=html_path,
            artifact_dir=self.config.artifact_dir,
        )
        log.debug(f"wrote {html_path}")
        return f"/{html_path}"

    def _shutdown(self):
        self.send_response(200)
        self.end_headers()
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _list_repos(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        repo_dict = {k: str(v) for k, v in self.repo_2_connection.items()}

        response = json.dumps(repo_dict, indent=2)
        self.wfile.write(response.encode("utf-8"))

    def _list_releases(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        repo_dict = {}
        for k, v in self.repo_2_connection.items():
            repo = v.get_repo(k)
            releases = v.list_release_assets(repo)
            repo_dict = {k: [str(r) for r in releases]}

        response = json.dumps(repo_dict, indent=2)
        self.wfile.write(response.encode("utf-8"))

    def do_GET(self):
        """
        Serve a GET request.
        /shutdown : will shutdown the server
        /simple/<distribution>/ : will serve the distribution's html page
        /simple/<distribution>/<artifact> : will serve the artifact
        """

        if self.path == "/shutdown":
            return self._shutdown()
        if self.path.startswith("/list"):
            return self._list_repos()
        if self.path.startswith("/list_releases"):
            return self._list_repos()

        distribution, ext = self._split_path(self.path)
        connection = self.repo_2_connection.get(distribution)

        log.debug(
            f"do_GET: distribution: {distribution} found={connection is not None} path={self.path}"
        )
        if not connection:
            super().do_GET()
            return
        print(f"ext: {ext} build: {self.config.build}")
        repo = connection.get_repo(f"{connection.name}/{distribution}")
        if not ext:
            self.path = self._make_distribution_html(repo, connection)
        elif ext == ".whl":
            w = Wheel.from_path(self.path)

            asset = connection.get_release_asset(
                repo=repo,
                release=w.version,
                asset_name=w.full_name,
                dest_folder=os.path.join(self.config.artifact_dir, w.distribution_name),
            )
            abs_base_path = os.path.abspath(self.config.base_path)
            if asset and asset.local_path:
                self.path = asset.local_path
            print(f"abs_base_path: {abs_base_path}")
            print(f"self.path: {self.path}")
            self.path = self.path.removeprefix(abs_base_path)
            print(f"self.path: {self.path}")

        log.debug(f"~do_GET(): {self.path}")
        super().do_GET()


def serve(cfg: Config):
    """
    Start the HTTP server
    Args:
        cfg: dict
            port: int (default 8083) : port to listen on
            base_path: str (default "") : base path for the server
            artifact_dir: str (default "web/artifacts") : directory to store artifacts
            html_dir: str (default "web/html") : directory to store html files
            cache: bool (default False) : Should use cached html files
            [[index]] : list of repositories to index
                name: str : name of the repository
                uri: str : uri of the repository
                access_token: str : token for the repository
                repos : list[str] : list of repositories to index
    """
    port = cfg.get("port", 8083)
    base_path = cfg.get("base_path", "")
    conf = HandlerConfig(
        artifact_dir=cfg.get("artifact_dir", "web/artifacts"),
        html_dir=cfg.get("html_dir", "web/html"),
        cache=cfg.get("cache", False),
        build=cfg.get("build", False),
        base_path=base_path,
    )
    repo_2_connection = make_connections(cfg)
    http_handler = partial(HTTPHandler, cfg, conf, repo_2_connection)
    httpd = BaseHTTPServer((base_path, port), http_handler)
    log.debug(f"HTTPServer: address{httpd.server_address}")
    httpd.serve_forever()


if __name__ == "__main__":
    config = {
        "port": 8083,
        "base_path": "",
        "artifact_dir": "web/artifacts",
        "html_dir": "web/html",
        "cache": False,
    }
    config.update(cfg)
    print("updated cfg: ", config)
    serve(Config.from_dict(config))
