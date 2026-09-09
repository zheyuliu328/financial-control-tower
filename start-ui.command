#!/bin/sh
# The tool and Excel dependencies live in a project-owned environment.
set -eu
FCT_PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$FCT_PROJECT_ROOT"
if ! command -v python3 >/dev/null 2>&1; then
  echo '请先安装 Python 3.9 或更新版本，再重新打开此文件。'
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else "需要 Python 3.9 或更新版本")'
if [ ! -x "$FCT_PROJECT_ROOT/.venv-ui/bin/python" ]; then
  echo '正在创建本工具的独立运行环境。'
  python3 -m venv "$FCT_PROJECT_ROOT/.venv-ui"
fi
FCT_EXPECTED_VERSION=$(python3 -c 'import re,pathlib; print(re.search(r"^version = \"([^\"]+)\"", pathlib.Path("pyproject.toml").read_text(), re.M)[1])')
FCT_INSTALLED_VERSION=$("$FCT_PROJECT_ROOT/.venv-ui/bin/python" -c 'from importlib.metadata import version; print(version("financial-control-tower"))' 2>/dev/null || true)
if [ "$FCT_EXPECTED_VERSION" != "$FCT_INSTALLED_VERSION" ] || [ ! -x "$FCT_PROJECT_ROOT/.venv-ui/bin/fct-ui" ] || ! "$FCT_PROJECT_ROOT/.venv-ui/bin/python" -c 'import openpyxl, defusedxml' >/dev/null 2>&1; then
  echo '首次安装或版本更新需要联网下载依赖；正常使用时文件只在本机处理。'
  "$FCT_PROJECT_ROOT/.venv-ui/bin/python" -m pip install '.[excel]'
fi
exec "$FCT_PROJECT_ROOT/.venv-ui/bin/fct-ui" "$@"
