import json

import pytest
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, redirect, url_for, render_template_string
from flask_serialize.flask_serialize import FlaskSerializeMixin
from flask_wtf import FlaskForm
from wtforms import StringField


class EditForm(FlaskForm):
    setting_type = StringField('setting_type')
    key = StringField('key')
    value = StringField('value')


app = Flask("test_app")
app.testing = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
db = SQLAlchemy(app)


@app.route('/get_setting/<item_id>', methods=['GET'])
def get_setting(item_id):
    return Setting.get_delete_put(item_id)


# Delete a single item.

@app.route('/delete_setting/<item_id>', methods=['DELETE'])
def delete_setting(item_id):
    return Setting.get_delete_put(item_id)


# Get all items as a json list.

@app.route('/get_setting_all', methods=['GET'])
def get_setting_all():
    return Setting.get_delete_put()


@app.route('/setting_edit/<int:item_id>', methods=['POST'])
@app.route('/setting_add', methods=['POST'])
def setting_edit(item_id=None):
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
                print('Error updating item: ' + str(e))
            return redirect(url_for('setting_edit', item_id=item_id))
        else:
            try:
                new_item = Setting.request_create_form()
                return redirect(url_for('setting_edit', item_id=new_item.id))
            except Exception as e:
                print('Error creating item: ' + str(e))

    for err in form.errors:
        print('**form error**', str(err), form.errors[err])

    return render_template_string(
        '''
        <form submit="{{url_for('setting_edit')}}">
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
    active = db.Column(db.String(1), default='y')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow)
    # relationships
    sub_settings = db.relationship('SubSetting', backref='setting', lazy='dynamic')

    # serializer fields
    create_fields = update_fields = ['setting_type', 'value', 'key', 'active']
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
        return '<Setting %r %r %r>' % (self.id, self.setting_type, self.value)


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
    rv = client.get('/get_setting_all')
    assert rv.status_code == 200
    assert len(json.loads(rv.data)) == 0
    key = 'test-key'
    # test add
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    rv = client.get('/get_setting_all')
    assert rv.status_code == 200
    json_settings = json.loads(rv.data)
    assert len(json_settings) == 1
    assert json_settings[0]['key'] == key


def test_relationships(client):
    rv = client.get('/get_setting_all')
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
    rv = client.get('/get_setting_all')
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
    rv = client.delete('/delete_setting/{}'.format(item.id))
    assert rv.status_code == 200
    # jsonify(dict(error=str(e), message=''))
    json_result = json.loads(rv.data)
    assert json_result['error'] == 'Deletion not allowed.  Magic value!'


def test_excluded(client):
    # create
    key = 'test-key'
    value = '1234'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key='test-key').first()
    # test non-serialize fields excluded
    rv = client.get('/get_setting/{}'.format(item.id))
    json_result = json.loads(rv.data)
    assert 'created' not in json_result
    assert 'updated' not in json_result
    assert rv.status_code == 200
    assert 'created' not in item.as_dict
    assert 'updated' in item.as_dict


def test_create_update_delete(client):
    # create
    key = 'test-key'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key='test-key').first()
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
    rv = client.delete('/delete_setting/{}'.format(item.id))
    assert rv.status_code == 200
    item = Setting.query.filter_by(key=key).first()
    assert not item
