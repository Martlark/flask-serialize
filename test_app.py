import json
import random
import string
import time

import pytest
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, redirect, url_for, render_template_string, abort, Response
from flask_serialize.flask_serialize import FlaskSerializeMixin
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField


def random_string(length=20):
    """
    return a <length> long character random string of ascii_letters
    :param length: {int} number of characters to return
    :return:
    """
    return ''.join(random.sample(string.ascii_letters, length))


# =========================
# TINY TEST FLASK APP
# =========================

class EditForm(FlaskForm):
    setting_type = StringField('setting_type')
    key = StringField('key')
    value = StringField('value')
    number = IntegerField('number')


app = Flask("test_app")
app.testing = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
db = SQLAlchemy(app)


# Get all items as a json list.
# post and get
@app.route('/setting_post', methods=['POST'])
@app.route('/setting_get_all', methods=['GET'])
@app.route('/setting_post/<item_id>', methods=['POST'])
@app.route('/setting_get/<item_id>', methods=['GET'])
@app.route('/setting_user/<user>', methods=['GET'])
@app.route('/setting_id_user/<int:item_id>/<user>', methods=['GET'])
def route_setting_get(item_id=None, user=None):
    return Setting.get_delete_put_post(item_id, user)


@app.route('/setting_get_key/<key>', methods=['GET'])
def route_setting_get_key(key):
    """
    get the first item that matches by a setting key
    :param key:
    :return:
    """
    return Setting.query.filter_by(key=key).first().as_json


# Delete a single item.

@app.route('/setting_delete/<item_id>', methods=['DELETE'])
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
        return Response('Error updating item: ' + str(e), 500)
    return 'Updated'


@app.route('/setting_edit/<int:item_id>', methods=['POST'])
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
                return Response('Error updating item: ' + str(e), 500)
            return redirect(url_for('route_setting_edit_add', item_id=item_id))
        else:
            try:
                new_item = Setting.request_create_form()
                return redirect(url_for('route_setting_edit_add', item_id=new_item.id))
            except Exception as e:
                return Response('Error creating item: ' + str(e), 500)

    for err in form.errors:
        print('**form error**', str(err), form.errors[err])

    return render_template_string(
        '''
        <form submit="{{url_for('route_setting_edit_add')}}">
        <input name="key" value="{{item.key}}">
        <input name="setting_type" value="{{item.setting_type}}">
        <input name="value" value="{{item.value}}">
        <input name="number" value="{{item.number}}">
        </form>
        ''',
        item=item,
        title='Edit or Create item',
        form=form
    )


# =========================
# MODELS
# =========================

FlaskSerializeMixin.db = db


class SubSetting(FlaskSerializeMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    setting_id = db.Column(db.Integer, db.ForeignKey('setting.id'))
    flong = db.Column(db.String(120), index=True, default='flang')

    def to_date_short(self, date_value):
        """
        override DATETIME conversion behaviour to return unix time
        :param date_value:
        :return:
        """
        if not date_value:
            return 0

        return int(time.mktime(date_value.timetuple())) * 1000


class Setting(FlaskSerializeMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    setting_type = db.Column(db.String(120), index=True, default='misc')
    key = db.Column(db.String(120), index=True)
    value = db.Column(db.String(3000), default='')
    number = db.Column(db.Integer, default=0)
    active = db.Column(db.String(1), default='y')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(10), default='Andrew')
    # relationships
    sub_settings = db.relationship('SubSetting', backref='setting')

    # serializer fields
    update_fields = ['setting_type', 'value', 'key', 'active', 'number']
    create_fields = ['setting_type', 'value', 'key', 'active', 'user']
    exclude_serialize_fields = ['created']
    exclude_json_serialize_fields = ['updated']
    relationship_fields = ['sub_settings']

    # checks if Flask-Serialize can delete
    def can_delete(self):
        if self.value == '1234':
            raise Exception('Deletion not allowed.  Magic value!')

    # checks if Flask-Serialize can create/update
    def verify(self, create=False):
        if not self.key or len(self.key) < 1:
            raise Exception('Missing key')

        if not self.setting_type or len(self.setting_type) < 1:
            raise Exception('Missing setting type')

    @property
    def prop_test(self):
        return 'prop:' + self.value

    def __repr__(self):
        return '<Setting %r=%r %r>' % (self.key, self.setting_type, self.value)


# =========================
# TESTS
# =========================


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'Testing'
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    with app.app_context():
        db.create_all()

    yield client

    db.drop_all()


def add_setting(client, key=random_string(), value='test-value'):
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    return item


def test_get_all(client):
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(json.loads(rv.data)) == 0
    key = random_string()
    # test add
    item = add_setting(client, key=key)
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    json_settings = json.loads(rv.data)
    assert len(json_settings) == 1
    assert json_settings[0]['key'] == key
    with app.app_context():
        rv = Setting.json_filter_by(key=key)
        json_settings = json.loads(rv.data)
        assert json_settings[0]['key'] == key


def test_get_user(client):
    key = random_string()
    # test add 2 settings
    client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    test_user_name = random_string()
    client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value', user=test_user_name))
    rv = client.get('/setting_user/{}'.format(test_user_name))
    json_settings = json.loads(rv.data)
    assert len(json_settings) == 1
    item = json_settings[0]
    assert item['user'] == test_user_name
    rv = client.get('/setting_id_user/{}/{}'.format(item['id'], test_user_name))
    item = json.loads(rv.data)
    assert item['user'] == test_user_name
    rv = client.get('/setting_user/{}'.format('no-one'))
    json_settings = json.loads(rv.data)
    assert len(json_settings) == 0


def test_get_property(client):
    key = random_string()
    test_value = random_string()
    # test add a thing
    add_setting(client, key=key, value=test_value)
    rv = client.get('/setting_get_key/{}'.format(key))
    assert rv.status_code == 200
    json_settings = json.loads(rv.data)
    assert json_settings['prop_test'] == 'prop:' + test_value


def test_relationships(client):
    key = random_string()
    # test add
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    # add relation
    setting = Setting.query.filter_by(setting_type='test').first()
    sub_setting = SubSetting(flong='blong', setting=setting)
    db.session.add(sub_setting)
    db.session.commit()
    # see if returned
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    json_settings = json.loads(rv.data)
    assert len(json_settings) == 1
    assert len(json_settings[0]['sub_settings']) == 1
    assert json_settings[0]['sub_settings'][0]['flong'] == 'blong'


def test_can_delete(client):
    # create
    key = random_string()
    value = '1234'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == value
    rv = client.delete('/setting_delete/{}'.format(item.id))
    assert rv.status_code == 200
    # jsonify(dict(error=str(e), message=''))
    json_result = json.loads(rv.data)
    assert json_result['error'] == 'Deletion not allowed.  Magic value!'


def test_column_conversion(client):
    # create
    key = random_string()
    value = '12.34'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    # get
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.as_dict['value'] == '12.34'
    item.column_type_converters = {'VARCHAR(3000)': lambda v: ','.join(str(v).split('.'))}
    assert item.as_dict['value'] == '12,34'
    # remove custom converter
    item.column_type_converters = {'VARCHAR(3000)': None}
    assert item.as_dict['value'] == '12.34'
    # remove built in DATETIME converter
    converted_date = item.as_dict['updated']
    item.column_type_converters = {'DATETIME': None}
    un_converted_date = item.as_dict['updated']
    assert converted_date != un_converted_date
    assert type(un_converted_date) == datetime


def test_update_create_type_conversion(client):
    # create
    key = random_string()
    value = '1234'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    # default bool type conversion
    rv = client.put('/setting_update/{}'.format(item.id), json=dict(active=False))
    assert rv.status_code == 200
    assert rv.data.decode('utf-8') == 'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item.active == 'n'
    rv = client.put('/setting_update/{}'.format(item.id), json=dict(active=True))
    assert rv.status_code == 200
    assert rv.data.decode('utf-8') == 'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item.active == 'y'
    # add conversion type
    old_convert_type = Setting.convert_types
    Setting.convert_types = [{'type': int, 'method': lambda n: n * 2}]
    rv = client.put('/setting_update/{}'.format(item.id), json=dict(number=100))
    Setting.convert_types = old_convert_type
    assert rv.status_code == 200
    assert rv.data.decode('utf-8') == 'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item.number == 200


def test_excluded(client):
    # create
    key = random_string()
    value = '1234'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    # test non-serialize fields excluded
    rv = client.get('/setting_get/{}'.format(item.id))
    json_result = json.loads(rv.data)
    assert 'created' not in json_result
    assert 'updated' not in json_result
    assert rv.status_code == 200
    assert 'created' not in item.as_dict
    assert 'updated' in item.as_dict


def test_get_delete_put_post(client):
    key = random_string()
    # create using post
    rv = client.post('/setting_post', data=dict(setting_type='test', key=key, value='test-value', number=10))
    assert rv.status_code == 200
    item_json = json.loads(rv.data)
    item = Setting.query.get_or_404(item_json['id'])
    assert item
    assert item_json['value'] == 'test-value'
    assert item.value == 'test-value'
    assert item.number == 0
    # update using post
    rv = client.post('/setting_post/{}'.format(item.id),
                     data=dict(setting_type='test', key=key, value='new-value', number=10))
    assert rv.status_code == 200
    assert json.loads(rv.data)['message'] == 'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == 'new-value'
    assert item.number == 10


def test_create_update_delete(client):
    # create
    key = random_string()
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value', number=10))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == 'test-value'
    # test that number is not set on creation as it is not included in create_fields
    assert item.number == 0
    old_updated = item.updated

    item.update_from_dict(dict(value='new-value'))
    assert item.value == 'new-value'
    # set to new value
    rv = client.post('/setting_edit/{}'.format(item.id),
                     data=dict(value='yet-another-value', number=100))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == 'yet-another-value'
    assert item.number == 100
    # check updated is changing
    assert old_updated != item.updated
    # set to ''
    rv = client.post('/setting_edit/{}'.format(item.id),
                     data=dict(value=''))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert not item.value
    # fail validation
    rv = client.post('/setting_edit/{}'.format(item.id),
                     data=dict(key=''))
    assert rv.status_code == 500
    assert rv.data.decode('utf-8') == 'Error updating item: Missing key'
    # delete
    rv = client.delete('/setting_delete/{}'.format(item.id))
    assert rv.status_code == 200
    item = Setting.query.filter_by(key=key).first()
    assert not item


def test_raise_error_for_create_fields(client):
    key = random_string()
    # add
    old_create_fields = Setting.create_fields
    # remove fields
    Setting.create_fields = []
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    assert rv.status_code == 500
    assert rv.data.decode('utf-8') == 'Error creating item: create_fields is empty'
    Setting.create_fields = old_create_fields


def test_raise_error_for_update_fields(client):
    key = random_string()
    # add
    old_fields = Setting.update_fields
    client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    item = Setting.query.filter_by(key=key).first()
    # remove fields
    Setting.update_fields = []
    # form
    rv = client.post('/setting_edit/{}'.format(item.id), data=dict(setting_type='test', key=key, value='test-value'))
    assert rv.status_code == 500
    assert rv.data.decode('utf-8') == 'Error updating item: update_fields is empty'
    # json
    rv = client.put('/setting_update/{}'.format(item.id), data=dict(setting_type='test', key=key, value='test-value'))
    assert rv.status_code == 500
    assert rv.data.decode('utf-8') == 'Error updating item: update_fields is empty'
    Setting.update_fields = old_fields


def test_override_datetime_conversion(client):
    key = random_string()
    test_value = random_string()
    # test add a thing
    item = add_setting(client, key=key, value=test_value)
    sub_setting = SubSetting(setting=item, flong=random_string(5))
    db.session.add(sub_setting)
    db.session.commit()
    item = Setting.query.filter_by(key=key).first()
    sub = item.sub_settings[0]
    unix_time = int(time.mktime(sub.created.timetuple())) * 1000
    assert type(sub.as_dict['created']) == int
    assert sub.as_dict['created'] == unix_time
