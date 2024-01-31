import os

import bs4
from github import GitReleaseAsset


def write_index_html(
    project: str,
    release_assets: list[GitReleaseAsset.GitReleaseAsset],
    html_path: str,
    artifact_dir: str,
    template_dir: str,
) -> str:
    """
    Write an index.html file for a project's distribution.
    args:
        project: the name of the project
        release_assets: a list of release assets
        html_path: the path to the index.html
        artifact_dir: the directory where the release assets are stored
        template_dir: the directory containing the template
    returns:
    str: the path to the index.html file
    """
    template_path = os.path.join(template_dir, "distribution.html")
    with open(template_path) as f:
        soup = bs4.BeautifulSoup(f, features="html.parser")
    div = soup.find("div", {"class": "revisions"})
    for asset in release_assets:
        name = asset.browser_download_url.split("/")[-1]
        tag = soup.new_tag("a", href=f"/{artifact_dir}/{project}/{asset.name}")
        tag.string = name
        div.append(tag)
    os.makedirs(os.path.dirname(html_path), exist_ok=True)

    with open(html_path, "w") as f:
        f.write(soup.prettify())
    return html_path
