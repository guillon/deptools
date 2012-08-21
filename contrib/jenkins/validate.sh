#!/usr/bin/env bash
#
# Unitary tests for deptools
#

mydir=`dirname $0`
mydir=`cd $mydir/../..;pwd`

WORKSPACE=${WORKSPACE:-$mydir}
artifacts=${WORKSPACE}/logs
mkdir -p ${artifacts}

cleanup() { rm -f $tmp_file; }

declare -i nfail=0
declare -i nskip=0
error() { echo $0: ERROR: $* >&2; exit 1; }
check() {
    local -i return=$1
    local -i res
    shift
    echo -n "Test: $* ..."
    if [ "$VERBOSE" != "" ]; then
    $*
    else
	$* >/dev/null 2>&1
    fi
    res=$?
    if [ $res != $return ]; then
	echo "FAILED: returned $res, expected $return"
	nfail=`expr $nfail + 1`
    else
	echo "ok."
    fi
}

check_not() {
    local -i return=$1
    local -i res
    shift
    echo -n "Test: $* ..."
    if [ "$VERBOSE" != "" ]; then
        $*
    else
        $* >/dev/null 2>&1
    fi
    res=$?
    if [ $res = $return ]; then
	echo "FAILED: returned $res, expected $return"
	nfail=`expr $nfail + 1`
    else
	echo "ok."
    fi
}

msg_check() {
    local -i return=$1
    local msg="$2"
    local -i res
    shift
    shift
    echo -n "Test: $* ..."
    $* >$tmp_file 2>&1
    res=$?
    if [ $res != $return ]; then
	echo "FAILED: returned $res, expected $return"
	nfail=`expr $nfail + 1`
    else
	if [ "`grep \"$msg\" $tmp_file`" = "" ]; then
	    echo "FAILED: expected \"$msg\" in output missing. Got:"
	    cat $tmp_file
	    nfail=`expr $nfail + 1`
	else 
	    echo "ok."
	fi
    fi
}

tmp_file=/tmp/test_deptools_tmp_$$
trap "cleanup" 0 1 2 15

echo "Something has to be done here" > ${artifacts}/test_report.log
exit 0
