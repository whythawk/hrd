# -*- coding: utf-8 -*-


# SECRET_KEY should be randomly generated
SECRET_KEY = "SecretKeyForSessionSigning"

DB_CONNECTION = 'postgresql://hrd:pass@localhost/hrd'
GA_ENABLED = False
EMAIL = 'admin@example.com'
EMAIL_ENABLED = False

# relative to application
UPLOAD_FOLDER = 'files'

PERMISSIONS = [
    ('sys_admin', 'System administrator'),
    ('content_manage', 'Content managment'),
  #  ('translator', 'Content translation'),
  #  ('user_admin', 'User administrator'),
  #  ('user_manage', 'User management'),
]

ALLOWED_IMAGE_TYPES = ['.gif', '.png', '.jpeg', '.jpg']

DISALLOWED_URLS = [
    '/forum',
    '/admin',
    '/user',
    '/resources',
    '/organisations',
]

ORG_PER_PAGE = 10

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
