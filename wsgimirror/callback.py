from webob import Request
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage


class Callback(object):
    def __init__(self, name, parsed_conf, next_app):
        self.name = name
        self.next_app = next_app
        self.path = parsed_conf['path']
        self.callback_uri = parsed_conf['callback_uri']
        self.token_uri = parsed_conf['token_uri']
        self.auth_uri = parsed_conf['auth_uri']
        self.client_id = parsed_conf['client_id']
        self.client_secret = parsed_conf['client_secret']
        self.credspath = parsed_conf['creds_path']
        self.scope = ['https://www.googleapis.com/auth/glass.location',
                      'https://www.googleapis.com/auth/glass.timeline',
                      'https://www.googleapis.com/auth/userinfo.profile']

    def __call__(self, env, start_response):
        if env['PATH_INFO'].startswith(self.path):
            body = ['']
            flow = OAuth2WebServerFlow(client_id=self.client_id,
                                       client_secret=self.client_secret,
                                       scope=self.scope,
                                       redirect_uri=self.callback_uri,
                                       access_type='offline',
                                       approval_prompt='force')
            if env['PATH_INFO'] == '/callback/authorize':
                auth_uri = flow.step1_get_authorize_url()
                start_response('302 Redirect', [('Content-Length', 0), ('Location', auth_uri), ])
                return body
            if env['PATH_INFO'] == '/callback':
                req = Request(env)
                try:
                    code = req.GET['code']
                except KeyError:
                    start_response('400 Error', [('Content-Length', 0), ])
                    return body
                try:
                    credentials = flow.step2_exchange(code)
                    storage_file = '/'.join((self.credspath, env['brim.authenticated_user']))
                    storage = Storage(storage_file)
                    storage.put(credentials)
                    start_response('302 Redirect', [('Content-Length', 0), ('Location', '/')])
                    return body
                except Exception:
                    body = 'wtf :[\n'
                    start_response('200 OK', [('Content-Length', str(len(body)))])
                return body
            body = []
            start_response('200 OK', [('Content-Length', str(len(body)))])
            return body
        else:
            return self.next_app(env, start_response)

    @classmethod
    def parse_conf(cls, name, conf):
        return {'path': conf.get(name, 'path', '/callback'),
                'callback_uri': conf.get(name, 'callback_uri'),
                'token_uri': conf.get(name, 'token_uri'),
                'auth_uri': conf.get(name, 'auth_uri'),
                'client_id': conf.get(name, 'client_id'),
                'client_secret': conf.get(name, 'client_secret'),
                'creds_path': conf.get(name, 'creds_path')}

    @classmethod
    def stats_conf(cls, name, parsed_conf):
        return [('%s.requests' % name, 'sum')]
