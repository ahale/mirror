import httplib2
from pprint import pformat as pp
from jinja2 import Environment, FileSystemLoader
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError


class App(object):
    def __init__(self, name, parsed_conf, next_app):
        self.name = name
        self.next_app = next_app
        self.path = parsed_conf['path']
        self.credspath = parsed_conf['creds_path']
        self.jinjaenv = Environment(loader=FileSystemLoader(parsed_conf['template_path']))

    def __call__(self, env, start_response):
        if env['PATH_INFO'].startswith(self.path):
            storage_file = '%s/%s' % (self.credspath, env['brim.authenticated_user'])
            storage = Storage(storage_file)
            credentials = storage.get()
            if not credentials:
                start_response('302 Redirect', [('Content-Length', 0), ('Location', '/')])
                return []
            env['credentials'] = credentials
            try:
                env['timeline'] = self._get_timeline_items(env)
            except AccessTokenRefreshError:
                env['timeline'] = [{'id': 'token refresh error'}, ]
            if env['PATH_INFO'] == self.path:
                return self._handle_listing(env, start_response)
            try:
                card_id = env['PATH_INFO'].split('/')[2]
                if card_id in [item['id'] for item in env['timeline']]:
                    return self._handle_card(env, start_response, card_id)
            except IndexError:
                pass
            start_response('302 Redirect', [('Content-Length', 0), ('Location', self.path)])
            return []
        return self.next_app(env, start_response)

    def _get_timeline_items(self, env):
        http = httplib2.Http()
        http = env['credentials'].authorize(http)
        service = build('mirror', 'v1', http=http)
        req = service.timeline().list()
        resp = req.execute()
        return resp['items']

    def _handle_listing(self, env, start_response):
        num_items = len(env['timeline'])
        template = self.jinjaenv.get_template('timeline.html')
        body = template.render(username=env['brim.authenticated_user'],
                               num_items=num_items,
                               timeline=env['timeline'])
        start_response('200 OK', [('Content-Length', str(len(body)))])
        return body

    def _handle_card(self, env, start_response, card_id):
        for card in env['timeline']:
            if card['id'] == card_id:
                break
        pp_card = pp(card)
        template = self.jinjaenv.get_template('card_info.html')
        body = template.render(username=env['brim.authenticated_user'],
                               card_content=pp_card,
                               card_id=card_id)
        start_response('200 OK', [('Content-Length', str(len(body)))])
        return body

    @classmethod
    def parse_conf(cls, name, conf):
        return {'path': conf.get(name, 'path', '/timeline'),
                'template_path': conf.get(name, 'template_path'),
                'creds_path': conf.get(name, 'creds_path')}

    @classmethod
    def stats_conf(cls, name, parsed_conf):
        return [('%s.requests' % name, 'sum')]
