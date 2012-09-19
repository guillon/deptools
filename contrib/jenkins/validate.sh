#!/usr/bin/env bash
#
# Unitary tests for deptools
#

[ "$DEBUG" = "" ] || set -x

mydir=`dirname $0`
srcdir=`cd $mydir/../..;pwd`

WORKSPACE=${WORKSPACE:-$srcdir}
LOGS=${LOGS:-${WORKSPACE}/logs}
mkdir -p ${LOGS}
rm -rf ${LOGS}/*

. /sw/st/gnu_compil/gnu/scripts/pre-all-paths.sh

cleanup() { local status=$?; rm -f $tmp_file; exit $status; }

tmp_file=/tmp/test_deptools_tmp_$$
trap "cleanup" INT QUIT TERM EXIT

echo "Running make check" > ${LOGS}/test_report.log
cd ${srcdir}
make check >>  ${LOGS}/test_report.log
