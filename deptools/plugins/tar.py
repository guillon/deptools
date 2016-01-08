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
# This plugin to deptools implement a tar component.
# A tar component must have the following fields in its
# repository description:
# - repos: an URI (Uniform Resource Identifier) for the archive
#
# The repos field URI supports the following schemes:
# - ssh: will use scp for the component retrieval
# - file/http[s]/ftp: will use curl for the component retrieval
# - if no scheme is given, the file:// scheme is assumed
#
# The file type must be one of:
# - .tar: a bare tar archive 
# - .tar.gz, .tgz: a tar+gzip archive
# - .tar.bz2: a tar+bzip2 archive
# - .tar.xz: a tar.xz archive
# - .zip: a zip archive
#
# The optional fields of the component are:
# - revision: either HEAD (no check of content) or the sha1sum
# - alias: the extraction dirname, default to archive basename
# - skip_dirs: specify the number of leading path components to
#   remove when extracting the archive into the dst dir, useful
#   for removing the top level dir of an archive.
# - ignore_status: set to 'true' for ignoring non-zero exit code
#   of the archive extraction, useful for some tar archives with
#   special files that can't be created but are useless.
#
 
from subprocess import call, check_call, Popen, PIPE
from plugins import SourceManager
import os, sys
import yaml
import tempfile, shutil, hashlib

verbose = 0

class TarConfig:
    def __init__(self):
        self.tar = 'tar'
        self.curl = 'curl'
        self.scp = 'scp'
        self.sha1sum = 'sha1sum'
        self.unzip = 'unzip'
        self.verbose = 0

class URI:
    """ URI management class. """
    class _type:
        """ Archive types constants. """
        TAR = 1
        TAR_GZ = 2
        TAR_BZ2 = 3
        TAR_XZ = 4
        ZIP = 5

    class _scheme:
        """ URI schemes constants. """
        FILE = 1
        SSH = 2
        HTTP = 3
        HTTPS = 4
        FTP = 5

    _scheme_names = { "file": _scheme.FILE,
                      "ssh": _scheme.SSH,
                      "http": _scheme.HTTP,
                      "https": _scheme.HTTPS,
                      "ftp": _scheme.FTP
                      }

    _extensions = { "tar": _type.TAR,
                    "tgz": _type.TAR_GZ,
                    "tar.gz": _type.TAR_GZ,
                    "tar.bz2": _type.TAR_BZ2,
                    "tar.xz": _type.TAR_XZ,
                    "zip": _type.ZIP,
                    }

    def __init__(self, uri):
        self.uri_ = uri
        parts = uri.split(":", 1)
        if len(parts) == 1:
            if len(parts[0]) == 0 or parts[0][0] != "/":
                raise Exception("missing scheme in URI: " + self.uri_)
            else:
                # Special case of file, we allow local file specification
                self.sch_ = "file"
                self.location_ = parts[0]
                self.remote_ = ""
                self.path_ = parts[0]
                self.uri_ = "file://" + self.path_
        else:
            self.sch_ = parts[0]
            parts = parts[1].split("/", 2)
            if len(parts) != 3 or parts[0] != "" or parts[1] != "" or parts[2] == "":
                raise Exception("malformed location in URI, truncated or missing '//': " + self.uri_)
            self.location_ = parts[2]
            parts = parts[2].split("/", 1)
            if len(parts) != 2:
                raise Exception("malformed path in URI location, missing starting '/': " + self.uri_)
            self.remote_ = parts[0]
            self.path_ = "/" + parts[1]

    def uri(self):
        """ Returns the full uri. """
        return self.uri_

    def scheme(self):
        """ Returns the scheme for the URI or None if not recognized. """
        return self._scheme_names.get(self.sch_)

    def base_and_ext(self):
        """ Returns a tuple for the basename and extension or (base, ""). """
        basename = self.basename()
        parts = self.path_.rsplit(".", 2)
        for i in range(1,len(parts)):
            if ".".join(parts[i:]) in self._extensions:
                return (".".join(parts[:i-1]), ".".join(parts[i:]))
        return (self.path_, "")

    def type(self):
        """ Returns the file type for the URI or None if not recognized. """
        (base, ext) = self.base_and_ext()
        return  self._extensions.get(ext)

    def dirname(self):
        """ Returns the dirname for the URI. """
        dir = self.path_.rsplit("/", 1)[0]
        if dir == "": dir = "/"
        return dir

    def basename(self):
        """ Returns the basename for the URI. """
        return self.path_.rsplit("/", 1)[1]

    def remote(self):
        """ Returns the remote specification for the URI or "". """
        return self.remote_

    def path(self):
        """ Returns the path specification for the URI. """
        return self.path_

class utils:
    """ This is a namespace for utility functions. """
    @staticmethod
    def move_dirs(srcdir, dstdir, skip_dirs=0):
        """
        Move the directory content of srcdir into dstdir.
        Optionally skipping the given number of lead path
        components when moving into dstdir.
        The directory dstdir must not exist before the call.
        For instance:
          move_dirs("src", "dst") does mv src/* dst/*
          move_dirs("src", "dst", skip_dirs=1) does
          for each src/<path>, mv src/<path>/* dst/
        """
        assert skip_dirs >= 0
        assert not os.path.exists(dstdir)
        assert os.path.isdir(srcdir)
        from os.path import join as join
        from os.path import isdir as isdir
        dirs = ["."]
        for depth in range(skip_dirs):
            new_dirs = []
            for y in dirs:
                for x in os.listdir(join(srcdir, y)):
                    if isdir(join(srcdir, y, x)):
                        new_dirs.append(join(y, x))
            dirs = new_dirs
        os.mkdir(dstdir)
        for y in dirs:
            for file in os.listdir(join(srcdir,y)):
                if os.path.exists(join(dstdir, file)):
                    raise Exception, "File exists " + join(dstdir, file)
                os.rename(join(srcdir, y, file), join(dstdir, file))

class TarManager(SourceManager):
    """ This class implements the tar format manager plugin.
    The tests for this class are in test_tar_*.sh.
    The command line interface for this class is implemented in the
    TarManagerCmdLine class below.
    The Configuration class for this class is the TarConfig class.
    """
    plugin_name_ = "tar"
    plugin_description_ = "tar archive manager"

    def __init__(self, name, component, config = TarConfig()):
        self.name_ = name
        self.config = config
        self.component = component

        # Check mandatory fields
        if 'repos' not in component:
            raise Exception("missing archive uri in component")

        # Initialise plugin from available fields
        self.repos = str(component.get('repos'))
        self.revision = str(component.get('revision', "HEAD"))
        uri = URI(self.repos)
        self.alias = str(component.get('alias', uri.basename()))
        self.basename = self.alias
        self.type = uri.type()
        self.scheme = uri.scheme()
        self.uri = uri.uri()
        self.remote = uri.remote()
        self.path = uri.path()
        self.ignore_status = component.get("ignore_status", False)
        if type(self.ignore_status) != type(True):
            raise Exception, "ignore_status field must be either 'true' or 'false'"
        self.skip_dirs = component.get("skip_dirs", 0)
        if type(self.skip_dirs) != type(0) or self.skip_dirs < 0:
            raise Exception, "skip_dirs field must be a positive integer"
        self.cwd = os.getcwd()

    def _cmd(self, args, ignore_status=False):
        if self.config.verbose:
            print " ".join(args)
        status = call(args)
        if not ignore_status and status != 0:
            raise Exception, ("command returned non-zero status " + str(status) +
                              ": " + " ".join(["'"+x+"'" for x in args]))

    def _cmd_output(self, args):
        if self.config.verbose:
            print " ".join(args)
        return Popen(args, stdout=PIPE).communicate()[0]
    
    def _subcmd(self, args, ignore_status=True):
        if not os.path.exists(self.basename):
            raise Exception("path does not exist: " + self.basename)
        os.chdir(self.basename)
        self._cmd(args, ignore_status)
        os.chdir(self.cwd)

    def _subcmd_output(self, args):
        if not os.path.exists(self.basename):
            raise Exception("path does not exist: " + self.basename)
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

    def _get_cached_archive(self):
        repo_sha1sum = hashlib.sha1(self.repos).hexdigest()
        repo_basename = os.path.basename(self.repos)
        return os.path.join(self._get_cachedir(),
                            repo_sha1sum[:2],
                            repo_sha1sum[2:],
                            repo_basename)

    def _get_tmpdir(self):
        dir = os.path.abspath(os.path.join(self.cwd, ".deptools", "tmp"))
        return dir

    def _make_tmpdir(self):
        tmpdir = self._get_tmpdir()
        if not os.path.exists(tmpdir):
            os.makedirs(tmpdir)
        return tempfile.mkdtemp(dir=tmpdir)
            
    def _fetch_archive(self):
        cached_archive = self._get_cached_archive()
        if (self.revision != "HEAD" and os.path.exists(cached_archive) and
            self.revision == self.get_actual_revision()):
            return
        try:
            if not os.path.exists(os.path.dirname(cached_archive)):
                os.makedirs(os.path.dirname(cached_archive))
            if self.scheme == URI._scheme.SSH:
                self._cmd([self.config.scp, self.remote + ":" + self.path, cached_archive])
            else:
                self._cmd([self.config.curl, "-o", cached_archive, self.uri])
        except Exception, e:
            raise Exception("cannot acces remote URI: " + self.repos + ": " + str(e))

    def _check_revision(self):
        if self.revision != "HEAD" and self.revision != self.get_actual_revision():
            raise Exception("archive component %s sha1sum (%s) mismatch expected sha1sum (%s)" %
                            (self.name_, self.get_actual_revision(), self.revision))


    def _extract_archive(self):
        assert not os.path.exists(self.basename)
        tmpdir = self._make_tmpdir()
        try:
            if self.type == URI._type.TAR:
                self._cmd([self.config.tar, "xf", self._get_cached_archive(), "-C", tmpdir],
                          self.ignore_status)
            elif self.type == URI._type.TAR_GZ:
                self._cmd([self.config.tar, "xzf", self._get_cached_archive(), "-C", tmpdir],
                          self.ignore_status)
            elif self.type == URI._type.TAR_BZ2:
                self._cmd([self.config.tar, "xjf", self._get_cached_archive(), "-C", tmpdir],
                          self.ignore_status)
            elif self.type == URI._type.TAR_XZ:
                self._cmd([self.config.tar, "xJf", self._get_cached_archive(), "-C", tmpdir],
                          self.ignore_status)
            elif self.type == URI._type.ZIP:
                self._cmd([self.config.unzip, "-q", "-d", tmpdir, self._get_cached_archive()],
                          self.ignore_status)
            else:
                raise Exception("unsupported file type in URI: " + self.repos)
            dirname = os.path.dirname(self.basename)
            if dirname == "": dirname = "."
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            utils.move_dirs(tmpdir, self.basename, self.skip_dirs)
        finally:
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)
            
    def name(self):
        return self.name_

    def execute(self, args):
        if self.config.verbose:
            print "Execute " + self.basename
        self._subcmd(args)

    def extract(self, args = []):
        if self.config.verbose:
            print "Extract " + self.basename
        if not os.path.exists(self.basename):
            try:
                self._fetch_archive()
                self._check_revision()
                self._extract_archive()
            except Exception, e:
                raise Exception("cannot extract component: " + str(e))
        else:
            print "Skipping extraction of existing '" + self.basename + "'"

    def update(self, args = []):
        if self.config.verbose:
            print "Update " + self.basename
        print "Update " + self.basename + ": nothing to do for archive"

    def extract_or_updt(self, args = []):
        if self.config.verbose:
            print "Extract or update " + self.basename
        if not os.path.exists(self.basename):
            self.extract(args)
        else:
            self.update(args)

    def commit(self, args = []):
        if self.config.verbose:
            print "Commit " + self.basename
        print "Commit " + self.basename + ": nothing to do for archive"

    def rebase(self, args = []):
        if self.config.verbose:
            print "Rebase " + self.basename
        print "Rebase " + self.basename + ": nothing to do for archive"

    def deliver(self, args = []):
        if self.config.verbose:
            print "Deliver " + self.basename
        print "Deliver " + self.basename + ": nothing to do for archive"

    def dump(self, args = []):
        if self.config.verbose:
            print "Dump " + self.basename
        print yaml.dump(self.component)

    def get_actual_revision(self):
        try:
            output = self._cmd_output([self.config.sha1sum, self._get_cached_archive()])
        except Exception, e:
            raise Exception("cannot get actual revision: " + str(e))
        return output.strip().split(" ")[0]

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
        print self.name_ + "," + self.revision +  "," + self.repos + "," + self.alias


class TarManagerCmdLine:
    """ This is a comand line class proxy for the TarManager class.
    The principle is to maintain a serial file for the TarManager object
    and apply internal method to the deserialized file, then serialize
    the object back to file.
    The special command new starts a new session by creating an object
    from a yaml dump of the constructors arguments.
    There is probably a much better way to implement the exec_cmd function
    by invoking directly the method name.
    Also the serialization of the TarManager class may be refactored into
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
        self._manager = TarManager(params['name'], params['component'])

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
        TarManagerCmdLine._error("missing arguments. Usage: git.py serial cmd ...")
    TarManagerCmdLine(sys.argv[1:])
else:
    if verbose == 1:
        print "Loading " + __name__         
