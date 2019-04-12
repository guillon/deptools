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

do_test() {
    echo "## ------------------------------------------------------------"
    echo "## $*"
    echo "## ------------------------------------------------------------"
    $TEST $*
}

dir=`dirname $0`
dir=`cd $dir; pwd`
TEST="env PYTHONPATH=$dir/.. python $dir/git.py"

tmpdir=`mktemp -d -t tmp.XXXXXX`
tmpbase=`basename $0 .sh`.tmp

cd $tmpdir
cwd=$tmpdir

# Be sure that git is present
git --version || error "git: command not found. Git must be installed for the git plugin to work"

# Be sure we are not in a git repository while performing this test
git rev-parse --git-dir >/dev/null 2>&1 && \
    echo "error: this script must not run in a git repository" && exit 1

# Clean from previous runs
rm -rf ${tmpbase}*

# Prepare tree from work dir and push to a new git reference
mkdir -p ${tmpbase}.1.work
cd ${tmpbase}.1.work
git init
echo "a file" >afile
git add afile
git commit -m 'Added afile'
git remote add origin $cwd/${tmpbase}.1.git
git clone --bare . $cwd/${tmpbase}.1.git
git log | cat
cd ..

# Prepare dependency spec
cat >${tmpbase}.1.dep <<EOF
name: a_test_dep
component:
  alias: ${tmpbase}.dep
  format: git
  label: master
  repos: $cwd/${tmpbase}.1.git
  revision: HEAD
EOF

# A deptools session
do_test ${tmpbase}.1.ser new ${tmpbase}.1.dep
do_test ${tmpbase}.1.ser extract
do_test ${tmpbase}.1.ser extract # second extract should be ok
do_test ${tmpbase}.1.ser dump
do_test ${tmpbase}.1.ser dump_actual
do_test ${tmpbase}.1.ser dump_head
do_test ${tmpbase}.1.ser update
do_test ${tmpbase}.1.ser execute touch bfile
do_test ${tmpbase}.1.ser extract_or_updt
do_test ${tmpbase}.1.ser execute git add bfile
do_test ${tmpbase}.1.ser commit -m 'Added_empty_bfile'
do_test ${tmpbase}.1.ser extract_or_updt
do_test ${tmpbase}.1.ser rebase
do_test ${tmpbase}.1.ser deliver
do_test ${tmpbase}.1.ser execute touch cfile
do_test ${tmpbase}.1.ser execute git add cfile
do_test ${tmpbase}.1.ser commit -m 'Added_empty_cfile'
do_test ${tmpbase}.1.ser execute rm afile
do_test ${tmpbase}.1.ser extract_or_updt


# Add a new file in the work repository
cd ${tmpbase}.1.work
echo "a file version 2" >afile
echo "d file" >dfile
git add dfile
git commit -am 'Added dfile and modified afile'
git fetch origin
git rebase origin/master
git push origin master
cd ..

# A second deptools session
do_test ${tmpbase}.1.ser extract_or_updt && exit 1 # should fail with conflict on afile
do_test ${tmpbase}.1.ser rebase && exit 1 # should fail with conflict on afile
do_test ${tmpbase}.1.ser execute git reset  --hard
do_test ${tmpbase}.1.ser extract_or_updt && exit 1 # should fail because needs rebase/merge
do_test ${tmpbase}.1.ser rebase
do_test ${tmpbase}.1.ser deliver
do_test ${tmpbase}.1.ser list
do_test ${tmpbase}.1.ser dump_actual

# Now checks that the repository is ok
git clone ${tmpbase}.1.git ${tmpbase}.final
cd ${tmpbase}.final
[ -f afile -a  "`cat afile`" = "a file version 2" ] || error "missing afile"
[ -f bfile -a "`cat bfile`" = "" ] || error "missing bfile"
[ -f cfile -a "`cat cfile`" = "" ] || error "missing cfile"
[ -f dfile -a "`cat dfile`" = "d file" ] || error "missing dfile"

# Notify success
echo SUCCESS

rm -rf $tmpdir
