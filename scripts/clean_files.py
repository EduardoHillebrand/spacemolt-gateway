#!/usr/bin/env python3
"""Remove null bytes and normalize line endings in text files."""
import os
import sys

EXTS = {'.py', '.toml', '.md', '.sh', '.txt', '.yaml', '.yml', '.json'}
root = sys.argv[1]

for dirpath, _, files in os.walk(root):
    for fname in files:
        if any(fname.endswith(e) for e in EXTS):
            path = os.path.join(dirpath, fname)
            try:
                data = open(path, 'rb').read()
                null = b'\x00'
                cr = b'\r\n'
                lone_cr = b'\r'
                cleaned = data.replace(null, b'').replace(cr, b'\n').replace(lone_cr, b'\n')
                if cleaned != data:
                    open(path, 'wb').write(cleaned)
            except Exception as e:
                print(f'Warning: {path}: {e}', file=sys.stderr)
