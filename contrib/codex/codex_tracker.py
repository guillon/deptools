#!/usr/bin/env python

import sys, os, getpass, json, urllib, datetime, warnings

# lib request install dir
python_lib_dir = '/sw/st/gnu_compil/comp/scripts/python-requests'
sys.path.insert(0, python_lib_dir)

import requests


# ####################################################################
#
#
#


def _check_auth_header(auth_header):
    status, content = codex_request(
        'GET', 'projects', headers=auth_header, authenticate=False)
    assert status == 200


def _get_auth_header(username, password):
    data = {
        'username': username, 'password': password}
    status, content = codex_request(
        'POST', 'tokens', data=data, authenticate=False)
    auth_header = {
        'X-Auth-Token': str(content['token']),
        'X-Auth-UserId': str(content['user_id'])}
    return auth_header


def _codex_auth_header(username):

    home_dir = os.getenv('HOME', '')
    token_file = os.path.join(home_dir, '.codex_token')
    password_file = os.path.join(home_dir, '.codex_passwd')

    while True:
        try: # try with existing codex token file
            auth_header = json.load(open(token_file))
            _check_auth_header(auth_header)
            break
        except: pass

        try: # try with codex password file
            password = open(password_file).read().strip()
            auth_header = _get_auth_header(username, password)
            _check_auth_header(auth_header)
            json.dump(auth_header, open(token_file, 'w'))
            os.chmod(token_file, 0600)
            break
        except: pass

        try: # try requesting password
            password = getpass.getpass(
                'password for %s: ' % username)
            auth_header = _get_auth_header(username, password)
            _check_auth_header(auth_header)
            json.dump(auth_header, open(token_file, 'w'))
            os.chmod(token_file, 0600)
            open(password_file, 'w').write(password)
            os.chmod(password_file, 0600)
            break
        except: raise

    return auth_header


def codex_request(
    reqty, url, params=None, data=None, headers=None,
    username=None, authenticate=True):

    #
    request_funcs = {
        'GET': requests.get, 'POST': requests.post, 'DELETE': requests.delete,
        'PUT': requests.put }
    assert reqty in request_funcs
    request_func = request_funcs[reqty]

    #
    codex_url = 'https://codex.cro.st.com'
    request_url = codex_url + '/api/v1/' + url

    #
    params = params or {}
    params_limit = int(params.get('limit', 0))

    datastr = data and json.dumps(data)

    headers = headers or {'content-type': 'application/json'}

    username = username or os.getenv('USER')
    authenticate and headers.update(_codex_auth_header(username))

    #
    full_response_content = []
    while True:
        # ignore python request InsecureRequestWarning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = request_func(
                request_url, params=params, data=datastr, headers=headers,
                verify=False)

        #
        if not response.content:
            break
        response_content = json.loads(response.content)
        if not isinstance(response_content, list):
            assert not params_limit
            full_response_content = response_content
            break

        # if a limit is given, loop to get full response if needed
        full_response_content.extend(response_content)
        if not params_limit or len(response_content) != params_limit:
            break
        params.update({'offset': params.get('offset', 0) + params_limit})

    return response.status_code, full_response_content




