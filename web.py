import urllib
from werkzeug.serving import run_simple

from hrd import app, language_list


@app.template_filter('sn')
def reverse_filter(s):
    if s is None:
        return ''
    return s


class I18nMiddleware(object):
    """I18n Middleware selects the language based on the url
    eg /fr/home is French"""

    def __init__(self, app):
        self.app = app
        self.default_locale = 'en'
        locale_list = []
        for code, lang, _dir in language_list:
            locale_list.append(code)
        self.locale_list = locale_list

    def __call__(self, environ, start_response):
        # strip the language selector from the requested url
        # and set environ variables for the language selected
        # LANG is the language code eg en, fr
        # CURRENT_URL is set to the current application url
        if 'LANG' not in environ:
            path_parts = environ['PATH_INFO'].split('/')
            if len(path_parts) > 1 and path_parts[1] in self.locale_list:
                environ['LANG'] = path_parts[1]
                # rewrite url
                if len(path_parts) > 2:
                    environ['PATH_INFO'] = '/'.join([''] + path_parts[2:])
                else:
                    environ['PATH_INFO'] = '/'
            else:
                environ['LANG'] = self.default_locale
            # Current application url
            path_info = environ['PATH_INFO']
            # sort out weird encodings
            path_info = '/'.join(urllib.quote(pce, '')
                                 for pce in path_info.split('/'))
            qs = environ.get('QUERY_STRING')
            if qs:
                # sort out weird encodings
                # qs = urllib.quote(qs, '')
                environ['CURRENT_URL'] = '%s?%s' % (path_info, qs)
            else:
                environ['CURRENT_URL'] = path_info
        return self.app(environ, start_response)


app = I18nMiddleware(app)
if __name__ == '__main__':
    run_simple('localhost', 5000, app, use_reloader=True)
