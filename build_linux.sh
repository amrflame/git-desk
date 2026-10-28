#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Build this target on Linux x86_64.' >&2
  exit 1
fi
build_python="${GIT_DESK_BUILD_PYTHON:-python3}"
"$build_python" -c 'import tkinter' || { echo 'The build Python must include Tkinter.' >&2; exit 1; }
build_dir="$project_dir/.build/linux"
output_dir="$project_dir/dist/linux-x86_64"
mkdir -p "$build_dir" "$output_dir"
"$build_python" -m venv "$build_dir/venv"
"$build_dir/venv/bin/python" -m pip install --disable-pip-version-check 'PyInstaller==6.22.3'
PYINSTALLER_CONFIG_DIR="$build_dir/cache" "$build_dir/venv/bin/python" -m PyInstaller \
  --noconfirm --clean --onefile --name GitDesk \
  --distpath "$output_dir" --workpath "$build_dir/work" --specpath "$build_dir" \
  "$project_dir/git_gui.py"
cp "$project_dir/packaging/linux/README.md" "$output_dir/README.md"
(cd "$output_dir" && sha256sum GitDesk > SHA256SUMS)
tar -czf "$project_dir/dist/GitDesk-Ubuntu-x86_64.tar.gz" -C "$output_dir" GitDesk README.md SHA256SUMS
echo "Ready: $output_dir/GitDesk"
