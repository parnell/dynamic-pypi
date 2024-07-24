import os
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from logging import getLogger
from typing import Optional, cast

import requests
from github import Auth, Github
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.Repository import Repository as GitRepository
from pi_conf import Config
from pydantic import BaseModel

from dpypi.connections.connection import Connection, ReleaseAsset, Repository

log = getLogger(__name__)

REDACT_KEYS = set(["access_token"])


class IndexConfig(BaseModel):
    name: str
    uri: str
    repos: Optional[list[str]] = None
    access_token: Optional[str] = None


@dataclass
class GithubConnection(Connection):
    name : str
    config: IndexConfig

    _g: Optional[Github] = None
    _auth = None

    # @property
    # def name(self) -> str:
    #     return self.config.name

    @property
    def uri(self) -> str:
        return self.config.uri

    @property
    def repo_names(self) -> Optional[list[str]]:
        return self.config.repos

    @property
    def auth(self) -> Auth.Token:
        if self._auth is None and self.config.access_token:
            self._auth = Auth.Token(self.config.access_token)
        if not self._auth:
            raise Exception("No access token provided")
        return self._auth

    @property
    def g(self) -> Github:
        if self._g is None:
            self._g = Github(auth=self.auth)

        return self._g

    def get_repo(self, repo_name: str) -> Repository:
        return cast(Repository, self.g.get_repo(repo_name))

    def list_release_assets(
        self,
        repo: Repository,
    ) -> list[ReleaseAsset]:
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
                setattr(asset, "local_path", None)
                a = cast(ReleaseAsset, asset)
                assets.append(a)
        return assets

    def get_release_asset(
        self,
        repo: Repository,
        release: str | GitRelease,
        asset_name: str,
        dest_folder: str ,
        overwrite: bool = False,
    ) -> Optional[ReleaseAsset]:
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
            setattr(asset, "local_path", dest)
            a = cast(ReleaseAsset, asset)
            if os.path.exists(dest) and not overwrite:
                log.debug(f"File {dest} already exists, skipping")
                return a

            response = session.get(asset.url, stream=True, headers=headers)
            with open(dest, "wb") as f:
                for chunk in response.iter_content(1024 * 1024):
                    f.write(chunk)
            return a
        return None
