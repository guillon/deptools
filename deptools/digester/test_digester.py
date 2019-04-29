#!/usr/bin/env python

#
# Test digester in different modes
#

from __future__ import print_function

import os
import sys

from digester import digester

def error(msg):
    print(sys.argv[0] + ": error: " + msg, file=sys.stderr)
    sys.exit(1)


print("path, text only, no content: ", end="")
dig = digester(digest_content=False)
res = dig.digest_paths("test_digester_input_text_only")
print(res)
expected = "353382aca12f64fe4eec137d96ac3b6cc540b161"
if res != expected:
    error("Invalid digester result, expecting " +  expected)

print("path, text only, content   : ", end="")
dig = digester(digest_content=True)
res = dig.digest_paths("test_digester_input_text_only")
print(res)
expected = "cf1756d1e1946251099bf324d005e09256a36332"
if res != expected:
    error("Invalid digester result, expecting " +  expected)

print("path, text+bin,  no content: ", end="")
dig = digester(digest_content=False)
res = dig.digest_paths("test_digester_input_text_and_bin")
print(res)
expected = "adca8a1a378db03fd850bf49cdd24e290581c3c4"
if res != expected:
    error("Invalid digester result, expecting " +  expected)

print("path, text+bin,  content   : ", end="")
dig = digester(digest_content=True)
res = dig.digest_paths("test_digester_input_text_and_bin")
print(res)
expected = "cf82b44ff987ce090e6315ff518f142adbbd7198"
if res != expected:
    error("Invalid digester result, expecting " +  expected)
