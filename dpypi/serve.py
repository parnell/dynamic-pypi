import os
import threading
from functools import partial
from http.server import HTTPServer as BaseHTTPServer
from http.server import SimpleHTTPRequestHandler
from logging import getLogger

from github import Repository
from pi_conf import Config
from platformdirs import site_cache_dir

from dpypi import ROOT_DIR, cfg
from dpypi.github_connection import GithubConnection, GithubConnections
from dpypi.web_utils import write_index_html
from dpypi.wheel import Wheel

log = getLogger(__name__)
## add stdout handler
import logging
import sys

log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.DEBUG)


class HandlerConfig(Config):
    web_dir: str
    artifact_dir: str
    html_dir: str
    template_dir: str


connections = GithubConnections(cfg)


class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""

    def __init__(self, config: HandlerConfig, *args, **kwargs):
        self.config: HandlerConfig = config
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
        repo: Repository.Repository,
        connection: GithubConnection,
    ) -> str:
        distribution = repo.name

        log.debug(f"_make_distribution_html: distribution: {distribution}, {self.path}")
        html_path = os.path.join(self.config.html_dir, distribution, "index.html")
        if os.path.exists(html_path):
            log.debug(f"html_path cache exists at {html_path}")
            return html_path

        assets = connection.list_release_assets(repo)
        assets = [a for a in assets if a.name.endswith(".whl")]
        write_index_html(
            project=distribution,
            release_assets=assets,
            html_path=html_path,
            artifact_dir=self.config.artifact_dir,
            template_dir=self.config.template_dir,
        )
        log.debug(f"wrote {html_path}")
        return f"/{html_path}"

    def do_GET(self):
        """
        Serve a GET request.
        /shutdown : will shutdown the server
        /simple/<distribution>/ : will serve the distribution's html page
        /simple/<distribution>/<artifact> : will serve the artifact
        """
        if self.path == "/shutdown":
            self.send_response(200)
            self.end_headers()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        distribution, ext = self._split_path(self.path)
        connection = connections.repo_2_connection.get(distribution)
        log.debug(
            f"do_GET: distribution: {distribution} found={connection is not None} path={self.path}"
        )
        if not connection:
            super().do_GET()
            return
        repo = connection.g.get_repo(f"{connection.name}/{distribution}")
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
            self.path = asset.local_path
        log.debug(f"~do_GET(): {self.path}")
        super().do_GET()


def main():
    port = cfg.get("port", 8083)
    base_path = cfg.get("base_path", "")
    conf = HandlerConfig(
        artifact_dir=cfg.get("artifact_dir", "web/artifacts"),
        html_dir=cfg.get("html_dir", "web/html"),
        template_dir=cfg.get("template_dir", f"{ROOT_DIR}/templates"),
    )
    http_handler = partial(HTTPHandler, conf)
    httpd = BaseHTTPServer((base_path, port), http_handler)
    log.debug(f"HTTPServer: address{httpd.server_address}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
