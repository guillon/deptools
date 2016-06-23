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

import os, sys
import argparse, copy

# non standard package, use local version
import yaml

# SourceManagers
from core import UserException
from plugins import SourceManager
from plugins import PluginLoader

version = "0.0.1"

class DefaultConfig:
    def __init__(self):
        self.dep_file = "DEPENDENCIES"
        self.configuration = "default"

class Config:
    def __init__(self, params):
        self.dep_file = params.dep_file
        self.configuration = params.configuration

    def handle_options(self, opts, args):
        self.dep_file = opts.dep_file
        self.configuration = opts.configuration

    def check(self):
        return True


class Check:
    @staticmethod
    def check(v, check_function):
        if isinstance(v, list):
            Check.check_list(v, check_function)
        elif isinstance(v, dict):
            Check.check_dict(v, check_function)
        else:
            check_function(v)

    @staticmethod
    def check_dict(d, check_function):
        for k, v in d.items():
            Check.check(v, check_function)

    @staticmethod
    def check_dict_values(d, check_function):
        for _, v in d.items():
            check_function(k)
            Check.check(v, check_function)

    @staticmethod
    def check_dict_keys(d, check_function):
        for k in d:
            check_function(k)

    @staticmethod
    def check_list(l, check_function):
        for v in l:
            Check.check(v, check_function)

class DependencyFile:
    def __init__(self, content = None):
        self.content = content

    def dump(self, ostream = sys.stdout):
        print >>ostream, yaml.dump(self.content)

    def load(self, istream = sys.stdin):
        self.content = yaml.load(istream)

class Dependency:
    def __init__(self, config):
        self.config = config
        self.deps = None
        self.components = []
        self.load()
        self.prepare()

    def load(self):
        if self.config.dep_file == "-":
            stream = sys.stdin
        else:
            try:
                stream = file(self.config.dep_file)
            except IOError, e:
                raise UserException("cannot access dependencies file %s: %s" % \
                                        (self.config.dep_file, e.strerror))
        deps =  DependencyFile()
        deps.load(stream)
        self.deps = deps.content

    def dump(self, component_names=[]):
        DependencyFile(self.deps).dump()

    def dump_actual(self, component_names=[]):
        if component_names == []:
            component_names = self.deps['configurations'][self.config.configuration]
        deps_actual = copy.deepcopy(self.deps)
        for component in self.components:
            name = component.name()
            if name in component_names:
                actual = component.get_actual_revision()
                deps_actual['repositories'][name]['revision'] = actual
        DependencyFile(deps_actual).dump()

    def dump_head(self, component_names=[]):
        if component_names == []:
            component_names = self.deps['configurations'][self.config.configuration]
        deps_head = copy.deepcopy(self.deps)
        for component in self.components:
            name = component.name()
            if name in component_names:
                head = component.get_head_revision()
                deps_head['repositories'][name]['revision'] = head
        DependencyFile(deps_head).dump()

    def prepare(self):
        def assert_string(v, msg=""):
            if not isinstance(v, (str, unicode)):
                raise UserException(
                    "%svalue is not a string, please use quotes: %s" % (msg, str(v)))
        configurations = self.deps.get("configurations")
        if configurations == None or type(configurations) != type({}):
            raise Exception, "Missing configurations map in dependency file: " + self.config.dep_file
        Check.check(configurations, lambda x: assert_string(x, "in configurations: "))
        components = configurations.get(self.config.configuration)
        if components == None or type(components) != type([]):
            raise Exception, "Missing components list specification for configuration: " + self.config.configuration
        repositories = self.deps.get("repositories")
        if repositories == None or type(repositories) != type({}):
            raise Exception, "Missing repositories map in dependency file: " + self.config.dep_file
        Check.check_dict_keys(repositories, lambda x: assert_string(x, "in repositories names: "))
        self.components = []
        for component in components:
            repository = repositories.get(component)
            if repository == None or type(repository) != type({}):
                raise Exception, "Missing repository map for component: " + component
            format = repository.get("format")
            if format == None or type(format) != type(""):
                raise Exception, "Missing format specification for component: " + component
            self.components.append(SourceManager.get_plugin(format)(component, repository))

    def foreach(self, command, args=[]):
        for component in self.components:
            method = None
            try:
                method = eval("component." + command)
            except AttributeError:
                print("Skipped component " + component.name() + ": does not implement " + command)
            if method != None: method(args)

    def exec_cmd(self, command, args=[]):
        command_list = [ 'execute', 'extract', 'extract_or_updt',
                         'update', 'commit', 'rebase', 'deliver',
                         'dump', 'dump_actual', 'dump_head', 'list' ]
        if command == "dump":
            self.dump(args)
        elif command == "dump_actual":
            self.dump_actual(args)
        elif command == "dump_head":
            self.dump_head(args)
        elif command in command_list:
            self.foreach(command, args)
        else:
            raise UserException("unexpected command: %s" % command)

def print_error(msg):
  print >>sys.stderr, "%s: error: %s" % (os.path.basename(sys.argv[0]), msg)

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
  print " extract_or_updt: extract all dependencies or update if already existing"
  print " commit: commit all dependencies"
  print " rebase: rebase changes on top of upstream"
  print " deliver: push changes upstream"
  print " execute: execute command for all dependencies"
  print " dump: dumps to stdout the dependencies"
  print " dump_actual: dumps to stdout the dependencies with actual revisions"
  print " dump_head: dumps to stdout the dependencies at head revisions"
  print ""
  print "where options are:"
  print " -f|--file <dep_file> : dependency file. Default [" + config.dep_file + "]"
  print " -c|--config <configuration> : configuration to use from the dependency file. Default [" + config.configuration + "]"
  print " -q|--quiet : quiet mode"
  print " -v|--version : output this script version"
  print " -h[--help : this help page"

def main():
    pdir = os.path.dirname(sys.argv[0])
    pdir = os.path.abspath(pdir)
    def_config = DefaultConfig()
    config = Config(def_config)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-f', '--file', dest='dep_file', default=def_config.dep_file)
    parser.add_argument('-c', '--config', dest='configuration', default=def_config.configuration)
    parser.add_argument('-q', '--quiet', action='store_true')
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('-h', '--help', action='store_true')

    opts, args = parser.parse_known_args()
    if opts.help:
        usage(def_config)
        sys.exit(0)
    if opts.version:
        print "%s version %s" % (os.path.basename(sys.argv[0]), version)
        sys.exit(0)
    config.handle_options(opts, args)

    if not config.check():
        sys.exit(2)
    if len(args) == 0:
        error("missing command, try --help for usage")
    try:
        dependency = Dependency(config)
        dependency.exec_cmd(args[0], args[1:])
    except UserException, e:
        error(str(e))

if __name__ == "__main__":
  main()
