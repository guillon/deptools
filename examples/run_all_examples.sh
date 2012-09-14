#!/bin/sh
#
# Test script for running all examples extraction.
# Some examples may depend upon a particular domain.
# Add the tests in the corresponding per domain
# variable.
#
set -e
[ "$DEBUG" = "" ] || set -x

# Add domain independent tests in test_any.
# Domain dependent tests in test_$domain
test_any="hello-cz deptools-all"
test_gnb="test-gnb1 test-gnb2 test-gnb3"

dir=`dirname $0`
host=`hostname`
case $host in
    gnx*) domain=gnb
	;;
    *) domain=""
esac

all_tests=`eval echo \\\$test_any \\\$test_$domain`
for test in $all_tests; do
    echo "Running Example $test"
    (cd $dir/$test && ls | grep -v DEPENDENCIES | xargs rm -rf && \
	../../deptools/deptool.py extract) || exit 1
done
