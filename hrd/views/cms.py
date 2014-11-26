import uuid
import os.path

from flask import (render_template, request, abort, redirect,
                   send_from_directory)
from flask import _request_ctx_stack

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool, config,
                 permission, permission_content, get_str, lang_codes)
from hrd.models import Cms


@app.route('/admin')
def admin():
    return render_template('index.html')


@app.route('/admin/cms_logo/<type>/<id>')
def cms_logo(type, id):
    if type == 'live':
        page = Cms.query.filter_by(
            page_id=id, lang='en', status='publish'
        ).first()
    else:
        page = Cms.query.filter_by(page_id=id, lang='en', current=True).first()
    return send_from_directory(app.config['UPLOAD_FOLDER'], page.image)


@app.route('/admin/cms_edit/<id>', methods=['GET', 'POST'])
def cms_edit(id):
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    errors = []
    page = Cms.query.filter_by(page_id=id, lang=lang, current=True)
    page = page.first()
    if not page and lang != 'en':
        page = Cms.query.filter_by(page_id=id, lang='en', current=True)
        page = page.first()
        if not page:
            abort(404)
    if not page:
        abort(404)
    if request.method == 'POST' and 'title' in request.form:
        if page.lang != lang:
            # no translation
            page = page_reedit(page)

        if (page.title != get_str('title')
                or page.content != get_str('content')):
            if page.status == 'publish':
                page = page_reedit(page)

            page.title = get_str('title')
            page.content = get_str('content')
            page.status = 'edit'
            trans_need_update(page)
        if lang == 'en':
            page.active = get_bool('active')
            page.private = get_bool('private')

            url = get_str('url')
            if url:
                check = Cms.query.filter(Cms.page_id != id, Cms.url == url)
                check = check.filter(db.or_(
                    Cms.status == 'publish', Cms.current == True
                ))
                if check.count():
                    errors.append(
                        'The url is already used by another page choose ' + \
                        'a new url or change the url of the existing page ' + \
                        'first. The url has been reset in this form.'
                    )
                elif url in config.DISALLOWED_URLS:
                    errors.append(
                        'The url provided is not allowed please choose ' + \
                        'a new one. The url has been reset in this form.'
                    )
                else:
                    page.url = url

            if get_bool('logo_remove'):
                page.image = None

            logo = request.files['logo']
            if logo:
                extension = os.path.splitext(logo.filename)[1]
                if extension and extension.lower() in config.ALLOWED_IMAGE_TYPES:
                    filename = unicode(uuid.uuid4())
                    filename += extension
                    logo.save(
                        os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    )
                    page.image = filename
                else:
                    errors.append(
                        'The image uploaded is not of an allowed type'
                    )

        db.session.add(page)
        db.session.commit()
        if lang == 'en':
            update_translations(page)
        if not errors:
            return redirect(url_for_admin('cms_preview', id=id))
    if lang != 'en':
        trans = Cms.query.filter_by(page_id=id, lang='en',
                                    current=True).first()
    else:
        trans = {}
    if lang != page.lang:
        page = {}
    translations = get_trans(id)
    return render_template('admin/cms_edit.html', page=page, trans=trans,
                           translations=translations, errors=errors)


def trans_need_update(page):
    # FIXME trigger updates needed for trans
    pass


def page_reedit(page):
    lang = get_admin_lang()
    new_page = Cms(
        lang=lang,
        page_id=page.page_id,
        content=page.content,
        title=page.title,
        url=page.url,
        active=page.active,
        private=page.private,
        image=page.image,
        status='edit',
        current=True,
        published=True
    )
    db.session.add(new_page)
    page.current = False
    db.session.add(page)
    db.session.commit()
    return new_page


@app.route('/admin/cms_delete/<id>', methods=['POST'])
def cms_delete(id):
    permission('content_manage')
    Cms.query.filter_by(page_id=id).delete()
    db.session.commit()
    return redirect(url_for_admin('cms_list'))


@app.route('/admin/cms_new/', methods=['POST'])
def cms_new():
    permission('content_manage')
    lang = 'en'
    page = Cms(lang=lang)
    page.status = 'edit'
    db.session.add(page)
    db.session.commit()
    return redirect(url_for_admin('cms_edit', id=page.page_id))


STATES = {
    'approve': 'edit',
    'approved': 'approve',
    'publish': 'approved',
}


@app.route('/admin/cms_state/<id>/<state>', methods=['POST'])
def cms_state(id, state):
    lang = get_admin_lang()
    permission_content(lang)
    if state not in STATES:
        abort(403)
    page = Cms.query.filter_by(page_id=id, status=STATES[state], lang=lang,
                               current=True).first()
    if not page:
        abort(403)
    if state == 'publish':
        page.published = True
        old_page = Cms.query.filter_by(page_id=id, status='publish',
                                       lang=lang).first()
        if old_page:
            old_page.status = 'archive'
            db.session.add(old_page)
    page.status = state
    db.session.add(page)
    db.session.commit()
    return redirect(url_for_admin('cms_preview', id=id))


def update_translations(page):
    trans = Cms.query.filter_by(page_id=page.page_id)
    trans = trans.filter(db.not_(Cms.id == page.id))
    trans = trans.filter(db.or_(
        Cms.status == 'publish', Cms.current == True
    ))

    for tran in trans:
        tran.active = page.active
        tran.private = page.private
        tran.url = page.url
        tran.image = page.image
        db.session.add(tran)
    db.session.commit()


@app.route('/page/<id>')
def cms_page(id):
    return show_page(page_id=id)


@app.route('/<id>')
@app.route('/')
def cms_page2(id=''):
    id = '/%s' % id
    return show_page(url=id)


def show_page(**kw):
    lang = get_admin_lang()
    lang = request.environ['LANG']
    page = Cms.query.filter_by(
        lang=lang, status='publish', active=True, **kw
    ).first()
    if not page:
        page = Cms.query.filter_by(
            lang='en', status='publish', active=True, **kw
        ).first()
        if not page:
            abort(404)

    # only show public page
    if not bool(request.user) and page.private:
        abort(403)

    return render_template('page.html', page=page)


@app.route('/admin/cms_preview/<id>')
def cms_preview(id):
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    page = Cms.query.filter_by(page_id=id, lang=lang, current=True).first()
    if not page:
        page = Cms.query.filter_by(page_id=id, lang='en', current=True).first()
        if not page:
            abort(404)
        page = None
    translations = get_trans(id)
    ctx = _request_ctx_stack.top
    if ctx:
        ctx.babel_locale = lang
    return render_template('admin/cms_preview.html',
                           page=page,
                           translations=translations)


@app.route('/admin/cms')
def cms_list():
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    pages = Cms.query.filter_by(lang=lang, current=True)
    pages = pages.order_by('title')
    for page in pages:
        p = Cms.query.filter_by(page_id=page.page_id, lang=lang,
                                status='publish').first()
        page.has_published = bool(p)
    if lang == 'en':
        missing = []
        trans = {}
    else:
        # missing pages
        trans = db.session.query(Cms.page_id).filter_by(lang=lang)
        missing = db.session.query(Cms).filter_by(lang='en', current=True)
        missing = missing.filter(db.not_(Cms.page_id.in_(trans)))
    status = list_status()
    return render_template('admin/cms_list.html', pages=pages, lang=lang,
                           missing=missing, trans=trans, status=status)


def list_status():
    results = {}
    for lang in lang_codes:
        # Unpublished
        unpublished = Cms.query.filter_by(lang=lang, current=True).filter(
            Cms.status != 'publish'
        ).count()
        # Missing
        trans = db.session.query(Cms.page_id).filter_by(lang=lang)
        missing = db.session.query(Cms).filter_by(lang='en', current=True)
        missing = missing.filter(db.not_(Cms.page_id.in_(trans))).count()
        results[lang] = {'missing': missing, 'unpublished': unpublished}
    return results


def get_trans(id):
    results = {}
    rows = db.session.query(Cms.lang, Cms.status).filter_by(
        page_id=id, current=True
    )
    t = {}
    for row in rows:
        t[row.lang] = row.status
    for lang in lang_codes:
        if lang in t:
            if t[lang] == 'publish':
                results[lang] = {'missing': 0}
            else:
                results[lang] = {'unpublished': 1}
        else:
            results[lang] = {'missing': 1}
    return results


def set_menu():
    request.environ['MENU_PATH'] = url_for_admin('cms_list')[3:]
