import os
from dataclasses import dataclass

@dataclass
class Wheel:
    """
    {distribution_name}-{version}-{pyversion}-{ABItag}-{platform}.whl
    """

    full_name: str
    distribution_name: str
    version: str
    pyversion: str
    ABItag: str
    platform: str

    @classmethod
    def from_path(cls, path: str):
        whl_name, ext = os.path.splitext(path)
        if ext != ".whl":
            raise Exception(f"Expected .whl file, got {ext}")
        whl = whl_name.split("/")[-1]

        splits = whl.split("-")
        w = cls(f"{whl}.whl", *splits)
        w.distribution_name = w.distribution_name.replace("_", "-")
        return w
