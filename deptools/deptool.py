#!/usr/bin/env python
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

import os, sys, getopt

# non standard package, use local version
import yaml

# SourceManagers
from plugins import SourceManager 
from plugins import PluginLoader

version = "0.0.1"

class DefaultConfig:
    def __init__(self):
        self.dep_file = "DEPENDENCIES"

class Config:
    def __init__(self, params):
        self.dep_file = params.dep_file

    def parse_options(self, opts, args):
        for o, a in opts:
            if o in ("-f", "--file"):
                self.dep_path = a
        #if len(args) > 0:
        #    self.prg_path = args

    def check(self):
        return True


class DependencyFile:
    def __init__(self, content = None):
        self.content = content
    def dump(self, ostream = sys.stdout):
        print >>ostream, yaml.dump(self.content)
    def load(self, istream = sys.stdin):
        self.content = yaml.load(istream)

class Dependency:
    def __init__(self, config, configuration="default"):
        self.config = config
        self.deps = None
        self.components = []
        self.configuration = configuration
        self.load()
        self.prepare()

    def load(self):
        stream = file(self.config.dep_file)
        deps =  DependencyFile()
        deps.load(stream)
        self.deps = deps.content
        
    def dump(self):
        deps = DependencyFile(self.deps)
        deps.dump()

    def prepare(self):
        list = self.deps["configurations"][self.configuration]
        self.components = []
        for component in list:
            repository = self.deps["repositories"][component]
            format = repository["format"]
            self.components.append(SourceManager.get_plugin(format)(component, repository))

    def foreach(self, command, args=[]):
        for component in self.components:
            if command == "execute":
                component.execute(args)
            elif command == "extract":
                component.extract(args)
            elif command == "update":
                component.update(args)
            elif command == "commit":
                component.commit(args)
            elif command == "rebase":
                component.rebase(args)
            elif command == "deliver":
                component.deliver(args)
            elif command == "dump":
                component.dump(args)
            elif command == "dump_actual":
                component.dump_actual(args)
            elif command == "list":
                component.list(args)
            else:
                error("unexpected command! " + command)

    def exec_cmd(self, command, args=[]):
        if command == "dump":
            self.dump()
        else:
            self.foreach(command, args)

def print_error(msg):
  print "error: " +  msg

def error(msg):
  print_error(msg)
  sys.exit(1)

def usage(config):
  print "usage: " + sys.argv[0] + " [options...] [cmd...]"
  print


def print_error(msg):
  print os.path.basename(sys.argv[0]) + ": error: " + msg

def error(msg):
  print_error(msg)
  sys.exit(1)

def usage(config):
  print "usage: " + sys.argv[0] + " [options...] [command...]"
  print
  print "where command is one of:"
  print " list: list all dependencies"
  print " extract: extract all dependencies"
  print " update: update all dependencies"
  print " commit: commit all dependencies"
  print " freeze: freeze all dependencies revisions"
  print " exec: execute command for all dependencies"
  print ""
  print "where options are:"
  print " -f|--file <dep_file> : dependency file. Default [" + config.dep_file + "]"
  print " -q|--quiet : quiet mode"
  print " -v|--version : output this script version"
  print " -h[--help : this help page"

def main():
    pdir = os.path.dirname(sys.argv[0])        
    pdir = os.path.abspath(pdir) 
    def_config = DefaultConfig()
    config = Config(def_config)
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "f:qvh", ["file=", "quiet", "version", "help"])
    except getopt.GetoptError, err:
        print_error(str(err))
        usage(def_config)
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage(def_config)
            sys.exit(0)
        elif o in ("-v", "--version"):
            print "deptool.py version " + version
            sys.exit(0)
    config.parse_options(opts, args)
    if not config.check():
        sys.exit(2)
    if len(args) == 0:
        error("missing command, try --help for usage")
    dependency = Dependency(config)
    dependency.exec_cmd(args[0], args[1:])
#    dependency.dump()

if __name__ == "__main__":
  main()
