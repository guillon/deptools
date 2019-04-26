#!/usr/bin/env bash
#
# Unitary tests for deptools
#
set -euo pipefail

[ "${DEBUG-}" = "" ] || set -x

mydir="$(dirname "$0")"
srcdir="$(readlink -e "$mydir/../..")"

WORKSPACE="${WORKSPACE:-$srcdir}"
LOGS="${LOGS:-${WORKSPACE}/logs}"
mkdir -p "$LOGS"
rm -rf "$LOGS"/*

cd "$srcdir"
echo "Running make all" | tee -a "$LOGS"/test_report.log
make all 2>&1 | tee -a "$LOGS"/test_report.log
echo "Running make check" | tee -a "$LOGS"/test_report.log
make check 2>&1 | tee -a "$LOGS"/test_report.log

