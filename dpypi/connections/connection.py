import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from logging import getLogger
from typing import Optional

import requests
from github import Auth, Github
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.Repository import Repository as GitRepository
from pi_conf import Config
from pydantic import BaseModel


@dataclass
class Release(GitRelease):
    pass


@dataclass
class ReleaseAsset(GitReleaseAsset):
    ## Hack to add a local_path attribute to GitReleaseAsset for type hinting
    local_path: Optional[str] = None

    # def name(self) -> str:
    #     return self.browser_download_url.split("/")[-1]


@dataclass
class Repository(GitRepository):
    @property
    @abstractmethod
    def name(self) -> str: ...


class Connection:
    name: str

    @abstractmethod
    def list_release_assets(self, repo: Repository) -> list[ReleaseAsset]: ...

    @abstractmethod
    def get_release_asset(
        self,
        repo: Repository,
        release: str | Release,
        asset_name: str,
        dest_folder: str,
        overwrite: bool = False,
    ) -> Optional[ReleaseAsset]: ...

    @abstractmethod
    def get_repo(self, repo_name: str) -> Repository: ...
