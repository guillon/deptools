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

dir=`dirname $0`
dir=`cd $dir; pwd`
TEST="env PYTHONPATH=$dir/.. python $dir/svn.py"

tmpdir=`mktemp -d -t tmp.XXXXXX`
tmpbase=`basename $0 .sh`.tmp

cd $tmpdir
cwd=$tmpdir

# Be sure that svn is present
svn --version >/dev/null || error "svn: command not found. Subversion must be installed for the svn plugin to work"
svn --version | head -n 1

# Be sure we are not in a svn repository while performing this test
svn info >/dev/null 2>&1 && \
    echo "error: this script must not run in a svn repository" && exit 1

# Clean from previous runs
rm -rf ${tmpbase}*

# Prepare bare svn
svnadmin create ${tmpbase}.1

# Prepare tree from work dir and push to bare
svn co file://$cwd/${tmpbase}.1 ${tmpbase}.1.work
cd ${tmpbase}.1.work
mkdir trunk branches tags
svn add trunk branches tags
svn commit -m 'Initial svn tree'
cd trunk
echo "a file" >afile
svn add afile
svn commit -m 'Added afile'
cd ../..

# Prepare dependency spec
cat >${tmpbase}.1.dep <<EOF
name: a_test_dep
component:
  alias: ${tmpbase}.dep
  format: svn
  label: trunk
  repos: file://$cwd/${tmpbase}.1
  revision: HEAD
EOF

# A deptools session
$TEST ${tmpbase}.1.ser new ${tmpbase}.1.dep
$TEST ${tmpbase}.1.ser extract 
$TEST ${tmpbase}.1.ser dump
$TEST ${tmpbase}.1.ser dump_actual
$TEST ${tmpbase}.1.ser dump_head
$TEST ${tmpbase}.1.ser update
$TEST ${tmpbase}.1.ser execute touch bfile
$TEST ${tmpbase}.1.ser execute svn add bfile
$TEST ${tmpbase}.1.ser commit -m 'Added empty bfile'
$TEST ${tmpbase}.1.ser execute touch cfile

# Add a new file in the work repository
cd ${tmpbase}.1.work/trunk
echo "d file" >dfile
svn add dfile
svn update
svn commit -m 'Added dfile'
cd ../..

# A second deptools session
$TEST ${tmpbase}.1.ser update
$TEST ${tmpbase}.1.ser execute svn add cfile
$TEST ${tmpbase}.1.ser commit -m 'Added empty cfile'

# Now checks that the repository is ok
svn co file://$cwd/${tmpbase}.1/trunk ${tmpbase}.final
cd ${tmpbase}.final
[ -f afile -a  "`cat afile`" = "a file" ] || error "missing afile"
[ -f bfile -a "`cat bfile`" = "" ] || error "missing bfile"
[ -f cfile -a "`cat cfile`" = "" ] || error "missing cfile"
[ -f dfile -a "`cat dfile`" = "d file" ] || error "missing dfile"

# Notify success
echo SUCCESS

rm -rf $tmpdir
