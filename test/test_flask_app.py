import os
import string
import time
from datetime import datetime, timedelta
import random

from flask import Flask, redirect, url_for, render_template_string, abort, Response, request, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from flask_serialize.flask_serialize import FlaskSerializeMixin
from flask_wtf import FlaskForm

from wtforms import StringField, IntegerField, ValidationError, validators, HiddenField

app = Flask("test_app")
app.testing = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# =========================
# TINY TEST FLASK APP
# =========================


def random_string(length=20):
    """
    return a <length> long character random string of ascii_letters
    :param length: {int} number of characters to return
    :return:
    """
    return ''.join(random.sample(string.ascii_letters, length))


class EditForm(FlaskForm):
    setting_type = StringField('setting_type', [validators.DataRequired()])
    key = StringField('key')
    value = StringField('value')
    number = IntegerField('number')


@app.route('/')
@app.route('/<item_id>')
def page_index(item_id=None):
    settings = Setting.query.all()
    return render_template("index.html", title='Flask Serialize Tester', settings=settings, key=random_string(),
                           setting_type=random_string(), value=random_string())


# Get all items as a json list.
# post, put update
# and get single
@app.route('/setting_post', methods=['POST'])
@app.route('/setting_get_all', methods=['GET'])
@app.route('/setting_post/<int:item_id>', methods=['POST'])
@app.route('/setting_put/<int:item_id>', methods=['PUT'])
@app.route('/setting_get/<int:item_id>', methods=['GET'])
@app.route('/setting_user/<user>', methods=['GET'])
@app.route('/setting_id_user/<int:item_id>/<user>', methods=['GET'])
def route_setting_get_delete_put_post(item_id=None, user=None):
    key = request.args.get('key')
    if key and request.method == 'GET':
        return Setting.get_delete_put_post(item_id, prop_filters={"key": key})
    return Setting.get_delete_put_post(item_id, user)


@app.route('/sub_setting_delete/<int:item_id>', methods=['DELETE'])
@app.route('/sub_setting_put/<int:item_id>', methods=['PUT', 'POST'])
@app.route('/sub_setting_get/<int:item_id>', methods=['GET'])
def route_sub_setting_get_delete_put_post(item_id=None, user=None):
    return SubSetting.get_delete_put_post(item_id, user)


@app.route('/bad_add', methods=['POST'])
@app.route('/bad_edit/<int:item_id>', methods=['PUT', 'POST'])
def route_bad_get_delete_put_post(item_id=None, user=None):
    return BadModel.get_delete_put_post(item_id, user)


@app.route('/setting_get_json/<int:item_id>', methods=['GET'])
def route_setting_get_json(item_id):
    return Setting.json_get(item_id)


@app.route('/setting_json_first/<key>', methods=['GET'])
def route_setting_json_first(key):
    return Setting.json_first(key=key)


@app.route('/setting_get_key/<key>', methods=['GET'])
def route_setting_get_key(key):
    """
    get the first item that matches by a setting key

    :param key:
    :return:
    """
    return Setting.query.filter_by(key=key).first().as_json


# Delete a single item.

@app.route('/setting_delete/<int:item_id>', methods=['DELETE'])
def route_setting_delete(item_id):
    return Setting.get_delete_put_post(item_id)


@app.route('/setting_update/<int:item_id>', methods=['PUT'])
def route_setting_update(item_id):
    """
    update from a json object

    :param item_id: item to update
    :return:
    """
    item = Setting.query.get_or_404(item_id)
    try:
        item.request_update_json()
    except Exception as e:
        print(e)
        return Response('Error updating item: ' + str(e), 500)
    return 'Updated'


@app.route('/sub_setting_add/<int:setting_id>', methods=['POST'])
def route_sub_setting_add(setting_id):
    """
    add as a child using kwargs on request create form

    :param setting_id:
    :return:
    """
    setting = Setting.query.get_or_404(setting_id)
    try:
        SubSetting.request_create_form(setting_id=setting.id)
    except Exception as e:
        return str(e), 500
    return redirect(url_for("route_setting_edit_add", item_id=setting_id))


@app.route('/setting_edit/<int:item_id>', methods=['POST', 'GET'])
@app.route('/setting_add', methods=['POST'])
def route_setting_edit_add(item_id=None):
    if item_id:
        item = Setting.query.get_or_404(item_id)
    else:
        item = {}
    form = EditForm(obj=item)

    if form.validate_on_submit():
        if item_id:
            try:
                item.request_update_form()
            except Exception as e:
                print(e)
                return Response('Error updating item: ' + str(e), 500)
            return redirect(url_for('route_setting_edit_add', item_id=item_id))
        else:
            try:
                Setting.request_create_form()
                return redirect(url_for('page_index'))
            except Exception as e:
                print(e)
                return Response('Error creating item: ' + str(e), 500)
    for err in form.errors:
        flash('**form error** {} {}'.format(str(err), form.errors[err]))

    return render_template("setting_edit.html", item=item, title='Edit Setting', form=form)


@app.route('/setting_form_edit/<int:item_id>', methods=['POST', 'GET'])
@app.route('/setting_form_add', methods=['POST'])
def route_setting_form(item_id=None):
    return Setting.form_page(item_id)


# =========================
# MODELS
# =========================

FlaskSerializeMixin.db = db


class SubSetting(FlaskSerializeMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    sub_updated = db.Column(db.DateTime, default=datetime.utcnow)

    setting_id = db.Column(db.Integer, db.ForeignKey('setting.id'))
    flong = db.Column(db.String(120), index=True, default='flang')
    boolean = db.Column(db.Boolean, default=True)

    update_properties = create_fields = update_fields = ['flong', 'boolean']
    convert_types = [{'type': bool, 'method': lambda v: (type(v) == bool and v) or str(v).lower() == 'true'}, ]

    @staticmethod
    def one_day_ago():
        return datetime.utcnow() - timedelta(days=1)

    def to_date_short(self, date_value):
        """
        override DATETIME conversion behaviour to return unix time

        :param date_value:
        :return:
        """
        if not date_value:
            return 0

        return int(time.mktime(date_value.timetuple())) * 1000

    timestamp_fields = ['sub_updated']
    timestamp_stamper = one_day_ago


class Setting(FlaskSerializeMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    setting_type = db.Column(db.String(120), index=True, default='misc')
    key = db.Column(db.String(120), index=True)
    value = db.Column(db.String(3000), default='')
    number = db.Column(db.Integer, default=0)
    active = db.Column(db.String(1), default='y')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(10), default='Andrew')
    floaty = db.Column(db.Float(), default=1.1)
    # converter fields
    splitter = db.Column(db.String(122), index=True)
    zero = db.Column(db.String(123), default='10')
    # relationships
    sub_settings = db.relationship('SubSetting', backref='setting', cascade="all, delete-orphan")

    # serializer fields
    update_fields = ['setting_type', 'value', 'key', 'active', 'number', 'floaty', 'scheduled']
    create_fields = ['setting_type', 'value', 'key', 'active', 'user', 'splitter', 'floaty']
    exclude_serialize_fields = ['created']
    exclude_json_serialize_fields = ['updated']
    relationship_fields = ['sub_settings']
    update_properties = ['prop_test']
    order_by_field = 'value'
    # column splitter
    column_type_converters = {'VARCHAR(122)': lambda v: ','.join(str(v).split('.'))}
    # column zero
    column_type_converters['VARCHAR(123)'] = lambda v: int(v) / 0
    # convert types
    scheduled_date_format = "%Y-%m-%d %H:%M:%S"
    convert_types = [
        {'type': bool, 'method': lambda v: 'y' if (type(v) == bool and v) or str(v).lower() == 'true' else 'n'},
        {'type': int, 'method': lambda n: int(n) * 2},
        {'type': float, 'method': lambda n: float(n) * 2},
        {'type': datetime, 'method': lambda n: datetime.strptime(n, Setting.scheduled_date_format)}
    ]
    # form_page
    form = EditForm
    form_route_update = 'route_setting_form'
    form_route_create = 'page_index'
    form_template = 'setting_edit.html'
    form_new_title_format = 'New Setting'

    def before_update(self, data_dict):
        d = dict(data_dict)
        d['active'] = d.get('active', 'n')
        return d

    # checks if Flask-Serialize can delete
    def can_delete(self):
        if self.value == '1234':
            raise Exception('Deletion not allowed.  Magic value!')

    # checks if Flask-Serialize can create/update
    def verify(self, create=False):
        if len(self.key or '') < 1:
            raise ValidationError('Missing key')

        if self.value == '666':
            raise ValidationError('Value is Devils Number')

        if len(self.setting_type or '') < 2:
            raise ValidationError('Insufficient setting type')

    @property
    def prop_test(self):
        return 'prop:' + self.value

    @property
    def prop_error(self):
        return 'prop:' + str(1 / 0)

    @property
    def prop_test_dict(self):
        return {'prop': self.value}

    @property
    def prop_datetime(self):
        return self.created

    @property
    def prop_set(self):
        return set([1, 2, 3, 'four'])

    def add_sub(self, flong):
        sub = SubSetting(setting=self, flong=flong)
        db.session.add(sub)
        db.session.commit()
        return sub

    def __repr__(self):
        return 'Setting {}'.format(self.key)

class BadModel(FlaskSerializeMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(30), default='')

    def __repr__(self):
        return '<BadModel %r>' % (self.value)


if __name__ == '__main__':
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'Testing'
    app.config['WTF_CSRF_ENABLED'] = False
    db.create_all()
    app.run(debug=True, port=5055)
