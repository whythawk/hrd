from flask import render_template, request, abort, redirect

from hrd import (app, db, url_for_admin, get_admin_lang, get_bool,
                 permission, permission_content, get_str)
from hrd.models import Organisation, OrgCodes
from hrd.views.codes import all_codes

@app.route('/admin/org_edit/<id>', methods=['GET', 'POST'])
def org_edit(id):
    lang = get_admin_lang()
    permission_content(lang)
    org = Organisation.query.filter_by(org_id=id, lang=lang, current=True)
    org = org.filter(Organisation.status != 'publish').first()
    if not org:
        abort(404)
    if org.status == 'publish':
        return redirect(url_for_admin('org_reedit', id=id), code=307)
    if request.method == 'POST':
        org.name = get_str('name')
        org.description = get_str('description')
        org.status = 'edit'
        db.session.add(org)
        if lang == 'en':
            locked = {
                'active': get_bool('active'),
            }
            Organisation.query.filter_by(org_id=org.org_id).update(locked)
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
        return redirect(url_for_admin('org_preview', id=id))
    if lang != 'en':
        trans = Organisation.query.filter_by(org_id=org.org_id, lang='en',
                                    current=True).first()
    else:
        trans = {}

    if lang == 'en':
        codes = all_codes('en', 'org')
        current = [
            c.code for c in OrgCodes.query.filter_by(org_id=id).all()
        ]
        print current
    else:
        codes = []
        current = []
    return render_template('admin/org_edit.html', org=org, trans=trans,
                           codes=codes, current=current)


@app.route('/admin/org_reedit/<id>', methods=['POST'])
def org_reedit(id):
    lang = get_admin_lang()
    permission_content(lang)
    org = Organisation.query.filter_by(org_id=id, status='publish', lang=lang,
                               current=True).first()
    if not org:
        abort(404)
    new_org = Organisation(
        lang=lang,
        org_id=org.org_id,
        description=org.description,
        name=org.name,
        status='edit',
        published=True
    )
    db.session.add(new_org)
    org.current = False
    db.session.add(org)
    db.session.commit()
    return redirect(url_for_admin('org_edit', id=new_org.org_id))


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
    org = Organisation.query.filter_by(org_id=id, status=STATES[state], lang=lang,
                               current=True).first()
    if not org:
        abort(403)
    if state == 'publish':
        org.published = True
        old_org = Organisation.query.filter_by(org_id=id, status='publish',
                                       lang=lang).first()
        if old_org:
            old_org.status = 'archive'
            db.session.add(old_org)
    org.status = state
    db.session.add(org)
    db.session.commit()
    return redirect(url_for_admin('org_preview', id=id))


@app.route('/org/<id>')
def org(id):
    lang = get_admin_lang()
    lang = request.environ['LANG']
    org = Organisation.query.filter_by(org_id=id, lang=lang, status='publish').first()
    if not org:
        abort(404)
    return render_template('admin/org_preview.html', org=org)


@app.route('/admin/org_preview/<id>')
def org_preview(id):
    lang = get_admin_lang()
    permission_content(lang)
    org = Organisation.query.filter_by(org_id=id, lang=lang, current=True).first()
    if not org:
        abort(404)
    return render_template('admin/org_preview.html', org=org)


@app.route('/admin/org_trans/<id>', methods=['POST'])
def org_trans(id):
    lang = get_admin_lang()
    permission_content(lang)
    org = Organisation.query.filter_by(org_id=id, lang='en').first()
    if not org:
        abort(404)
    exists = Organisation.query.filter_by(org_id=org.org_id, lang=lang).first()
    if exists:
        abort(403)
    trans = Organisation(lang=lang)
    trans.status = 'edit'
    trans.org_id = org.org_id
    db.session.add(trans)
    db.session.commit()
    return redirect(url_for_admin('org_edit', id=trans.org_id))

@app.route('/admin/org')
def org_list():
    lang = get_admin_lang()
    permission_content(lang)
    orgs = Organisation.query.filter_by(lang=lang, current=True)
    orgs = orgs.order_by('name')
    for org in orgs:
        p = Organisation.query.filter_by(org_id=org.org_id, lang=lang,
                                status='publish').first()
        org.has_published = bool(p)
    if lang == 'en':
        missing = []
        trans = {}
    else:
        # missing orgs
        trans = db.session.query(Organisation.org_id).filter_by(lang=lang)
        missing = db.session.query(Organisation).filter_by(lang='en')
        missing = missing.filter(db.not_(Organisation.org_id.in_(trans)))
    return render_template('admin/org_list.html', orgs=orgs, lang=lang,
                           missing=missing, trans=trans)
