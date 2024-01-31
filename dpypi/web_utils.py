import os

from github import GitReleaseAsset
html_index = """
<!DOCTYPE html>
<html lang="en">
  <body>
    {links}
  </body>
</html>
"""

def write_index_html(
    project: str,
    release_assets: list[GitReleaseAsset.GitReleaseAsset],
    html_path: str,
    artifact_dir: str,
) -> str:
    """
    Write an index.html file for a project's distribution.
    args:
        project: the name of the project
        release_assets: a list of release assets
        html_path: the path to the index.html
        artifact_dir: the directory where the release assets are stored
    returns:
    str: the path to the index.html file
    """
    
    links = []
    for asset in release_assets:
        name = asset.browser_download_url.split("/")[-1]
        # tag = soup.new_tag("a", href=f"/{artifact_dir}/{project}/{asset.name}")
        s = f'<a href="/{artifact_dir}/{project}/{asset.name}">{name}</a>'
        links.append(s)
    html = html_index.format(links="\n    ".join(links))
    
    os.makedirs(os.path.dirname(html_path), exist_ok=True)

    with open(html_path, "w") as f:
        f.write(html)
        # f.write(soup.prettify())
    return html_path
