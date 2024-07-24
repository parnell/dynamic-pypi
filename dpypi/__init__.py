import os

from pi_conf import load_config

cfg = load_config("dpypi")

## Get the root directory of this project
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
