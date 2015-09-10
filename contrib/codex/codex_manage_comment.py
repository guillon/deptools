#!/usr/bin/env python

#
# get/update codex artifact comments
#
# usage:
# codex_manage_comment.py CODEX_ARTIFACT_ID
#   -> get follow-up comments from a codex artifact
# codex_manage_comment.py CODEX_ARTIFACT_ID COMMENT
#   -> add a new comment to a codex artifact
#

import sys, os
import unicodedata

from codex_tracker import codex_request


if not len(sys.argv) >= 2:
    print >>sys.stderr, 'usage:', os.path.basename(sys.argv[0]),
    print >>sys.stderr, 'ARTIFACT_ID [comment]'
    sys.exit(1)

artifact_id = int(sys.argv[1])
comment = ' '.join(sys.argv[2:])

if comment:
    # update artifact with a new follow-up comment
    data = { 'values': [], 'comment': {'body' : comment, 'format' : 'text'} }
    status, content = codex_request(
        'PUT', 'artifacts/%d' % artifact_id, data=data)
    assert status == 200

else:
    # list comments attached to artifact
    params = {'values': 'all', 'limit': '10'}
    status, content = codex_request(
        'GET', 'artifacts/%d/changesets' % artifact_id, params=params)
    assert status == 200

    comments = map(
        lambda cs: (
            cs.get('submitted_on', ''),
            cs.get('last_comment', {}).get('body', '')),
        content)

    for (comment_date, comment_text) in comments:
        print '#', comment_date
        print unicodedata.normalize(
            'NFKD', comment_text).encode('ascii','ignore')
        print
