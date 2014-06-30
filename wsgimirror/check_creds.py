from oauth2client.file import Storage
from jinja2 import Environment, FileSystemLoader


class Index(object):
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
            if credentials:
                start_response('302 Redirect', [('Content-Length', 0), ('Location', '/timeline')])
                return ['']
            template = self.jinjaenv.get_template('index.html')
            body = template.render(username=env['brim.authenticated_user'])
            start_response('200 OK', [('Content-Length', str(len(body)))])
            return body
        else:
            return self.next_app(env, start_response)

    @classmethod
    def parse_conf(cls, name, conf):
        return {'path': conf.get(name, 'path', '/'),
                'template_path': conf.get(name, 'template_path'),
                'creds_path': conf.get(name, 'creds_path')}

    @classmethod
    def stats_conf(cls, name, parsed_conf):
        return [('%s.requests' % name, 'sum')]
