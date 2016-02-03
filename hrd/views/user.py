import cStringIO
from datetime import datetime

import qrcode
from passlib.hash import sha512_crypt as passlib
from flask import render_template, request, session, redirect, send_file, abort
from werkzeug.wrappers import Response

import flaskbb.user.views as bb_user
from flask.ext.babel import _
from hrd.bb import user_forms, forum_forms

from hrd import (app, db, url_for_admin, get_str, url_for, check_ga, config,
                 get_bool, permission_list, permission, default_url_for,
                 has_permission, lang_picker)
from hrd.models import User, UserPerms, Organisation

from hrd import googauth
from hrd import hrd_email

from flaskbb.user.models import Group, PrivateMessage
from flaskbb.forum.models import Post, Forum

from flask.ext.login import (current_user, login_user, login_required,
                             logout_user, login_fresh)



@app.before_request
def before_request():
    request.user = None
    request.permissions = []
    user = current_user
    if user.is_authenticated():
        ga = check_ga()
        if ga:
            return ga
        request.user = user
        request.permissions = get_users_permissions(user)



def get_users_permissions(user):
    try:
        return [
            p.permission
            for p in UserPerms.query.filter_by(user_id=user.id).all()
        ]
    except:
        return []


def password_verify(password, p_hash):
    return passlib.verify(password, p_hash)


def password_encrypt(value):
    return passlib.encrypt(value)


@app.route('/user/login', methods=['GET', 'POST'])
def login():
    username = ''
    if request.method == 'POST':
        username = get_str('name')
        password = get_str('password')
        if username and password:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                result = db.session.execute('SELECT ga_key FROM users WHERE id=:id',
                                            {'id':user.id}).first()
                if result[0]:
                    session['ga'] = 'check'
                else:
                    session['ga'] = 'setup'
                login_user(user)
                return redirect(url_for('cms_page2'))

    return render_template('user/login.html', username=username)


@app.route('/user/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('cms_page2'))


def send_reset_email(user):
    secret_key = googauth.generate_secret_key(32)
    db.session.execute('UPDATE users SET reset_code=:secret_key, reset_date=now() WHERE id=:id',
                       {'id':user.id, 'secret_key': secret_key})
    db.session.commit()
    link = default_url_for('reset_request_action', _external=True, key=secret_key, _scheme='https')
    msg = _('A password reset has been requested. Please click on the link below or paste it into your browser. This link is valid for 24 hours.')
    msg = msg + '\n\n' + link
    sender = config.EMAIL
    subject = _('HRD password reset request')
    hrd_email.send_email(user.email, subject=subject, content=msg, sender=sender)


def send_new_user(user, lang):
    secret_key = googauth.generate_secret_key(32)
    db.session.execute('UPDATE users SET reset_code=:secret_key, reset_date=now() WHERE id=:id',
                       {'id':user.id, 'secret_key': secret_key})
    db.session.commit()
    link = default_url_for('newuser_request_action', _external=True, key=secret_key, _scheme='https')
    with app.test_request_context(environ_overrides={'LANG': lang}):
        msg = _('You have been invited to join HRDRelocation.eu.')
        msg = msg + '\n\n' + link
        sender = config.EMAIL
        subject = _('HRD access')
        hrd_email.send_email(user.email, subject=subject, content=msg, sender=sender)


@app.route('/user/register', methods=['GET', 'POST'])
def newuser_request_action():
    key = request.args.get('key')
    if not key:
        abort(403)
    result = db.session.execute('SELECT id, reset_date FROM users WHERE reset_code=:key',
                                {'key': key}).first()
    if (not result):
        abort(403)
    if (datetime.now() - result.reset_date).days > 5:
        return render_template("user/link_out_of_date.html",
                              message=_('Your invite has expired, please request a new one'))
    # we are authorized
    error = ''
    if request.method == 'POST':
        p1 = get_str('password1')
        p2 = get_str('password2')
        if not (p1 and p2):
            error = _('Please provide a password and confirmed password')
        elif p1 != p2:
            error = _('Passwords do not match')
        elif len(p1) < 6:
            error = _('Password should be at least 6 characters long')
        if not error:
            user = User.query.filter_by(id=result.id).first()
            user.password = p1
            user.save()
            db.session.execute('UPDATE users SET reset_code=NULL, reset_date=NULL WHERE id=:id',
                       {'id':result.id})
            db.session.commit()
            return render_template("user/reset_password_complete.html", new_user=True)

    return render_template("user/reset_password.html", error=error, new_user=True)

@app.route("/user/resend_invite/<user_id>", methods=['GET', 'POST'])
def resend_invite(user_id):
    permission(['user_manage', 'user_admin'])
    resend = db.session.execute('SELECT reset_code, reset_date FROM users WHERE id=:id',
                       {'id':user_id}).first()

    if not bool(resend.reset_code or resend.reset_date):
        abort(403)

    user = User.query.filter_by(id=user_id).first()
    if request.method == 'GET':
        return render_template("user/resend_invite.html", langs=lang_picker)

    send_new_user(user, request.form.get('lang'))
    bb_user.flash(_("A fresh invite has been sent for this user."), "success")
    return redirect(url_for('user_profile', username=user.username))


@app.route('/user/reset_action', methods=['GET', 'POST'])
def reset_request_action():
    key = request.args.get('key')
    if not key:
        abort(403)
    result = db.session.execute('SELECT id, reset_date FROM users WHERE reset_code=:key',
                                {'key': key}).first()
    if (not result):
        abort(403)
    if (datetime.now() - result.reset_date).days > 0:
        return render_template("user/link_out_of_date.html",
                              message=_('This link has expired!'))
    # we are authorized
    error = ''
    if request.method == 'POST':
        p1 = get_str('password1')
        p2 = get_str('password2')
        if not (p1 and p2):
            error = _('Please provide a password and confirmed password')
        elif p1 != p2:
            error = _('Passwords do not match')
        elif len(p1) < 6:
            error = _('Password should be at least 6 characters long')
        if not error:
            user = User.query.filter_by(id=result.id).first()
            user.password = p1
            user.save()
            db.session.execute('UPDATE users SET reset_code=NULL, reset_date=NULL WHERE id=:id',
                       {'id':result.id})
            db.session.commit()
            return render_template("user/reset_password_complete.html", new_user=False)

    return render_template("user/reset_password.html", error=error, new_user=False)


@app.route('/user/reset', methods=['GET', 'POST'])
def reset_request():
    error = ''
    if request.method == 'POST':
        username = get_str('name')
        user = User.query.filter_by(username=username).first()
        if user:
            send_reset_email(user)
        return render_template('user/reset_request_sent.html', error=error)
    return render_template('user/reset_request.html', error=error)


@app.route("/user/reset_ga/<user_id>", methods=['GET', 'POST'])
def reset_ga(user_id):
    permission(['user_manage', 'user_admin'])

    user = User.query.filter_by(id=user_id).first()
    if not user:
        abort(403)
    if request.method == 'GET':
        return render_template("user/reset_ga.html", username=user.username)

    db.session.execute('UPDATE users set ga_key = null, ga_enabled = false WHERE id=:id',
                                {'id':user.id})
    db.session.commit()
    bb_user.flash(_("User GA Code has been reset."), "success")
    return redirect(url_for('user_profile', username=user.username))


@app.route('/user/ga_setup', methods=['GET', 'POST'])
def ga_setup():
    user = current_user
    if not user.is_authenticated():
        abort(403)
    result = db.session.execute('SELECT ga_key FROM users WHERE id=:id',
                                {'id':user.id}).first()
    if result[0]:
        abort(403)
    if request.method == 'POST':
        if get_str('cancel'):
            return logout()
        code = str(get_str('code'))
        key = get_str('key')
        if googauth.verify_time_based(key, code):
            db.session.execute('UPDATE users SET ga_key=:key WHERE id=:id',
                               {'id':user.id, 'key': key})
            db.session.commit()
            session['ga'] = 'authorized'
            return render_template('user/ga_setup_complete.html')
        else:
            error = _('The verification code is incorrect please try again')
    else:
        error = ''
        key = googauth.generate_secret_key()
    return render_template('user/ga_setup.html', key=key, error=error)


@app.route('/user/ga_check', methods=['GET', 'POST'])
def ga_check():
    user = current_user
    if not user.is_authenticated():
        abort(403)
    result = db.session.execute('SELECT ga_key FROM users WHERE id=:id',
                                {'id':user.id}).first()
    if not result[0]:
        logout_user()
        session.clear()
        return redirect(url_for('cms_page2'))

    if request.method == 'POST':
        if get_str('cancel'):
            return logout()
        user = current_user
        key = result[0]
        code = str(get_str('code'))
        if googauth.verify_time_based(key, code):
            session['ga'] = 'authorized'
            return redirect(url_for('cms_page2'))
        error = 'Your verification code is incorrect'
    else:
        error = ''
    return render_template('user/ga_check.html', error=error)

@app.route('/user/qr.svg')
def qr_code():
    key = request.args.get('key')
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    data = 'otpauth://totp/Hrd?secret=%s&issuer=Hrd' % key
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image()
    img_buf = cStringIO.StringIO()
    img.save(img_buf)
    img_buf.seek(0)
    return send_file(img_buf, mimetype='image/png')


@app.route("/user/profile/<username>")
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    resend = db.session.execute('SELECT reset_code, reset_date FROM users WHERE id=:id',
                       {'id':user.id}).first()

    can_resend_invite = bool(resend.reset_code or resend.reset_date)
    return render_template("user/profile.html", _user=user,
                           can_resend_invite=can_resend_invite)


@app.route('/user/profile', methods=['GET', 'POST'])
def user_my_profile():
    form = user_forms.ChangeUserDetailsForm(obj=current_user)

    if form.validate_on_submit():
        form.populate_obj(current_user)
        current_user.save()

        bb_user.flash(_("Your details have been updated!"), "success")

    return render_template("user/change_user_details.html", form=form)


@app.route("/user/password", methods=["POST", "GET"])
def user_change_password():
    form = user_forms.ChangePasswordForm()
    if form.validate_on_submit():
        current_user.password = form.new_password.data
        current_user.save()

        bb_user.flash(_("Your password have been updated!"), "success")
    return render_template("user/change_password.html", form=form)



@app.route("/user/email", methods=["POST", "GET"])
def user_change_email():
    form = user_forms.ChangeEmailForm(current_user)
    if form.validate_on_submit():
        current_user.email = form.new_email.data
        current_user.save()

        bb_user.flash(_("Your email have been updated!"), "success")
    return render_template("user/change_email.html", form=form)



@app.route("/user/manage", methods=['GET', 'POST'])
def user_manage():
    permission(['user_manage', 'user_admin'])
    page = request.args.get("page", 1, type=int)
    search_form = forum_forms.UserSearchForm()

    search = request.form.get('search_query')
    users = User.query
    if not has_permission('user_admin'):
        users = users.filter_by(organization=current_user.organization)
    if search:
        users = users.filter(User.username.like(u'%%%s%%' % search))
    users = users.order_by(User.username.asc()).\
        paginate(page, app.bb.config['USERS_PER_PAGE'], False)

    return render_template("user/users.html", users=users,
                           search_form=search_form)



@app.route("/user/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    permission(['user_manage', 'user_admin'])
    user = User.query.filter_by(id=user_id).first_or_404()

    if not has_permission('user_admin'):
        if user.organization != current_user.organization:
            abort(403)

    secondary_group_query = Group.query.filter(
        db.not_(Group.id == user.primary_group_id),
        db.not_(Group.banned == True),
        db.not_(Group.guest == True))

    form = user_forms.EditUserForm(user)
    form.secondary_groups.query = secondary_group_query
    if form.validate_on_submit():
        form.populate_obj(user)
        user.primary_group_id = form.primary_group.data.id

        user.save(groups=form.secondary_groups.data)

        if has_permission('user_admin'):
            update_user_perms(user)
            update_user_org(user)


        bb_user.flash("User successfully edited", "success")
        return redirect(url_for("user_edit", user_id=user.id))

    if has_permission('user_admin'):
        perms = permission_list
    else:
        perms = []

    user_perms = get_user_perms(user_id)
    return render_template("user/user_form.html", form=form, perms=perms,
                           orgs=get_orgs(), current_org=get_current_org(user),
                           user_perms=user_perms, title=_("Edit User"))


def get_current_org(user):
    return user.organization


def update_user_org(user):
    org = get_str('org')
    if org:
        check = Organisation.query.filter_by(org_id=org).first()
        if not check:
            return
    if not org:
        org = None
    user.organization = org
    user.save()



def update_user_perms(user):
    perms = permission_list
    # permissions
    p_in = []
    p_out = []
    for perm, rest in perms:
        if get_bool(perm):
            p_in.append(perm)
        else:
            p_out.append(perm)
    current = [
        p.permission for p in UserPerms.query.filter_by(user_id=user.id).all()
    ]
    for perm in p_in:
        if perm not in current:
            perm = UserPerms(user_id=user.id, permission=perm)
            db.session.add(perm)
    for perm in p_out:
        UserPerms.query.filter_by(user_id=user.id, permission=perm).delete()
    db.session.commit()
    if 'sys_admin' in p_in:
        user.primary_group_id = 1
    else:
        user.primary_group_id = 4
    user.save()

def get_user_perms(id):
    user_perms = [
        p.permission for p in UserPerms.query.filter_by(user_id=id).all()
    ]
    return user_perms



@app.route("/user/<int:user_id>/delete")
def user_delete(user_id):
    permission(['user_manage', 'user_admin'])
    user = User.query.filter_by(id=user_id).first_or_404()
    if not has_permission('user_admin'):
        if user.organization != current_user.organization:
            abort(403)

    posts = Post.query.filter_by(user_id=user.id).all()
    for post in posts:
        forums = Forum.query.filter_by(last_post_id=post.id).all()
        for forum in forums:
            forum.last_post_id = None
            forum.save()
        post.delete()

    PrivateMessage.query.filter_by(from_user_id=user.id).delete()
    PrivateMessage.query.filter_by(to_user_id=user.id).delete()

    user.delete()
    bb_user.flash("User successfully deleted", "success")
    return redirect(url_for("user_manage"))


@app.route("/user/add", methods=["GET", "POST"])
def user_add():
    permission(['user_manage', 'user_admin'])
    form = user_forms.AddUserForm()
    if form.validate_on_submit():
        user = form.save()
        if has_permission('user_admin'):
            update_user_perms(user)
            update_user_org(user)
        else:
            user.organization = current_user.organization
            user.save()
        send_new_user(user, request.form.get('lang'))
        bb_user.flash("User successfully added.", "success")
        return redirect(url_for("user_manage"))

    if has_permission('user_admin'):
        perms = permission_list
    else:
        perms = []

    return render_template("user/add_user_form.html", form=form, perms=perms,
                           langs=lang_picker, orgs=get_orgs(),
                           title=_("Add User"))

def get_orgs():
    if not has_permission('user_admin'):
        return []

    orgs = db.session.query(Organisation.org_id, Organisation.name).filter_by(lang='en', current=True)
    orgs = orgs.order_by('name')
    orgs = [{'value': '', 'name': 'None'}] + [{'value': v, 'name': n} for v, n in orgs]
    return orgs
