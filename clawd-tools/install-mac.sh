#!/usr/bin/env bash
set -euo pipefail

echo "OpenClaw Tools Installer (Mac/Linux)"

default="$HOME/clawd"
read -r -p "Enter your Clawd workspace path (default: $default): " workspace
workspace="${workspace:-$default}"

src="$(cd "$(dirname "$0")" && pwd)/tools"
dst="$workspace/tools"

mkdir -p "$dst"

echo "Copying tools to: $dst"
cp -R "$src"/* "$dst"/

echo ""
echo "Done."
echo "Next steps:"
echo "- Add any required env vars / secrets (do NOT commit them)"
echo "- Run the tools from inside your workspace as documented in tools/README.md"
