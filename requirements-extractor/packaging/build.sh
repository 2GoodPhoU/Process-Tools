#!/usr/bin/env bash
# Build a RequirementsExtractor binary on macOS or Linux.
#
# Usage:
#     ./packaging/build.sh
#
# On macOS this produces dist/RequirementsExtractor.app and a matching
# standalone binary at dist/RequirementsExtractor.  On Linux you just get
# the binary.  Cross-building to Windows from these platforms is not
# supported — run packaging\build.bat on a Windows machine for a .exe.

set -e
cd "$(dirname "$0")/.."

echo "=== Cleaning previous build artifacts ==="
rm -rf build dist

echo "=== Running PyInstaller ==="
pyinstaller packaging/RequirementsExtractor.spec --clean --noconfirm

echo
echo "=== Build complete ==="
ls -lh dist/
