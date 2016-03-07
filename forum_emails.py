# -*- coding: utf-8 -*-
import uuid
import os
import re
import sys
from datetime import date, datetime

from sqlalchemy.sql import text
import sqlalchemy as sa

import gettext

import hrd.hrd_email as hrd_email
import hrd.config as config


engine = sa.create_engine(config.DB_CONNECTION)


def get_digest_users():
    sql = '''
    SELECT id, prefered_lang, username, realname, email
    FROM users
    WHERE
    forum_digest = true
    '''
    if config.GA_ENABLED:
        sql += '''
        AND ga_key is not NULL
        '''
    conn = engine.connect()
    result = conn.execute(sql)
    conn.close()
    return result


def get_posts(user_id, post_date, lang, email):
    conn = engine.connect()
    # new posts
    sql = text('''
    SELECT DISTINCT p.topic_id
    FROM posts AS p
    LEFT OUTER JOIN topicsread AS tr
    ON p.topic_id = tr.topic_id
      AND tr.user_id = :user_id
    WHERE p.date_created > :date
    AND (tr.last_read < p.date_created OR tr.last_read IS NULL)
    AND p.topic_id IN (
     SELECT topic_id FROM topictracker WHERE user_id = :user_id
    )
    ''')
    result = conn.execute(sql, date=post_date, user_id=user_id)
    replies = []
    for row in result:
        replies.append(row[0])
    # new topics

    sql = text('''
    SELECT t.id
    FROM topics AS t
    LEFT OUTER JOIN forumsread AS fr
    ON fr.forum_id = t.forum_id
        AND fr.user_id = :user_id
    LEFT OUTER JOIN topicsread AS tr
    ON t.id = tr.topic_id
      AND tr.user_id = :user_id
    WHERE t.date_created > :date
    AND (tr.last_read < t.date_created OR tr.last_read IS NULL)
    AND (fr.last_read < t.date_created OR fr.last_read IS NULL)
    ''')
    result = conn.execute(sql, date=post_date, user_id=user_id)
    new_posts = []
    for row in result:
        new_posts.append(row[0])

    if new_posts or replies:
        print 'USER', user_id, lang, email
        print 'new_posts:', new_posts
        print 'replies:', replies
    create_email(new_posts, replies, lang, email)
    conn.close()


def create_email(new_posts, replies, lang, email):
    # select message catalog
    lang = 'fr'
    f = './hrd/translations/%s/LC_MESSAGES/messages.mo' % lang
    try:
        trans = gettext.GNUTranslations(open(f))
        _ = trans.gettext
    except:
        _ = gettext.gettext

    if not (new_posts + replies):
        return
    info = get_topic_details(new_posts + replies)
    body = []
    if new_posts:
        body.append('')
        body.append(_('A new topic has been created.'))
        body.append('')
        for post in new_posts:
            body.append(info[post])
            body.append('%s/forum/topic/%s\n' % (config.SITE_URL, post))
    if replies:
        body.append('')
        body.append(_('The following topics you are tracking have had replies.'))
        body.append('')
        for post in replies:
            body.append(info[post])
            body.append('%s/forum/topic/%s\n' % (config.SITE_URL, post))
    body.append('-' * 78)
    body.append(_('You have received this as you are a member of the EU Human Rights Defenders Relocation Platform.  To unsubscribe please log in and uncheck the forum digest checkbox in your profile.'))
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
        conn = engine.connect()
        result = conn.execute(sql, posts=tuple(ids))
        conn.close()
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
        email = user[4]
        get_posts(user[0], post_date, lang, email)
