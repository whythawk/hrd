# -*- coding: utf-8 -*-


# SECRET_KEY should be randomly generated
SECRET_KEY = "SecretKeyForSessionSigning"

DB_CONNECTION = 'sqlite:///db.sqlite'

# relative to application
UPLOAD_FOLDER = 'files'

PERMISSIONS = [
    ('sys_admin', 'System administrator'),
    ('content_manage', 'Content managment'),
    ('translator', 'Content translation'),
    ('user_admin', 'User administrator'),
    ('user_manage', 'User management'),
]

DEBUG = True

# code, local language name, direction, active
LANGUAGE_LIST = [
    ('en', u'English', 'ltr', True),
    ('fr', u'français', 'ltr', True),
    ('es', u'español', 'ltr', True),
    ('ar', u'العربية', 'rtl', True),
    # ('zh', u'中文', 'ltr', False),
    ('ru', u'русский', 'ltr', True),
]
