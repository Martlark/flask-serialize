import json
import random
import string
import time

import pytest
from datetime import datetime

from test.test_flask_app import app, db, Setting, SubSetting


def random_string(length=20):
    """
    return a <length> long character random string of ascii_letters
    :param length: {int} number of characters to return
    :return:
    """
    return ''.join(random.sample(string.ascii_letters, length))


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
    # post item not found
    rv = client.post('/setting_post/{}'.format(random.randint(100, 999)),
                     data=dict(setting_type='test', key=key, value='new-value', number=10))
    assert rv.status_code == 404
    # post fail validation
    rv = client.post('/setting_post/{}'.format(item.id), data=dict(key=''))
    assert rv.status_code == 200
    json_result = json.loads(rv.data)
    assert json_result['error'] == 'Missing key'
    # update using put
    new_value = random_string()
    new_number = random.randint(0, 999)
    rv = client.put('/setting_put/{}'.format(item.id),
                    data=dict(setting_type='test', key=key, value=new_value, number=new_number))
    assert rv.status_code == 200
    assert json.loads(rv.data)['message'] == 'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == new_value
    assert item.number == new_number
    # put fail validation
    rv = client.put('/setting_put/{}'.format(item.id), data=dict(key=''))
    assert rv.status_code == 200
    json_result = json.loads(rv.data)
    assert json_result['error'] == 'Missing key'


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


def test_json_get(client):
    key = random_string()
    test_value = random_string()
    setting_type = random_string()
    # test add setting
    item = Setting(setting_type=setting_type, key=key, value=test_value)
    db.session.add(item)
    db.session.commit()
    item = Setting.query.get_or_404(item.id)
    # get by id
    json_item = json.loads(client.get('/setting_get_json/{}'.format(item.id)).data)
    assert json_item['value'] == test_value
    assert json_item['key'] == key
    assert json_item['setting_type'] == setting_type
    rv = client.get('/setting_get_json/{}'.format(item.id + 100))
    assert rv.status_code == 200
    json_item = json.loads(rv.data)
    assert json_item == {}
    # get first
    json_first_item = json.loads(client.get('/setting_json_first/{}'.format(item.key)).data)
    assert json_first_item['value'] == test_value
    assert json_first_item['key'] == key
    assert json_first_item['setting_type'] == setting_type
    assert json.loads(client.get('/setting_json_first/{}'.format(random_string())).data) == {}
