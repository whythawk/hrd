# -*- coding: utf-8 -*-
"""
    flaskbb.user.forms
    ~~~~~~~~~~~~~~~~~~~~

    It provides the forms that are needed for the user views.

    :copyright: (c) 2014 by the FlaskBB Team.
    :license: BSD, see LICENSE for more details.
"""
from flask.ext.login import current_user
from flask.ext.wtf import Form
from flask.ext.babel import lazy_gettext as _

from wtforms.ext.sqlalchemy.fields import (QuerySelectField,
                                           QuerySelectMultipleField)
from wtforms import (StringField, PasswordField, DateField, TextAreaField,
                     SelectField, ValidationError)
from wtforms.validators import (Length, DataRequired, Email, EqualTo, regexp,
                                Optional, URL)

from flaskbb.user.models import User, PrivateMessage, Group
from flaskbb.extensions import db
from flaskbb.utils.widgets import SelectDateWidget


from hrd import googauth

IMG_RE = r'^[^/\\]\.(?:jpg|gif|png)'

is_image = regexp(IMG_RE,
                  message=(_("Only jpg, jpeg, png and gifs are allowed!")))

USERNAME_RE = r'^[\w.+-]+$'
is_username = regexp(USERNAME_RE,
                     message=("You can only use letters, numbers or dashes"))



class GeneralSettingsForm(Form):
    # The choices for those fields will be generated in the user view
    # because we cannot access the current_app outside of the context
    #language = SelectField("Language")
    theme = SelectField("Theme")


class ChangeEmailForm(Form):
    old_email = StringField(_("Old E-Mail Address"), validators=[
        DataRequired(message=_("Email address required")),
        Email(message=_("This email is invalid"))])

    new_email = StringField(_("New E-Mail Address"), validators=[
        DataRequired(message=_("Email address required")),
        Email(message=_("This email is invalid"))])

    confirm_new_email = StringField(_("Confirm E-Mail Address"), validators=[
        DataRequired(message=_("Email adress required")),
        Email(message=_("This email is invalid")),
        EqualTo("new_email", message=_("E-Mails do not match"))])

    def __init__(self, user, *args, **kwargs):
        self.user = user
        kwargs['obj'] = self.user
        super(ChangeEmailForm, self).__init__(*args, **kwargs)

    def validate_email(self, field):
        user = User.query.filter(db.and_(
                                 User.email.like(field.data),
                                 db.not_(User.id == self.user.id))).first()
        if user:
            raise ValidationError(_("This email is taken"))


class ChangePasswordForm(Form):
    old_password = PasswordField(_("Old Password"), validators=[
        DataRequired(message=_("Password required"))])

    new_password = PasswordField(_("New Password"), validators=[
        DataRequired(message=_("Password required"))])

    confirm_new_password = PasswordField(_("Confirm New Password"), validators=[
        DataRequired(message=_("Password required")),
        EqualTo("new_password", message=_("Passwords do not match"))])


class ChangeUserDetailsForm(Form):
    # TODO: Better birthday field

    birthday = DateField(_("Your Birthday"), format="%d %m %Y",
                         widget=SelectDateWidget(), validators=[Optional()])

    gender = SelectField(_("Gender"), default="None", choices=[
        ("None", ""),
        ("Male", _("Male")),
        ("Female", _("Female"))])

    location = StringField(_("Location"), validators=[
        Optional()])

    website = StringField(_("Website"), validators=[
        Optional(), URL()])

    avatar = StringField(_("Avatar"), validators=[
        Optional(), URL()])

    signature = TextAreaField(_("Forum Signature"), validators=[
        Optional()])

    notes = TextAreaField(_("Notes"), validators=[
        Optional(), Length(min=0, max=5000)])


class NewMessageForm(Form):
    to_user = StringField(_("To User"), validators=[
        DataRequired(message="_(A username is required.")])
    subject = StringField(_("Subject"), validators=[
        DataRequired(message=_("A subject is required."))])
    message = TextAreaField(_("Message"), validators=[
        DataRequired(message=_("A message is required."))])

    def validate_to_user(self, field):
        user = User.query.filter_by(username=field.data).first()
        if not user:
            raise ValidationError(_("The username you entered doesn't exist"))
        if user.id == current_user.id:
            raise ValidationError(_("You cannot send a PM to yourself."))

    def save(self, from_user, to_user, user_id, unread, as_draft=False):
        message = PrivateMessage(
            subject=self.subject.data,
            message=self.message.data,
            unread=unread)

        if as_draft:
            return message.save(from_user, to_user, user_id, draft=True)
        return message.save(from_user, to_user, user_id)


class EditMessageForm(NewMessageForm):
    pass



def select_primary_group():
    return Group.query.filter(Group.guest == False).order_by(Group.id)


class UserForm(Form):
    username = StringField(_("Username"), validators=[
        DataRequired(message=_("A username is required.")),
        is_username])

    email = StringField(_("E-Mail"), validators=[
        DataRequired(message=_("A E-Mail address is required.")),
        Email(message=_("This email is invalid"))])

#    password = PasswordField(_("Password"), validators=[
 #       Optional()])

    birthday = DateField(_("Birthday"), format="%d %m %Y",
                         widget=SelectDateWidget(),
                         validators=[Optional()])

    gender = SelectField(_("Gender"), default="None", choices=[
        ("None", ""),
        ("Male", _("Male")),
        ("Female", _("Female"))])

    location = StringField(_("Location"), validators=[
        Optional()])

    website = StringField(_("Website"), validators=[
        Optional(), URL()])

    avatar = StringField(_("Avatar"), validators=[
        Optional(), URL()])

    signature = TextAreaField(_("Forum Signature"), validators=[
        Optional(), Length(min=0, max=250)])

    notes = TextAreaField(_("Notes"), validators=[
        Optional(), Length(min=0, max=5000)])

    primary_group = QuerySelectField(
        _("Primary Group"),
        query_factory=select_primary_group,
        get_label="name")

    secondary_groups = QuerySelectMultipleField(
        _("Secondary Groups"),
        # TODO: Template rendering errors "NoneType is not callable"
        #       without this, figure out why.
        query_factory=select_primary_group,
        allow_blank=True,
        get_label="name")

    def validate_username(self, field):
        if hasattr(self, "user"):
            user = User.query.filter(
                db.and_(User.username.like(field.data),
                        db.not_(User.id == self.user.id)
                        )
            ).first()
        else:
            user = User.query.filter(User.username.like(field.data)).first()

        if user:
            raise ValidationError(_("This username is taken"))

    def validate_email(self, field):
        if hasattr(self, "user"):
            user = User.query.filter(
                db.and_(User.email.like(field.data),
                        db.not_(User.id == self.user.id)
                        )
            ).first()
        else:
            user = User.query.filter(User.email.like(field.data)).first()

        if user:
            raise ValidationError(_("This email is taken"))

    def save(self):
        user = User(**self.data)
        return user.save()


class AddUserForm(Form):
    username = StringField(_("Username"), validators=[
        DataRequired(message=_("A username is required.")),
        is_username])

    email = StringField(_("E-Mail"), validators=[
        DataRequired(message=_("A E-Mail address is required.")),
        Email(message=_("This email is invalid"))])


    def validate_username(self, field):
        if hasattr(self, "user"):
            user = User.query.filter(
                db.and_(User.username.like(field.data),
                        db.not_(User.id == self.user.id)
                        )
            ).first()
        else:
            user = User.query.filter(User.username.like(field.data)).first()

        if user:
            raise ValidationError(_("This username is taken"))

    def validate_email(self, field):
        if hasattr(self, "user"):
            user = User.query.filter(
                db.and_(User.email.like(field.data),
                        db.not_(User.id == self.user.id)
                        )
            ).first()
        else:
            user = User.query.filter(User.email.like(field.data)).first()

        if user:
            raise ValidationError(_("This email is taken"))

    def save(self):
        user = User(_password=googauth.generate_secret_key(64), primary_group_id=4, **self.data)
        return user.save()




class EditUserForm(UserForm):
    def __init__(self, user, *args, **kwargs):
        self.user = user
        kwargs['obj'] = self.user
        super(UserForm, self).__init__(*args, **kwargs)


