import os
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from logging import getLogger

import requests
from github import Auth, Github
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.Repository import Repository
from pi_conf import Config

log = getLogger(__name__)


@dataclass
class IndexConfig(Config):
    name: str
    uri: str
    repos: list[str] = None
    access_token: str = None


@dataclass
class ReleaseAsset(GitReleaseAsset):
    ## Hack to add a local_path attribute to GitReleaseAsset for type hinting
    local_path: str = None


@dataclass
class GithubConnections:
    config: Config
    connections: dict[str, "GithubConnection"] = field(default_factory=dict)
    _repo_2_connection: dict = None

    def __post_init__(self):
        index_cfg: IndexConfig
        redact = set(["access_token"])
        for index_cfg in self.config.index:
            for k in index_cfg:
                cfg = index_cfg.copy()
                if k in redact:
                    cfg[k] = "*****"
                log.debug(f"{k}={cfg[k]}")
            gc = GithubConnection(index_cfg)
            self.connections[index_cfg.name] = gc

        self.projects = {}

    @property
    def repo_2_connection(self) -> dict[str, "GithubConnection"]:
        if self._repo_2_connection is None:
            self._repo_2_connection = self._make_repos()
        return self._repo_2_connection

    def _make_repos(self) -> dict:
        d: dict[str, GithubConnection] = {}
        for gc in self.connections.values():
            repo_filter = set(gc.config.repos) if "repos" in gc.config else None
            for repo in gc.g.get_user().get_repos():
                if repo_filter and repo.name not in repo_filter:
                    continue
                d[repo.name] = gc
        return d


@dataclass
class GithubConnection:
    config: IndexConfig

    _g: Github = None
    _auth = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def uri(self) -> str:
        return self.config.uri

    @property
    def repo_names(self) -> list[str]:
        return self.config.repos

    @property
    def auth(self) -> Auth.Token:
        if self._auth is None:
            self._auth = Auth.Token(self.config.access_token)
        return self._auth

    @property
    def g(self) -> Github:
        if self._g is None:
            self._g = Github(auth=self.auth)

        return self._g

    def list_release_assets(
        self,
        repo: Repository,
    ) -> list[GitReleaseAsset]:
        """
        Get all assets for all releases in a repository
        args:
            repo: Repository.Repository
        returns:
            list[GitReleaseAsset.GitReleaseAsset]
        """
        assets = []
        for release in repo.get_releases():
            for asset in release.get_assets():
                assets.append(asset)
        return assets

    def get_release_asset(
        self,
        repo: Repository,
        release: str | GitRelease,
        asset_name: str,
        dest_folder: str | StringIO | BytesIO,
        overwrite: bool = False,
    ) -> ReleaseAsset:
        asset_name = asset_name.split("/")[-1]
        if not isinstance(release, GitRelease):
            try:
                release = repo.get_release(release)
            except Exception as e:
                raise Exception(f"Release {release} not found") from e
        if release is None:
            raise Exception(f"Release {release} not found")

        for asset in release.assets:
            if asset.name != asset_name:
                continue
            session = requests.Session()
            headers = {
                "Authorization": "token " + self.auth.token,
                "Accept": "application/octet-stream",
            }
            os.makedirs(dest_folder, exist_ok=True)
            dest = os.path.join(dest_folder, asset.name)
            asset.local_path = dest
            if os.path.exists(dest) and not overwrite:
                log.debug(f"File {dest} already exists, skipping")
                return asset

            response = session.get(asset.url, stream=True, headers=headers)
            with open(dest, "wb") as f:
                for chunk in response.iter_content(1024 * 1024):
                    f.write(chunk)
            return asset
        return None
