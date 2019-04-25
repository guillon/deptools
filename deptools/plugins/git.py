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

from subprocess import call, check_call, Popen, PIPE
from plugins import SourceManager
import os, sys, hashlib, shutil
import yaml

verbose = 0

class GitConfig:
    def __init__(self):
        self.git = 'git'
        self.verbose = 0

class GitManager(SourceManager):
    """ This class implements the git format manager plugin.
    The tests for this class are in test_git_*.sh.
    The command line interface for this class is implemented in the
    GitManagerCmdLine class below.
    The Configuration class for this class is the GitConfig class.
    """
    plugin_name_ = "git"
    plugin_description_ = "git repository manager"
    
    def __init__(self, name, component, config = GitConfig()):
        self.name_ = name
        self.config = config
        self.component = component

        # Check mandatory fields
        if 'repos' not in component:
            raise Exception, "missing repository url in component"
        self.repos = str(component['repos'])

        # Initialise plugin from available fields
        if 'alias' in component and component['alias'] != None:
            self.alias = str(component['alias'])
        else:
            self.alias = os.path.basename(self.repos)
            if self.alias.endswith(".git"):
                self.alias = self.alias.rsplit('.', 1)[0]
        self.basename = self.alias
        if 'label' in component and component['label'] != None:
            self.label = str(component['label'])
        else:
            self.label = "master"
        if 'revision' in component and component['revision'] != None:
            self.revision = str(component['revision'])
        else:
            self.revision = "HEAD"

        self.cwd = os.getcwd()

    def _cmd(self, args):
        if self.config.verbose:
            print " ".join(args)
        check_call(args)

    def _cmd_output(self, args):
        if self.config.verbose:
            print " ".join(args)
        return Popen(args, stdout=PIPE).communicate()[0]
    
    def _subcmd(self, args):
        if not os.path.exists(self.basename):
            raise Exception, "path does not exist: " + self.basename
        os.chdir(self.basename)
        self._cmd(args)
        os.chdir(self.cwd)

    def _subcmd_output(self, args):
        if not os.path.exists(self.basename):
            raise Exception, "path does not exist: " + self.basename
        os.chdir(self.basename)
        output = self._cmd_output(args)
        os.chdir(self.cwd)
        return output

    def _get_cachedir(self):
        dir = os.path.abspath(os.path.join(self.cwd,
                                           ".deptools",
                                           "cache",
                                           "plugins",
                                           self.plugin_name_))
        return dir

    def _get_cached_repo(self):
        repo_sha1sum = hashlib.sha1(self.repos).hexdigest()
        repo_basename = os.path.basename(self.repos)
        if not repo_basename.endswith(".git"):
            repo_basename += ".git"
        return os.path.join(self._get_cachedir(),
                            repo_sha1sum[:2],
                            repo_sha1sum[2:],
                            repo_basename)

    def _fetch_cached_repo(self):
        cached_repo = self._get_cached_repo()
        def _git_cached(args):
            self._cmd(['env', 'GIT_DIR=%s' % cached_repo,
                       self.config.git] + args)
        if not os.path.exists(cached_repo):
            os.makedirs(cached_repo)
            _git_cached(['init', '--bare'])
            _git_cached(['config', 'remote.origin.url',
                         self.repos])
            _git_cached(['config', '--add', 'remote.origin.fetch',
                         '+refs/heads/*:refs/heads/*'])
            _git_cached(['config', '--add', 'remote.origin.fetch',
                         '+refs/tags/*:refs/tags/*'])
        _git_cached(['fetch', 'origin', '--prune'])

    def name(self):
        return self.name_

    def execute(self, args):
        print "Executing command for component in '" + self.basename + "'"
        self._subcmd(args)

    def extract(self, args = []):
        if os.path.exists(self.basename) and "--force" in args:
            print "Removing directory '" + self.basename + "'"
            shutil.rmtree(self.basename)
        if not os.path.exists(self.basename):
            print "Extracting component in '" + self.basename + "'"
            try:
                self._fetch_cached_repo()
                self._cmd([self.config.git, 'clone', '--reference', self._get_cached_repo(),
                           '-b', self.label, self.repos, self.basename])
                self._subcmd([self.config.git, 'reset', '--hard', self.revision])
            except Exception, e:
                raise Exception, "cannot clone component: " + str(e)
        else:
            print "Skipping extraction of component in '" + self.basename + "'"

    def update(self, args = []):
        print "Updating component in '" + self.basename + "'"
        try:
            self._fetch_cached_repo()
            self._subcmd([self.config.git, 'pull', '--ff-only'])
        except Exception, e:
            raise Exception, "cannot update component: " + str(e)

    def extract_or_updt(self, args = []):
        if not os.path.exists(self.basename):
            self.extract(args)
        else:
            self.update(args)

    def commit(self, args = []):
        print "Commiting component in '" + self.basename + "'"
        try:
            self._subcmd([self.config.git, 'commit' ] + args)
        except Exception, e:
            raise Exception, "cannot commit component: " + str(e)

    def rebase(self, args = []):
        print "Rebasing component in '" + self.basename + "'"
        try:
            self._fetch_cached_repo()
            self._subcmd([self.config.git, 'pull', '--rebase'])
        except Exception, e:
            raise Exception, "cannot rebase component: " + str(e)

    def deliver(self, args = []):
        print "Delivering component in '" + self.basename + "'"
        try:
            self._fetch_cached_repo()
            self._subcmd([self.config.git, '-c', 'push.default=upstream', 'push'])
        except Exception, e:
            raise Exception, "cannot deliver component: " + str(e)

    def dump(self, args = []):
        if self.config.verbose:
            print "Dump " + self.basename
        print yaml.dump(self.component)

    def get_actual_revision(self):
        try:
            revision = self._subcmd_output([self.config.git, 'rev-parse', 'HEAD']).strip()
        except Exception, e:
            raise Exception, "cannot get actual revision: " + str(e)
        return revision

    def get_head_revision(self):
        return "HEAD"

    def dump_actual(self, args = []):
        if self.config.verbose:
            print "Dump_actual " + self.basename
        actual = self.component.copy()
        actual['revision'] = self.get_actual_revision()
        print yaml.dump(actual)

    def dump_head(self, args = []):
        if self.config.verbose:
            print "Dump_head " + self.basename
        actual = self.component.copy()
        actual['revision'] = self.get_head_revision()
        print yaml.dump(actual)

    def list(self, args = []):
        if self.config.verbose:
            print "List " + self.basename
        print self.name_ + "," + self.label + "@" + self.revision +  "," + self.repos + "," + self.alias


class GitManagerCmdLine:
    """ This is a comand line class proxy for the GitManager class.
    The principle is to maintain a serial file for the GitManager object
    and apply internal method to the deserialized file, then serialize
    the object back to file.
    The special command new starts a new session by creating an object
    from a yaml dump of the constructors arguments.
    There is probably a much better way to implement the exec_cmd function
    by invoking directly the method name.
    Also the serialization of the GitManager class may be refactored into
    a generic support, perhaps in a metaclass.
    Refer to test_git_01.sh for example of usage.
    """
    def __init__(self, args):
        self._serial = args[0]
        self._manager = None
        self._exec_cmd(args[1], args[2:])

    @staticmethod
    def error(msg):
        print >>sys.stderr, sys.argv[0] + ": error: "+ msg
        sys.exit(1)

    def _serialize_manager(self, manager, ostream = sys.stdout):
        print >> ostream, yaml.dump(manager)

    def _deserialize_manager(self, istream = sys.stdin):
        return yaml.load(istream)

    def _new_session(self, args_serials):
        try:
            params_stream = open(args_serials[0], "r")
        except IOError, e:
            self.error("can't open serial: " + str(e))
        with params_stream:
            params = yaml.load(params_stream)
        self._manager = GitManager(params['name'], params['component'])

    def _store_session(self):
        try:
            ofile = open(self._serial, "w")
        except IOError, e:
            self.error("can't write serial: " + str(e))
        with ofile:
            self._serialize_manager(self._manager, ofile)

    def _restore_session(self):
        try:
            ifile = open(self._serial, "r")
        except IOError, e:
            self.error("can't open serial: " + str(e))
        with ifile:
            self._manager = self._deserialize_manager(ifile)

    def _exec_cmd(self, cmd_name, args):
        if cmd_name == "new":
            self._new_session(args)
        else:
            self._restore_session()
            dispatch = { 'execute': self._manager.execute,
                         'extract': self._manager.extract,
                         'extract_or_updt': self._manager.extract_or_updt,
                         'update': self._manager.update,
                         'commit': self._manager.commit,
                         'rebase': self._manager.rebase,
                         'deliver': self._manager.deliver,
                         'dump': self._manager.dump,
                         'dump_actual': self._manager.dump_actual,
                         'dump_head': self._manager.dump_head,
                         'list': self._manager.list }
            if cmd_name in dispatch:
                dispatch[cmd_name](args)
            else:
                print "unexpected command, ignored: " + cmd_name + " ".join(args)
        self._store_session()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        GitManagerCmdLine._error("missing arguments. Usage: git.py serial cmd ...")
    GitManagerCmdLine(sys.argv[1:])
else:
    if verbose == 1:
        print "Loading " + __name__         
