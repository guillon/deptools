#!/bin/sh
dir=`dirname $0`
res=0
for i in $dir/plugins/test_*.sh
do
    $i
    [ $? = 0 ] || res=1
done
echo
[ $res = 0 ] && echo "PASSED: all tests passed"
[ $res = 0 ] || echo "FAILED: some tests failed"
exit $res
