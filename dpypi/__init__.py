import os

from pi_conf import set_config

cfg = set_config("dpypi")

## Get the root directory of this project
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
