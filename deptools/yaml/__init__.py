# Simple wrapper around Python 2.x/3.x library versions
import sys

if sys.version_info[0] == 2:
    from yaml2 import *
    __version__ = yaml2.__version__
else:
    from .yaml3 import *
    __version__ = yaml3.__version__
