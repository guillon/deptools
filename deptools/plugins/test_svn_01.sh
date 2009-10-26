
#!/bin/sh
set -e

error() {
    echo "error: $*"
    exit 1
}

dir=`dirname $0`
dir=`cd $dir; pwd`
TEST="env PYTHONPATH=$dir/.. python $dir/svn.py"

tmpdir=`mktemp -d `
tmpbase=`basename $0 .sh`.tmp

cd $tmpdir
cwd=$tmpdir

# Be sure that svn is present
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
$TEST ${tmpbase}.1.ser clone 
$TEST ${tmpbase}.1.ser dump
$TEST ${tmpbase}.1.ser dump_actual
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
