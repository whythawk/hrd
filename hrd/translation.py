# -*- coding: utf-8 -*-
import uuid
import os
import re
import sys

from sqlalchemy.sql import text
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

engine = sa.create_engine(config.DB_CONNECTION)
conn = engine.connect()

DIR = os.path.dirname(os.path.realpath(__file__))


def get_translations(quiet=True):
    ''' Extract translations put in db and create mo file'''
    sql = "UPDATE translation SET active='0' WHERE lang='en';"
    engine.execute(sql)

    method_map = [
        ('**/templates/**.html', 'jinja2'),
        ('**.py', 'python')
    ]
    options_map = {
        '**/themes/hrd/**.html': {'extensions':'jinja2.ext.autoescape'}
    }

    if not quiet:
        print 'Extracting translations'

    extracted = extract.extract_from_dir('.', method_map=method_map,options_map = options_map)

    DIR = os.path.dirname(os.path.realpath(__file__))

    catalog = Catalog(project='hrd')

    sql = """
        SELECT max(id) FROM translation;
    """

    result = conn.execute(sql).first()

    max_id = result[0]
    if not max_id:
        max_id = 0

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
            lang = 'en' and "string" = %s and plural = %s;
        """

        result = conn.execute(sql, values).first()
        if result is None:
            sql = """
                INSERT INTO translation (id, string, plural, lang, active)
                VALUES (%s, %s, %s, 'en', '1');
            """
            max_id += 1
            conn.execute(sql, (max_id,) + values)
        elif result[0] == 0:
            sql = """
                UPDATE translation
                SET active = '1'
                WHERE
                lang = 'en' and string=%s and plural=%s;
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
    sql = "DELETE FROM translation WHERE lang = %s"
    result = conn.execute(sql, lang)

    sql = """
        SELECT max(id) FROM translation;
    """

    result = conn.execute(sql).first()

    max_id = result[0]
    if not max_id:
        max_id = 0

    sql = """
        SELECT DISTINCT string, plural FROM translation
        WHERE lang = 'en' and active='1';
    """

    result = conn.execute(sql)
    values = []
    for row in result:
        max_id += 1
        values.append(
            (max_id, row.string, row.plural, lang, mangle(row.string), mangle(row.plural))
        )

    sql = """
        INSERT INTO translation (id, string, plural, lang, active, trans0, trans1)
        VALUES (%s, %s, %s, %s, '1', %s, %s);
    """
    for value in values:
        conn.execute(sql, value)


def create_i18n_files(lang, quiet=True):
    sql = """
        SELECT * FROM translation
        WHERE lang = %s and active='1';
    """

    result = conn.execute(sql, lang)

    catalog = Catalog(locale=lang)

    for row in result:
        if row.plural:
            key = (row.string, row.plural)
            values = [
                row.trans0,
                row.trans1,
                row.trans2,
                row.trans3,
                row.trans4,
                row.trans5,
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
            key = row.string
            value = row.trans0
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

def update_categories_countries():
    sql = """
        CREATE TABLE IF NOT EXISTS cat_translations (
            id1 character varying(50),
            id2 character varying(50)
        )
    """

    result = conn.execute(sql)

    countries_id = '27c406c7-951f-482d-bbd8-3229c7f9c74b'
    relocation_id = 'bc99b20d-be07-4379-93a6-b2fcd7cdb3db'

    sql = text("DELETE FROM code WHERE category_id = :id")
    result = conn.execute(sql, id=relocation_id)

    sql = text("SELECT * FROM code WHERE category_id = :id")
    result = conn.execute(sql, id=countries_id)

    for row in result:
        print row['title']

        sql = text("SELECT id2 FROM cat_translations WHERE id1 = :id")
        ct = conn.execute(sql, id=row['code_id'])
        new_id = None
        for ct_row in ct:
            new_id = ct_row['id2']
        if not new_id:
            new_id = str(uuid.uuid4())
            sql = text("INSERT INTO cat_translations (id1, id2) VALUES (:id1, :id2)")
            ct = conn.execute(sql, id1=row['code_id'], id2=new_id)
        sql = text("""
            INSERT INTO code (
                id, code_id, category_id, title, description, lang, status, current, active, public, "order"
            ) VALUES (
                :id, :code_id, :category_id, :title, :description, :lang, :status, :current, :active, :public, :order
            )""")
        ct = conn.execute(
            sql,
            id=str(uuid.uuid4()),
            code_id=new_id,
            category_id=relocation_id,
            title=row['title'],
            description=row['description'],
            lang=row['lang'],
            status=row['status'],
            current=row['current'],
            active=row['active'],
            public=row['public'],
            order=row['order']
         )



def create_all_i18n_files(quiet=True):
    locales = [lang[0] for lang in config.LANGUAGE_LIST]
    for locale in locales:
        if locale == 'en':
            continue
        create_i18n_files(locale, quiet=quiet)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        create_all_i18n_files(quiet=False)
    else:
        if sys.argv[1] == 'extract' and len(sys.argv) == 2:
            get_translations(quiet=False)
        if sys.argv[1] == 'mangle' and len(sys.argv) == 3:
            create_fake_trans(sys.argv[2])
        if sys.argv[1] == 'category_fix' and len(sys.argv) == 2:
            update_categories_countries()
