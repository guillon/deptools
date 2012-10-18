#
# Copyright (C) STMicroelectronics Ltd. 2012
#
# Licensed under the MIT licence: 
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

import os
import sys
import hashlib
import tempfile

class digester:
    """
    Digester class.
    """
    def __init__(self, **kwargs):
        args = { 'block_size': 8192,
                 'stdout': sys.stdout,
                 'stderr': sys.stderr,
                 'digest_content': False,
                 'ignore_errors': False
                 }
        for key, value in kwargs.items():
            if key not in args:
                raise Exception("unexpeted kwargs key: %s" % key)
            args[key] = value
        self.block_size_ = args['block_size']
        self.output_ = args['stdout']
        self.stderr_ = args['stderr']
        self.digest_content_ = args['digest_content']
        self.ignore_errors_ = args['ignore_errors']

    def digest_file_content_(self, infile):
        if self.block_size_ == 0:
            return hashlib.sha1(infile.read()).hexdigest()
        else:
            digest = hashlib.sha1()
            while True:
                s = infile.read(self.block_size_)
                if not s: break
                digest.update(s)
            return digest.hexdigest()

    def digest_file_(self, path):
        try:
            if self.digest_content_:
                with open(path) as f:
                    print >>self.output_, "F %s %s" % (self.digest_file_content_(f), path)
            else:
                print >>self.output_, "F %d %s" % (os.path.getsize(path), path)
        except IOError, e:
            e.filename = path
            return self.report_exc_(e, "can't read file")
        except OSError, e:
            e.filename = path
            return self.report_exc_(e, "can't access file")
        return 0

    def digest_link_(self, path):
        try:
            link = os.readlink(path)
            if self.digest_content_:
                print >>self.output_, "L %s %s" % (hashlib.sha1(link).hexdigest(), path)
            else:
                print >>self.output_, "L %d %s" % (len(link), path)
        except OSError, e:
            e.filename = path
            return self.report_exc_(e, "can't open link")
        return 0

    def digest_special_(self, path):
        if self.digest_content_:
            print >>self.output_, "S %s %s" % (hashlib.sha1("").hexdigest(), path)
        else:
            print >>self.output_, "S %s" % path
        return 0

    def error_(self, msg):
        print >>self.stderr_, "%s: %s" % (os.path.basename(sys.argv[0]), msg)
        return 1

    def report_error_(self, msg):
        if not self.ignore_errors_:
            self.error_(msg)
        return 1

    def report_exc_(self, exc, msg):
        return self.report_error_("%s: %s: %s" % (msg, exc.strerror, exc.filename))

    def digest_not_dir_(self, path):
        # Must check link first,
        # a link can be reported as a file in some cases
        if os.path.islink(path):
            retcode = self.digest_link_(path)
        elif os.path.isfile(path):
            retcode = self.digest_file_(path)
        else:
            retcode = self.digest_special_(path)
        return retcode

    def digest_dir_(self, root):
        self.retcode_ = 0
        def report_error(exc):
            self.report_exc_(exc, "can't access path")
            self.retcode_ = 1

        for dirname, dirnames, filenames in os.walk(root, onerror=report_error):
            for filename in sorted(filenames):
                path = os.path.join(dirname, filename)
                if self.digest_not_dir_(path) != 0:
                    self.retcode_ = 1
            for subdirname in sorted(dirnames):
                path = os.path.join(dirname, subdirname)
                if os.path.islink(path):
                    if self.digest_link_(path) != 0:
                        self.retcode_ = 1
        return self.retcode_

    def digest_list(self, paths):
        if not isinstance(paths, list):
            paths = [paths]
        sorted_paths = sorted(paths)
        for path in sorted_paths:
            if not os.path.exists(path):
                return self.error_("path does not exist: %s" % path)
        retcode = 0
        for path in sorted_paths:
            if os.path.isdir(path) and not os.path.islink(path):
                if self.digest_dir_(path) != 0:
                    retcode = 1
            else:
                if self.digest_not_dir_(path) != 0:
                    retcode = 1
        return 0 if self.ignore_errors_ else retcode

    def digest_paths(self, paths):
        list_file = tempfile.TemporaryFile()
        retcode = digester(block_size = self.block_size_,
                           ignore_errors = self.ignore_errors_,
                           digest_content = self.digest_content_,
                           stdout = list_file,
                           stderr = self.stderr_).digest_list(paths)
        if retcode != 0 and not self.ignore_errors_:
            self.report_error_("error when computing digest list, the final digest will be inaccurate")
        list_file.seek(0)
        return self.digest_file_content_(list_file)
