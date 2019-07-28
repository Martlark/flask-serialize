import json
import random
import string

import pytest
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, redirect, url_for, render_template_string, abort
from flask_serialize.flask_serialize import FlaskSerializeMixin
from flask_wtf import FlaskForm
from wtforms import StringField


def random_key():
    return ''.join(random.sample(string.ascii_letters, 20))


class EditForm(FlaskForm):
    setting_type = StringField('setting_type')
    key = StringField('key')
    value = StringField('value')


app = Flask("test_app")
app.testing = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
db = SQLAlchemy(app)


@app.route('/setting_get/<item_id>', methods=['GET'])
def route_setting_get(item_id):
    return Setting.get_delete_put(item_id)


# Delete a single item.

@app.route('/setting_delete/<item_id>', methods=['DELETE'])
def route_setting_delete(item_id):
    return Setting.get_delete_put(item_id)


# Get all items as a json list.

@app.route('/setting_get_all', methods=['GET'])
def route_get_setting_all():
    return Setting.get_delete_put()


@app.route('/setting_update/<int:item_id>', methods=['PUT'])
def route_setting_update(item_id):
    item = Setting.query.get_or_404(item_id)
    item.request_update_json()
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
            except:
                abort(500)
            return redirect(url_for('route_setting_edit_add', item_id=item_id))
        else:
            try:
                new_item = Setting.request_create_form()
                return redirect(url_for('route_setting_edit_add', item_id=new_item.id))
            except Exception as e:
                print('Error creating item: ' + str(e))

    for err in form.errors:
        print('**form error**', str(err), form.errors[err])

    return render_template_string(
        '''
        <form submit="{{url_for('route_setting_edit_add')}}">
        <input name="key" value="{{item.key}}">
        <input name="setting_type" value="{{item.setting_type}}">
        <input name="value" value="{{item.value}}">
        </form>
        ''',
        item=item,
        title='Edit or Create item',
        form=form
    )


FlaskSerializeMixin.db = db


class SubSetting(FlaskSerializeMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    setting_id = db.Column(db.Integer, db.ForeignKey('setting.id'))
    flong = db.Column(db.String(120), index=True, default='flang')


class Setting(FlaskSerializeMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    setting_type = db.Column(db.String(120), index=True, default='misc')
    key = db.Column(db.String(120), index=True)
    value = db.Column(db.String(30000), default='')
    number = db.Column(db.Integer, default=0)
    active = db.Column(db.String(1), default='y')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow)
    # relationships
    sub_settings = db.relationship('SubSetting', backref='setting')

    # serializer fields
    create_fields = update_fields = ['setting_type', 'value', 'key', 'active', 'number']
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

    def __repr__(self):
        return '<Setting %r=%r %r>' % (self.key, self.setting_type, self.value)


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


def test_get_all(client):
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(json.loads(rv.data)) == 0
    key = 'test-key'
    # test add
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    json_settings = json.loads(rv.data)
    assert len(json_settings) == 1
    assert json_settings[0]['key'] == key


def test_relationships(client):
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(json.loads(rv.data)) == 0
    key = 'test-key'
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
    key = 'test-key'
    value = '1234'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key='test-key').first()
    assert item
    assert item.value == value
    rv = client.delete('/setting_delete/{}'.format(item.id))
    assert rv.status_code == 200
    # jsonify(dict(error=str(e), message=''))
    json_result = json.loads(rv.data)
    assert json_result['error'] == 'Deletion not allowed.  Magic value!'


def test_update_create_type_conversion(client):
    # create
    key = random_key()
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
    Setting.convert_types = [{'type': int, 'method': lambda n: n*2}]
    rv = client.put('/setting_update/{}'.format(item.id), json=dict(number=100))
    Setting.convert_types = old_convert_type
    assert rv.status_code == 200
    assert rv.data.decode('utf-8') == 'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item.number == 200


def test_excluded(client):
    # create
    key = random_key().upper()
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


def test_create_update_delete(client):
    # create
    key = random_key()
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == 'test-value'

    item.update_from_dict(dict(value='new-value'))
    assert item.value == 'new-value'
    # set to new value
    rv = client.post('/setting_edit/{}'.format(item.id),
                     data=dict(value='yet-another-value'))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == 'yet-another-value'
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
    # delete
    rv = client.delete('/setting_delete/{}'.format(item.id))
    assert rv.status_code == 200
    item = Setting.query.filter_by(key=key).first()
    assert not item
