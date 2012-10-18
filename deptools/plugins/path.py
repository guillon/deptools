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

#
# This plugin to deptools implement a path component.
# A path component can be used to reference a path in a local
# filesystem. The content at the path location can be checked
# with the revision being a recursive digest of the content under
# path.
#
# The path is described as a file or directory absolute location
# with the repos entry:
# - repos: an URI (Uniform Resource Identifier) for the path
# Note: currently, only local path are supported, hence the URI
# must have the form '/my/path' or 'file:///my/path'.
#
# The optional fields of the component are:
# - revision: either HEAD (no check of content) or the treedigest
#   as returned for instance by dump_actual.
# - digest_content: set to 'true' for including files contents
#   digests, by default only the files sizes are included in the
#   digest.
# - ignore_status: set to 'true' for ignoring non-zero exit code
#   of the treedigest, useful for some paths where read accesses
#   for the user are not complete. Warning: this makes the digest
#   unsafe and thus should not be actually used when revision
#   is specified.
#

from subprocess import call
from plugins import SourceManager
from digester import digester
from core import UserException
import os, sys
import yaml
import tempfile

verbose = 0

class PathConfig:
    def __init__(self):
        self.verbose = 0

class PathManager(SourceManager):
    """ This class implements the path format manager plugin.
    The tests for this class are in test_path_*.sh.
    The command line interface for this class is implemented in the
    PathManagerCmdLine class below.
    The Configuration class for this class is the PathConfig class.
    """
    plugin_name_ = "path"
    plugin_description_ = "path reference manager"

    def __init__(self, name, component, config = PathConfig()):
        self.name_ = name
        self.config = config
        self.component = component

        # Check mandatory fields
        if 'repos' not in component:
            raise UserException("'missing 'repos' field in component")

        # Initialise plugin from available fields
        self.repos = str(component.get('repos'))
        self.revision = str(component.get('revision', "HEAD"))
        self.digest_content = component.get('digest_content', False)
        if type(self.digest_content) != type(True):
            raise UserException("field 'digest_content' must be either 'true' or 'false'")
        self.ignore_status = component.get("ignore_status", False)
        if type(self.ignore_status) != type(True):
            raise UserException("field 'ignore_status' must be either 'true' or 'false'")
        if self.repos.find("/") == 0:
            self.path = self.repos
        elif self.repos.find("file://") == 0:
            self.path = self.repos[len("file://"):]
        self.cwd = os.getcwd()

    def _cmd(self, args):
        if self.config.verbose:
            print " ".join(args)
        status = call(args)
        if status != 0:
            raise UserException("command returned non-zero status: %d: %s" %
                                (status, " ".join(["'"+x+"'" for x in args])))

    def _subcmd(self, args):
        if not os.path.exists(self.path):
            raise UserException("component path does not exist: " + self.path)
        os.chdir(self._dirname())
        self._cmd(args)
        os.chdir(self.cwd)

    def _dirname(self):
        if os.path.isdir(self.path):
            return self.path
        else:
            return os.path.dirname(self.path)

    def _check_digest(self, digest, expected):
        if expected != "HEAD" and digest != expected:
            raise UserException("component path digest mismatch: %s, digest %s, expected %s" %
                                (self.path, digest, self.revision))

    def _check_path(self):
        if not os.path.exists(self.path):
            raise UserException("cannot access component path: " + self.path)

    def _digest(self):
        list_file = tempfile.TemporaryFile()
        if os.path.isdir(self.path):
            digest_path = "."
        else:
            digest_path = os.path.basename(self.path)
        os.chdir(self._dirname())
        digest = digester(ignore_errors = self.ignore_status,
                          digest_content = self.digest_content,
                          stdout = list_file)
        retcode = digest.digest_list(digest_path)
        os.chdir(self.cwd)
        if retcode != 0:
            raise UserException("cannot compute digest for component path: " % self.path)
        list_file.seek(0)
        return digest.digest_file_content_(list_file)

    def name(self):
        return self.name_

    def execute(self, args):
        if self.config.verbose:
            print "Execute " + self.path
        self._subcmd(args)

    def extract(self, args = []):
        if self.config.verbose:
            print "Extracting " + self.path
        print "Extracting digest for component " + self.path
        self._check_path()
        digest = self._digest()
        self._check_digest(digest, self.revision)
        print "%s digest is %s" % (self.path, digest)

    def update(self, args = []):
        if self.config.verbose:
            print "Update " + self.path
        print "Update " + self.path + ": nothing to do for path"

    def extract_or_updt(self, args = []):
        if self.config.verbose:
            print "Extract or update " + self.path
        self.extract(args)

    def commit(self, args = []):
        if self.config.verbose:
            print "Commit " + self.path
        print "Commit " + self.path + ": nothing to do for path"

    def rebase(self, args = []):
        if self.config.verbose:
            print "Rebase " + self.path
        print "Rebase " + self.path + ": nothing to do for path"

    def deliver(self, args = []):
        if self.config.verbose:
            print "Deliver " + self.path
        print "Deliver " + self.path + ": nothing to do for path"

    def dump(self, args = []):
        if self.config.verbose:
            print "Dump " + self.path
        print yaml.dump(self.component)

    def get_actual_revision(self):
        try:
            revision = self._digest()
        except UserException, e:
            raise UserException("cannot get actual revision: " + str(e))
        return revision

    def get_head_revision(self):
        return "HEAD"

    def dump_actual(self, args = []):
        if self.config.verbose:
            print "Dump_actual " + self.path
        actual = self.component.copy()
        actual['revision'] = self.get_actual_revision()
        print yaml.dump(actual)

    def dump_head(self, args = []):
        if self.config.verbose:
            print "Dump_head " + self.path
        actual = self.component.copy()
        actual['revision'] = self.get_head_revision()
        print yaml.dump(actual)

    def list(self, args = []):
        if self.config.verbose:
            print "List " + self.path
        print self.name_ + "," + self.revision +  "," + self.repos


class PathManagerCmdLine:
    """ This is a comand line class proxy for the PathManager class.
    The principle is to maintain a serial file for the PathManager object
    and apply internal method to the deserialized file, then serialize
    the object back to file.
    The special command new starts a new session by creating an object
    from a yaml dump of the constructors arguments.
    There is probably a much better way to implement the exec_cmd function
    by invoking directly the method name.
    Also the serialization of the PathManager class may be refactored into
    a generic support, perhaps in a metaclass.
    Refer to test_path_01.sh for example of usage.
    """
    def __init__(self, args):
        self._serial = args[0]
        self._manager = None
        self._cmd_name = args[1]
        self._cmd_args = args[2:]

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
        self._manager = PathManager(params['name'], params['component'])

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

    def run(self):
        if self._cmd_name == "new":
            self._new_session(self._cmd_args)
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
            if self._cmd_name in dispatch:
                dispatch[self._cmd_name](self._cmd_args)
            else:
                print >>sys.stderr, "unexpected command, ignored: %s %s" % \
                    (self._cmd_name, " ".join(self._cmd_args))
        self._store_session()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        PathManagerCmdLine._error("missing arguments. Usage: path.py serial cmd ...")
    try:
        PathManagerCmdLine(sys.argv[1:]).run()
    except UserException, e:
        print >>sys.stderr, "error: %s" % str(e)
        sys.exit(1)
else:
    if verbose == 1:
        print "Loading " + __name__
