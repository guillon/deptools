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

from subprocess import call
from subprocess import check_call
from plugins import SourceManager
import os, sys
import yaml

verbose = 0

class SvnConfig:
    def __init__(self):
        self.svn = 'svn'
        self.verbose = 0

class SvnManager(SourceManager):
    """ This class implements the svn format manager plugin.
    The tests for this class are in test_svn_*.sh.
    The command line interface for this class is implemented in the
    SvnManagerCmdLine class below.
    The Configuration class for this class is the SvnConfig class.
    """
    plugin_name_ = "svn"
    plugin_description_ = "svn repository manager"
    
    def __init__(self, name, component, config = SvnConfig()):
        self.name_ = name
        self.component = component
        self.config = config
        if component['alias'] != None:
            self.basename = component['alias']
        else:
            self.basename = os.path.basename(self.component['repos'])
        self.branch = component['label']
        if self.branch != "trunk":
            self.branch = "branches/" + self.branch
        self.cwd = os.getcwd()

    def _cmd(self, args):
        if self.config.verbose:
            print " ".join(args)
        check_call(args)
    
    def _subcmd(self, args):
        if not os.path.exists(self.basename):
            raise Exception, "path does not exist: " + self.basename
        os.chdir(self.basename)
        self._cmd(args)
        os.chdir(self.cwd)
        
    def name(self):
        return self.name_

    def execute(self, args):
        if self.config.verbose:
            print "Execute " + self.basename
        self._subcmd(args)

    def extract(self, args = []):
        if self.config.verbose:
            print "Clone " + self.basename
        try:
            if os.path.exists(self.basename):
                print "Cannot extract component " +  self.name_ + ", path exists: " + self.basename + ". Skipped."
                return
            self._cmd([self.config.svn, 'checkout', self.component['repos'] + "/" + self.branch + "@" + str(self.component['revision']), self.basename])
        except Exception, e:
            raise Exception, "cannot clone component: " + str(e)
        
    def extract_or_updt(self, args = []):
        if self.config.verbose:
            print "Clone " + self.basename
        try:
            if os.path.exists(self.basename):
                self._subcmd([self.config.svn, 'update', '-r', str(self.component['revision'])])
                return
            self._cmd([self.config.svn, 'checkout', self.component['repos'] + "/" + self.branch + "@" + str(self.component['revision']), self.basename])
        except Exception, e:
            raise Exception, "cannot clone component: " + str(e)
        
    def update(self, args = []):
        if self.config.verbose:
            print "Update " + self.basename
        try:
            self._subcmd([self.config.svn, 'update', '-r', str(self.component['revision'])])
        except Exception, e:
            raise Exception, "cannot update component: " + str(e)

    def commit(self, args = []):
        if self.config.verbose:
            print "Commit " + self.basename
        try:
            self._subcmd([self.config.svn, 'commit' ] + args)
        except Exception, e:
            raise Exception, "cannot commit component: " + str(e)

    def rebase(self, args = []):
        if self.config.verbose:
            print "Rebase " + self.basename
        raise Exception, "svn format does not support rebase in subdir " + self.basename

    def deliver(self, args = []):
        if self.config.verbose:
            print "Deliver " + self.basename
        raise Exception, "svn format does not support deliver in subdir " + self.basename

    def dump(self, args = []):
        if self.config.verbose:
            print "Dump " + self.basename
        print yaml.dump(self.component)

    def get_actual_revision(self):
        try:
            self._subcmd([self.config.svn, 'update'])
            self._subcmd([self.config.svn, 'info', '-r', 'HEAD'])
        except Exception, e:
            raise Exception, "cannot get actual revision: " + str(e)
        return "TODO"

    def get_head_revision(self):
        return "HEAD"

    def dump_actual(self, args = []):
        if self.config.verbose:
            print "Dump_actual " + self.basename
        actual = self.component
        actual['revision'] = self.get_actual_revision()
        print yaml.dump(actual)

    def dump_head(self, args = []):
        if self.config.verbose:
            print "Dump_head " + self.basename
        actual = self.component
        actual['revision'] = self.get_head_revision()
        print yaml.dump(actual)

    def list(self, args = []):
        if self.config.verbose:
            print "List " + self.basename
        if self.component['alias'] != None:
            alias_str = "," + self.component['alias']
        else:
            alias_str = ""
        print self.name_ + "," + self.component['label'] + "@" + str(self.component['revision']) +  "," + self.component['repos'] + alias_str


class SvnManagerCmdLine:
    """ This is a comand line class proxy for the SvnManager class.
    The principle is to maintain a serial file for the SvnManager object
    and apply internal method to the deserialized file, then serialize
    the object back to file.
    The special command new starts a new session by creating an object
    from a yaml dump of the constructors arguments.
    There is probably a much better way to implement the exec_cmd function
    by invoking directly the method name.
    Also the serialization of the SvnManager class may be refactored into
    a generic support, perhaps in a metaclass.
    Refer to test_svn_01.sh for example of usage.
    """
    def __init__(self, args):
        self._serial = args[0]
        self._manager = None
        self._exec_cmd(args[1], args[2:])

    def _serialize_manager(self, manager, ostream = sys.stdout):
        print >> ostream, yaml.dump(manager)

    def _deserialize_manager(self, istream = sys.stdin):
        return yaml.load(istream)

    def _new_session(self, args_serials):
        params_stream = open(args_serials[0], "r")
        params = yaml.load(params_stream)
        self._manager = SvnManager(params['name'], params['component'])

    def _store_session(self):
        ofile = open(self._serial, "w")
        self._serialize_manager(self._manager, ofile)

    def _restore_session(self):
        ifile = open(self._serial, "r")
        self._manager = self._deserialize_manager(ifile)

    def _exec_cmd(self, cmd_name, args):
        if cmd_name == "new":
            self._new_session(args)
        else:
            self._restore_session()
            if cmd_name == "execute":
                self._manager.execute(args)
            elif cmd_name == "extract":
                self._manager.extract(args)
            elif cmd_name == "extract_or_updt":
                self._manager.extract_or_updt(args)
            elif cmd_name == "update":
                self._manager.update(args)
            elif cmd_name == "commit":
                self._manager.commit(args)
            elif cmd_name == "rebase":
                self._manager.rebase(args)
            elif cmd_name == "deliver":
                self._manager.deliver(args)
            elif cmd_name == "dump":
                self._manager.dump(args)
            elif cmd_name == "dump_actual":
                self._manager.dump_actual(args)
            elif cmd_name == "dump_head":
                self._manager.dump_head(args)
            elif cmd_name == "list":
                self._manager.list(args)
            else:
                print "unexpected command: ignored: " + " ".join(args)
        self._store_session()

if __name__ == "__main__":
    SvnManagerCmdLine(sys.argv[1:])
else:
    if verbose == 1:
        print "Loading " + __name__         
