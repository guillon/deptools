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
