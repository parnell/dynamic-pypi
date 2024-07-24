# dynamic-pypi


## Usage
Configure for pip or poetry, start server, then add as usual `pip install <mypackage>`

### Starting Dynamic PyPi server
```sh
# Start server
python dpypi/serve.py
```

### Pip
Configure pip to use your local server:
Create or edit a pip configuration file. On Unix systems, this is typically `~/.pip/pip.conf` or `/etc/pip.conf`. On Windows, it's `%APPDATA%\pip\pip.ini`.
Add the following content:

```ini
[global]
index-url = http://localhost:8083/simple
extra-index-url = https://pypi.org/simple
```

### Poetry
```toml
[[tool.poetry.source]]
name = "PyPI"
priority = "supplemental"

[[tool.poetry.source]]
name = "dpypi"
url = "http://localhost:8083"
priority = "default"
```