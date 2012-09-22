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
TEST="env PYTHONPATH=$dir/.. python $dir/tar.py"

tmpdir=`mktemp -d -t tmp.XXXXXX`
tmpbase=`basename $0 .sh`.tmp

echo "Working dir: $tmpdir"
cd $tmpdir
cwd=$tmpdir

# Be sure that tools are present
tar --version || error "tar: command not found. tar must be installed for the tar plugin to work"
curl --version || error "curl: command not found. tar must be installed for the tar plugin to work"
which scp || error "scp: command not found. tar must be installed for the scp plugin to work"

# Clean from previous runs
rm -rf ${tmpbase}*

# Prepare tree from work dir and creates an archive
mkdir -p ${tmpbase}.1.work
cd ${tmpbase}.1.work
echo "a file" >afile
tar cvzf afile.tgz afile
echo "b file" >bfile
tar cvzf bfile.tgz bfile
cd ..

# Prepare dependency spec
cat >${tmpbase}.1.dep <<EOF
name: a_test_dep
component:
  alias: afile
  format: tar
  repos: $cwd/${tmpbase}.1.work/afile.tgz
EOF

# A deptools session
$TEST ${tmpbase}.1.ser new ${tmpbase}.1.dep
$TEST ${tmpbase}.1.ser extract 
$TEST ${tmpbase}.1.ser extract # second extract should be ok
$TEST ${tmpbase}.1.ser dump_actual
$TEST ${tmpbase}.1.ser dump_head
$TEST ${tmpbase}.1.ser dump
$TEST ${tmpbase}.1.ser list
$TEST ${tmpbase}.1.ser execute cat afile

# Prepare dependency spec
sum=`sha1sum ${cwd}/${tmpbase}.1.work/bfile.tgz | cut -f1 -d' '`
cat >${tmpbase}.2.dep <<EOF
name: b_test_dep
component:
  alias: b_dir
  format: tar
  repos: ssh://${user}@${hostname}${cwd}/${tmpbase}.1.work/bfile.tgz
  revision: ${sum}
EOF

# A deptools session
$TEST ${tmpbase}.2.ser new ${tmpbase}.2.dep
$TEST ${tmpbase}.2.ser extract 
$TEST ${tmpbase}.2.ser extract # second extract should be ok
$TEST ${tmpbase}.2.ser dump_actual
$TEST ${tmpbase}.2.ser dump_head
$TEST ${tmpbase}.2.ser dump
$TEST ${tmpbase}.2.ser list
$TEST ${tmpbase}.2.ser execute cat bfile

# Notify success
echo SUCCESS

rm -rf $tmpdir
