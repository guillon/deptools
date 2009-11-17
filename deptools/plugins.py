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
# Simple base class for plugins implementation
# Ref to http://martyalchin.com/2008/jan/10/simple-plugin-framework/
#
__all__ = ['PluginMount', 'PluginLoader', 'SourceManager']

import os, sys

verbose = 0

class PluginMount(type):
    def __init__(cls, name, bases, attrs):
        cls.plugin_map = {}
        if not hasattr(cls, 'plugins'):
            # This branch only executes when processing the mount point itself.
            # So, since this is a new plugin type, not an implementation, this
            # class shouldn't be registered as a plugin. Instead, it sets up a
            # list where plugins can be registered later.
            cls.plugins = []
        else:
            # This must be a plugin implementation, which should be registered.
            # Simply appending it to the list is all that's needed to keep
            # track of it later.
            cls.plugins.append(cls)
            

    def get_plugin(cls, name):
        try:
            p = cls.plugin_map[name]
        except KeyError:
            for p in cls.plugins:
                if p.name == name:
                    cls.plugin_map[name] = p
                    return p
        return p
    

class PluginLoader:
    """ PluginLoader is a static class that loads all the availble
    plugins from the plugins directory
    """
    def __init__(self):
        pdir = os.path.dirname(sys.argv[0])
        pluginpath = os.path.join(pdir, "plugins")
        try: # might not be a filesystem path
            files = os.listdir(pluginpath)
            sys.path.insert(0,pluginpath)
        except OSError:
            files = []
        for file in files:
            if file.endswith('.py'):
                name = file.rsplit('.', 1)[0]
                if verbose != 0:
                    print "Loading plugin " + name
                __import__(name)


class SourceManager:
    """ SourceManager plugins must derive from this class.
    Methods that must be implemented by SourceManager plugins are:
    clone, update, commit, rebase, deliver.
    Attributes are:
    name, description.
    """
    __metaclass__ = PluginMount


loader = PluginLoader()
