# -*- coding: utf-8 -*-
import os
import re
import sys

import sqlalchemy as sa

from babel.messages import extract
from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo
from babel.messages.pofile import write_po


# Import our config
try:
    import config.production as config
except ImportError:
    import config.default as config

engine = sa.create_engine(config.DB_CONNECTION, echo=False)
conn = engine.connect()

DIR = os.path.dirname(os.path.realpath(__file__))


def get_translations(quiet=True):
    ''' Extract translations put in db and create mo file'''
    sql = "UPDATE translation SET active=0 WHERE lang='en';"
    engine.execute(sql)

    method_map = [
        ('**/templates/**.html', 'jinja2'),
        ('**/themes/**.html', 'jinja2'),
        ('**.py', 'python')
    ]

    if not quiet:
        print 'Extracting translations'

    extracted = extract.extract_from_dir('.', method_map=method_map)

    DIR = os.path.dirname(os.path.realpath(__file__))

    catalog = Catalog(project='hrd')

    for filename, lineno, message, comments, context in extracted:
        filepath = os.path.normpath(os.path.join(DIR, filename))
        catalog.add(
            message, None, [(filepath, lineno)],
            auto_comments=comments, context=context
        )

        if isinstance(message, tuple):
            values = message
        else:
            values = (message, '')

        sql = """
            SELECT active FROM translation
            WHERE
            lang = 'en' and id=? and plural=?;
        """

        result = conn.execute(sql, values).first()
        if result is None:
            sql = """
                INSERT INTO translation (id, plural, lang, active)
                VALUES (?, ?, 'en', 1);
            """
            conn.execute(sql, values)
        elif result[0] == 0:
            sql = """
                UPDATE translation
                SET active = 1
                WHERE
                lang = 'en' and id=? and plural=?;
            """
            conn.execute(sql, values)

    path = os.path.join(DIR, 'translations')
    try:
        os.makedirs(path)
    except OSError:
        pass

    outfile = open(os.path.join(path, 'messages.pot'), 'wb')
    try:
        if not quiet:
            print 'writing POT template file to trans'
        write_po(outfile, catalog)
    finally:
        outfile.close()


# for fake translations
t1 = u'aBCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
t2 = u'ÅßÇÐËƑĢĦĨĴĶŁϺÑÕÞƍŘŠŦÙƔŴЖÝȤåɓçđêʄǧħîĵĸƖɱñðþƣŗšŧüɤŵϰŷż'
trans_table = dict(zip([ord(char) for char in t1], t2))


def mangle(value):
    spf_reg_ex = "\+?(0|'.)?-?\d*(.\d*)?[\%bcdeufosxX]"
    extract_reg_ex = '(\%\([^\)]*\)' + spf_reg_ex + \
                     '|\[\d*\:[^\]]*\]' + \
                     '|\{[^\}]*\}' + \
                     '|<[^>}]*>' + \
                     '|\%((\d)*\$)?' + spf_reg_ex + ')'
    matches = re.finditer(extract_reg_ex, value)
    position = 0
    translation = u''
    for match in matches:
        translation += unicode(
            value[position:match.start()]
        ).translate(trans_table)
        position = match.end()
        translation += match.group(0)
    translation += unicode(value[position:]).translate(trans_table)
    return translation


def create_fake_trans(lang):
    sql = "DELETE FROM translation WHERE lang = ?"
    result = conn.execute(sql, lang)

    sql = """
        SELECT DISTINCT id, plural FROM translation
        WHERE lang = 'en' and active=1;
    """

    result = conn.execute(sql)
    values = []
    for row in result:
        values.append(
            (row.id, row.plural, lang, mangle(row.id), mangle(row.plural))
        )

    sql = """
        INSERT INTO translation (id, plural, lang, active, trans1, trans2)
        VALUES (?, ?, ?, 1, ?, ?);
    """
    for value in values:
        conn.execute(sql, value)


def create_i18n_files(lang, quiet=True):
    sql = """
        SELECT * FROM translation
        WHERE lang = ? and active=1;
    """

    result = conn.execute(sql, lang)

    catalog = Catalog(locale=lang)

    for row in result:
        if row.plural:
            key = (row.id, row.plural)
            values = [
                row.trans1,
                row.trans2,
                row.trans3,
                row.trans4,
            ]
            value = []
            for v in values:
                if v:
                    value.append(v)
            if len(value) == 1:
                value = value[0]
            else:
                value = tuple(value)

        else:
            key = row.id
            value = row.trans1
        catalog.add(key, value)

    path = os.path.join(DIR, 'translations', lang, 'LC_MESSAGES')
    try:
        os.makedirs(path)
    except OSError:
        pass

    outfile = open(os.path.join(path, 'messages.po'), 'wb')
    try:
        if not quiet:
            print 'writing PO for', lang
        write_po(outfile, catalog)
    finally:
        outfile.close()

    outfile = open(os.path.join(path, 'messages.mo'), 'wb')
    try:
        if not quiet:
            print 'writing MO for', lang
        write_mo(outfile, catalog)
    finally:
        outfile.close()


def create_all_i18n_files(quiet=True):
    locales = [lang[0] for lang in config.LANGUAGE_LIST]
    for locale in locales:
        if locale == 'en':
            continue
        create_i18n_files(locale, quiet=quiet)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        get_translations(quiet=False)
        create_all_i18n_files(quiet=False)
    else:
        if sys.argv[1] == 'mangle' and len(sys.argv) == 3:
            create_fake_trans(sys.argv[2])
