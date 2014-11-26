import os.path
import uuid

from flask import (render_template, request, abort, redirect,
                   send_from_directory)
from flask import _request_ctx_stack

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool,
                 permission, permission_content, get_str, lang_codes)
from hrd.models import Organisation, OrgCodes
from hrd.views.codes import all_codes, cat_codes


ORG_PER_PAGE = 5


@app.route('/admin/org_logo/<type>/<id>')
def org_logo(type, id):
    if type == 'live':
        org = Organisation.query.filter_by(
            org_id=id, lang='en', status='publish'
        ).first()
    else:
        org = Organisation.query.filter_by(
            org_id=id, lang='en', current=True
        ).first()
    return send_from_directory(app.config['UPLOAD_FOLDER'], org.image)


@app.route('/admin/org_edit/<id>', methods=['GET', 'POST'])
def org_edit(id):
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    org = Organisation.query.filter_by(
        org_id=id, lang=lang, current=True
    ).first()
    if not org and lang != 'en':
        org = Organisation.query.filter_by(
            org_id=id, lang='en', current=True
        ).first()
        if not org:
            abort(404)
    if not org:
        abort(404)
    if request.method == 'POST' and 'name' in request.form:
        if org.lang != lang:
            # No translation
            org = org_reedit(org)
        if (org.name != get_str('name')
                or org.description != get_str('description')):
            if org.status == 'publish':
                org = org_reedit(org)
            org.name = get_str('name')
            org.description = get_str('description')
            org.status = 'edit'
            trans_need_update(org)

        if lang == 'en':
            org.address = get_str('address')
            org.contact = get_str('contact')
            org.phone = get_str('phone')
            org.email = get_str('email')
            org.pgp_key = get_str('pgp_key')
            org.website = get_str('website')
            org.private = get_bool('private')
            org.active = get_bool('active')

            logo = request.files['logo']
            if logo:
                extension = os.path.splitext(logo.filename)[1]
                filename = unicode(uuid.uuid4())
                if extension:
                    filename += extension
                logo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                org.image = filename
            if get_bool('logo_remove'):
                org.image = None


        db.session.add(org)
        if lang == 'en':
            # codes
            codes_data = all_codes('en', 'org')
            cats = [cat for cat in codes_data if cat['active']]
            cat_codes = []
            for cat in cats:
                cat_codes += cat['codes']
            codes = [code['code'] for code in cat_codes if code['active']]
            c_in = []
            c_out = []
            for code in codes:
                if get_bool(code):
                    c_in.append(code)
                else:
                    c_out.append(code)
            current = [
                c.code for c in OrgCodes.query.filter_by(org_id=id).all()
            ]
            for code in c_in:
                if code not in current:
                    code = OrgCodes(org_id=id, code=code)
                    db.session.add(code)
            for code in c_out:
                OrgCodes.query.filter_by(org_id=id, code=code).delete()

        db.session.commit()
        if lang == 'en':
            update_translations(org)
        return redirect(url_for_admin('org_preview', id=id))
    if lang != 'en':
        trans = Organisation.query.filter_by(
            org_id=org.org_id, lang='en', current=True
        ).first()
    else:
        trans = {}

    if lang == 'en':
        codes = all_codes('en', 'org')
        current = [
            c.code for c in OrgCodes.query.filter_by(org_id=id).all()
        ]
    else:
        codes = []
        current = []
    translations = get_trans(id)
    if lang != org.lang:
        org = {}
    return render_template('admin/org_edit.html', org=org, trans=trans,
                           codes=codes, current=current,
                           translations=translations)


def org_reedit(org):
    lang = get_admin_lang()
    new_org = Organisation(
        lang=lang,
        org_id=org.org_id,
        description=org.description,
        name=org.name,
        status='edit',
        published=True,

        address=org.address,
        contact=org.contact,
        phone=org.phone,
        email=org.email,
        pgp_key=org.pgp_key,
        website=org.website,
        private=org.private,
        active=org.active,
        image=org.image,

    )
    db.session.add(new_org)
    org.current = False
    db.session.add(org)
    db.session.commit()
    return new_org


@app.route('/admin/org_delete/<id>', methods=['POST'])
def org_delete(id):
    permission('content_manage')
    Organisation.query.filter_by(org_id=id).delete()
    db.session.commit()
    return redirect(url_for_admin('org_list'))


@app.route('/admin/org_new/', methods=['POST'])
def org_new():
    permission('content_manage')
    lang = 'en'
    org = Organisation(lang=lang)
    org.status = 'edit'
    db.session.add(org)
    db.session.commit()
    return redirect(url_for_admin('org_edit', id=org.org_id))


STATES = {
    'approve': 'edit',
    'approved': 'approve',
    'publish': 'approved',
}


@app.route('/admin/org_state/<id>/<state>', methods=['POST'])
def org_state(id, state):
    lang = get_admin_lang()
    permission_content(lang)
    if state not in STATES:
        abort(403)
    org = Organisation.query.filter_by(
        org_id=id, status=STATES[state], lang=lang, current=True
    ).first()
    if not org:
        abort(403)
    if state == 'publish':
        org.published = True
        old_org = Organisation.query.filter_by(
            org_id=id, status='publish', lang=lang
        ).first()
        if old_org:
            old_org.status = 'archive'
            db.session.add(old_org)
    org.status = state
    db.session.add(org)
    db.session.commit()
    return redirect(url_for_admin('org_preview', id=id))


def trans_need_update(org):
    # FIXME trigger updates needed for trans
    pass


def update_translations(org):
    trans = Organisation.query.filter_by(org_id=org.org_id)
    trans = trans.filter(db.not_(Organisation.id == org.id))
    trans = trans.filter(
        db.or_(
            Organisation.status == 'publish', Organisation.current == True
        )
    )

    for tran in trans:
        tran.address = org.address
        tran.contact = org.contact
        tran.phone = org.phone
        tran.email = org.email
        tran.pgp_key = org.pgp_key
        tran.website = org.website
        tran.active = org.active
        tran.private = org.private
        tran.image = org.image
        db.session.add(tran)
    db.session.commit()


@app.route('/org/<id>')
def org(id):
    lang = get_admin_lang()
    lang = request.environ['LANG']
    org = Organisation.query.filter_by(
        org_id=id, lang=lang, status='publish', active=True
    )

    org = org.first()
    if not org:
        org = Organisation.query.filter_by(
            org_id=id, lang='en', status='publish', active=True
        ).first()
        if not org:
            abort(404)

    # only show public orgs
    if not bool(request.user) and org.private:
        abort(403)

    cat_codes = org_cat_codes(lang, id)
    return render_template('admin/org.html',
                           org=org,
                           cat_codes=cat_codes)


def org_cat_codes(lang, id):
    codes = all_codes(lang, 'org')
    current = [
        c.code for c in OrgCodes.query.filter_by(org_id=id).all()
    ]
    out = []
    for cat in codes:
        found = []
        for code in cat['codes']:
            if code['code_id'] in current:
                found.append(code['title'])
        if found:
            out.append((cat['title'], ', '.join(found)))
    return out


@app.route('/admin/org_preview/<id>')
def org_preview(id):
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    org = Organisation.query.filter_by(
        org_id=id, lang=lang, current=True
    ).first()
    if not org:
        org = Organisation.query.filter_by(
            org_id=id, lang='en', current=True
        ).first()
        if not org:
            abort(404)
    translations = get_trans(id)
    cat_codes = org_cat_codes(lang, id)
    ctx = _request_ctx_stack.top
    if ctx:
        ctx.babel_locale = lang
    return render_template('admin/org_preview.html', org=org,
                           cat_codes=cat_codes,
                           translations=translations)


def get_trans(id):
    results = {}
    rows = db.session.query(Organisation.lang, Organisation.status).filter_by(
        org_id=id, current=True
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


@app.route('/admin/org')
def org_list():
    set_menu()
    lang = get_admin_lang()
    permission_content(lang)
    orgs = Organisation.query.filter_by(lang=lang, current=True)
    orgs = orgs.order_by('name')
    for org in orgs:
        p = Organisation.query.filter_by(
            org_id=org.org_id, lang=lang, status='publish'
        ).first()
        org.has_published = bool(p)
    if lang == 'en':
        missing = []
        trans = {}
    else:
        # missing orgs
        trans = db.session.query(Organisation.org_id).filter_by(
            lang=lang, current=True
        )
        missing = db.session.query(Organisation).filter_by(
            lang='en', current=True
        )
        missing = missing.filter(db.not_(Organisation.org_id.in_(trans)))
    status = list_status()
    return render_template('admin/org_list.html', orgs=orgs, lang=lang,
                           missing=missing, trans=trans, status=status)


def list_status():
    results = {}
    for lang in lang_codes:
        # Unpublished
        unpublished = Organisation.query.filter_by(
            lang=lang, current=True
        ).filter(
            Organisation.status != 'publish'
        ).count()
        # Missing
        trans = db.session.query(Organisation.org_id).filter_by(lang=lang)
        missing = db.session.query(Organisation).filter_by(
            lang='en', current=True
        )
        missing = missing.filter(
            db.not_(Organisation.org_id.in_(trans))
        ).count()
        results[lang] = {'missing': missing, 'unpublished': unpublished}
    return results


@app.route('/orgs')
def org_search():
    lang = request.environ['LANG']
    cats = all_codes(lang, 'org')
    codes_list = cat_codes(lang, 'org')


    orgs = Organisation.query.filter_by(
        lang=lang, status='publish', active=True
    )

    # only show public orgs
    if not bool(request.user):
        orgs = orgs.filter_by(private=False)

    search_codes = set()
    for field, _null in request.args.items():
        if field == 'Filter':
            continue
        search_codes.add(field)

    for codes in codes_list:
        union = set(codes) & search_codes
        if union:
            c = db.session.query(OrgCodes.org_id).filter(OrgCodes.code.in_(list(union)))
            orgs = orgs.filter(Organisation.org_id.in_(c))

    orgs = orgs.order_by('name')

    count = orgs.count()
    try:
        page = int(request.args.get('page', 0))
    except ValueError:
        page = 0
    pages = page_num(count, ORG_PER_PAGE)

    orgs = orgs.limit(ORG_PER_PAGE).offset(page * ORG_PER_PAGE)
    orgs = orgs.all()


    return render_template(
        'org_search.html', cats=cats, orgs=orgs, count=count, page=page, pages=pages
    )


def page_num(count, number_per_page):
    if count % number_per_page:
        return (count / number_per_page) + 1
    return count / number_per_page


def get_trans(id):
    results = {}
    rows = db.session.query(Organisation.lang, Organisation.status).filter_by(
        org_id=id, current=True
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
    request.environ['MENU_PATH'] = url_for_admin('org_list')[3:]
