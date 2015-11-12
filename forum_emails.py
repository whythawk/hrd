# -*- coding: utf-8 -*-
import uuid
import os
import re
import sys
from datetime import date, datetime

from sqlalchemy.sql import text
import sqlalchemy as sa

import gettext

from hrd import hrd_email, config


engine = sa.create_engine(config.DB_CONNECTION)
conn = engine.connect()


def get_digest_users():
    sql = '''
    SELECT id, prefered_lang, username, realname, email
    FROM users
    WHERE
    forum_digest = true
    AND ga_enabled = true
    AND ga_key is not NULL
    '''
    result = engine.execute(sql)
    return result


def get_posts(user_id, post_date, lang, email):
    conn = engine.connect()
    print 'USER', user_id, lang
    # new posts
    sql = text('''
    SELECT DISTINCT p.topic_id
    FROM posts AS p
    LEFT OUTER JOIN topicsread AS tr
    ON p.topic_id = tr.topic_id
      AND tr.user_id = :user_id
    WHERE p.date_created > :date
    AND (tr.last_read < p.date_created OR tr.last_read IS NULL)
    AND p.topic_id NOT IN (

    SELECT t.id
    FROM topics AS t
    LEFT OUTER JOIN forumsread AS fr
    ON fr.forum_id = t.forum_id
        AND fr.user_id = :user_id
    WHERE t.date_created > :date
    AND (fr.last_read < t.date_created OR fr.last_read IS NULL)

    )
    ''')
    result = conn.execute(sql, date=post_date, user_id=user_id)
    replies = []
    for row in result:
        replies.append(row[0])
    print 'replies:', replies
    # new topics

    sql = text('''
    SELECT t.id
    FROM topics AS t
    LEFT OUTER JOIN forumsread AS fr
    ON fr.forum_id = t.forum_id
        AND fr.user_id = :user_id
    WHERE t.date_created > :date
    AND (fr.last_read < t.date_created OR fr.last_read IS NULL)
    ''')
    result = conn.execute(sql, date=post_date, user_id=user_id)
    new_posts = []
    for row in result:
        new_posts.append(row[0])
    print 'new_posts:', new_posts
    create_email(new_posts, replies, lang, email)


def create_email(new_posts, replies, lang, email):
    # select message catalog
    lang = 'fr'
    f = './hrd/translations/%s/LC_MESSAGES/messages.mo' % lang
    try:
        trans = gettext.GNUTranslations(open(f))
        _ = trans.gettext
    except:
        _ = gettext.gettext

    if not (new_posts or replies):
        return
    info = get_topic_details(new_posts + replies)
    body = []
    if new_posts:
        body.append('')
        body.append(_('The following posts have been added in the HRD forum'))
        body.append('')
        for post in new_posts:
            body.append(info[post])
            body.append('%s/forum/topic/%s\n' % (config.SITE_URL, post))
    if replies:
        body.append('')
        body.append(_('New following posts have had replies'))
        body.append('')
        for post in new_posts:
            body.append(info[post])
            body.append('%s/forum/topic/%s\n' % (config.SITE_URL, post))
    body.append('-' * 78)
    body.append(_('You have recieved this as you are a member of the EU Human Rights Defenders Relocation Platform.  To unsubscribe please log in and uncheck the forum digest checkbox in your profile.'))
    msg = '\n'.join(body)
    subject = _('HRD daily digest')
    sender = config.EMAIL
    hrd_email.send_email(email, subject=subject, content=msg, sender=sender)

def get_topic_details(ids):
    results = {}
    if ids:
        sql = text('''
        SELECT id, title
        FROM topics
        WHERE id IN :posts
        ''')
        result = engine.execute(sql, posts=tuple(ids))
        for row in result:
            results[row[0]] = row[1]
    return results


if __name__ == '__main__':



    post_date = date.fromordinal(date.today().toordinal() - 1)

    post_date = datetime(post_date.year, post_date.month, post_date.day, 12)
    print 'DIGEST for %s' %  post_date
    if config.FORUM_DIGEST is False:
        print 'digest disabled'
        exit()
    users = get_digest_users()
    for user in users:
        if config.FORUM_DIGEST_LIMITED and user[0] not in config.FORUM_DIGEST_LIMIT_LIST:
            continue
        lang = user[1] or 'en'
        email = user[2]
        get_posts(user[0], post_date, lang, email)
