#!/bin/sh
res=0
for i in plugins/test_*.sh
do
    $i
    [ $? = 0 ] || res=1
done
[ $res = 0 ] || echo "FAILED: some tests failed"
exit $res
