#!/bin/bash
# Roda pytest no sandbox Linux, limpando null bytes e CRLFs dos arquivos.
# Necessário porque o venv foi criado no Windows e não roda no Linux.

PROJECT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
TMP=/tmp/sgw

rm -rf "$TMP"
cp -r "$PROJECT" "$TMP"
find "$TMP" \( -name "*.py" -o -name "*.toml" \) | xargs sed -i 's/\x00//g; s/\r//'
cd "$TMP" && python3 -m pytest "$@"
