#!/bin/sh
#
# This software is delivered under the terms of the MIT License
#
# Copyright (c) 2009 Christophe Guillon <christophe.guillon.perso@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

set -e

[ "$DEBUG" = "" ] || set -x

error() {
    echo "error: $*"
    exit 1
}

user=${USER}
hostname=`hostname`
dir=`dirname $0`
dir=`cd $dir; pwd`
TEST="env PYTHONPATH=$dir/.. python $dir/path.py"

tmpdir=`mktemp -d -t tmp.XXXXXX`
tmpbase=`basename $0 .sh`.tmp

echo "Working dir: $tmpdir"
cd $tmpdir
cwd=$tmpdir

# Clean from previous runs
rm -rf ${tmpbase}*

# Prepare tree from work dir
mkdir -p ${tmpbase}.1.work
cd ${tmpbase}.1.work
echo "a file" >afile
echo "b file" >bfile
ln -s bfile blink
mkdir c
echo "d file" >c/dfile
cd ..

# Prepare dependency specs
cat >${tmpbase}.1.dep <<EOF
name: a_test_dep
component:
  format: path
  repos: $cwd/${tmpbase}.1.work/afile
EOF
$TEST ${tmpbase}.1.ser new ${tmpbase}.1.dep

cat >${tmpbase}.2.dep <<EOF
name: a_rev_test_dep
component:
  format: path
  repos: $cwd/${tmpbase}.1.work/afile
  revision: 716d1aa00cf64b8f25f59f5fbbc60e51a211fea3
EOF
$TEST ${tmpbase}.2.ser new ${tmpbase}.2.dep

cat >${tmpbase}.3.dep <<EOF
name: a_content_test_dep
component:
  format: path
  repos: $cwd/${tmpbase}.1.work/afile
  digest_content: true
EOF
$TEST ${tmpbase}.3.ser new ${tmpbase}.3.dep

cat >${tmpbase}.4.dep <<EOF
name: dir_test_dep
component:
  format: path
  repos: $cwd/${tmpbase}.1.work
EOF
$TEST ${tmpbase}.4.ser new ${tmpbase}.4.dep

# A deptools session
$TEST ${tmpbase}.1.ser extract
$TEST ${tmpbase}.1.ser extract # second extract should be ok
$TEST ${tmpbase}.1.ser dump_actual
$TEST ${tmpbase}.1.ser dump_head
$TEST ${tmpbase}.1.ser dump
$TEST ${tmpbase}.1.ser list
$TEST ${tmpbase}.1.ser execute cat afile
$TEST ${tmpbase}.2.ser extract
$TEST ${tmpbase}.2.ser extract_or_updt
$TEST ${tmpbase}.2.ser dump_actual
$TEST ${tmpbase}.2.ser list
$TEST ${tmpbase}.3.ser extract
$TEST ${tmpbase}.3.ser extract_or_updt
$TEST ${tmpbase}.3.ser dump_actual
$TEST ${tmpbase}.3.ser list
$TEST ${tmpbase}.4.ser list
$TEST ${tmpbase}.4.ser extract
$TEST ${tmpbase}.4.ser extract_or_updt
$TEST ${tmpbase}.4.ser dump_actual
$TEST ${tmpbase}.4.ser list

# No op operations
$TEST ${tmpbase}.4.ser update
$TEST ${tmpbase}.4.ser commit
$TEST ${tmpbase}.4.ser rebase
$TEST ${tmpbase}.4.ser deliver

# Notify success
echo SUCCESS

rm -rf $tmpdir
