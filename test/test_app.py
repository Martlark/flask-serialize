import random
import string
import time

import pytest

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


def test_order_by_field(client):
    # add plenty
    count = 10
    for z in range(count):
        add_setting(client, key=str(z), value=str(z + 1))

    Setting.order_by_field = 'id'
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    json_settings = rv.json
    assert len(json_settings) == count
    sorted_list = sorted(json_settings, key=lambda i: i['id'])
    for z in range(count):
        assert json_settings[z]['id'] == sorted_list[z]['id']
    # ascending.
    Setting.order_by_field = 'value'
    rv = client.get('/setting_get_all')
    json_settings = rv.json
    sorted_list = sorted(json_settings, key=lambda i: i['value'])
    for z in range(count):
        assert json_settings[z]['value'] == sorted_list[z]['value']
    Setting.order_by_field = None
    Setting.order_by_field_desc = 'value'
    # descending
    rv = client.get('/setting_get_all')
    json_settings = rv.json
    sorted_list = sorted(json_settings, key=lambda i: i['value'], reverse=True)
    for z in range(count):
        assert json_settings[z]['value'] == sorted_list[z]['value']


def test_get_filter(client):
    key_1 = random_string()
    key_2 = random_string()
    # test add
    add_setting(client, key=key_1)
    add_setting(client, key=key_2)
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(rv.json) == 2
    rv = client.get(f'/setting_get_all?key={key_1}')
    assert rv.json[0]['key'] == key_1
    assert len(rv.json) == 1
    rv = client.get(f'/setting_get_all?key={key_2}')
    assert len(rv.json) == 1
    assert rv.json[0]['key'] == key_2


def test_get_all(client):
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(rv.json) == 0
    key = random_string()
    # test add
    item = add_setting(client, key=key)
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(rv.json) == 1
    assert rv.json[0]['key'] == key
    with app.app_context():
        # filter by
        rv = Setting.json_filter_by(key=key)
        assert rv.json[0]['key'] == key
    # all as dict list
    result = Setting.query.all()
    dict_list = Setting.dict_list(result)
    assert len(dict_list) == 1
    assert dict_list[0]['key'] == key


def test_get_user(client):
    key = random_string()
    # test add 2 settings
    client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    test_user_name = random_string()
    client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value', user=test_user_name))
    rv = client.get('/setting_user/{}'.format(test_user_name))
    assert len(rv.json) == 1
    item = rv.json[0]
    assert item['user'] == test_user_name
    rv = client.get('/setting_id_user/{}/{}'.format(item['id'], test_user_name))
    assert rv.json['user'] == test_user_name
    # should not be found
    rv = client.get('/setting_id_user/{}/{}'.format(item['id'], random_string()))
    assert rv.status_code == 404
    # get all by user
    rv = client.get('/setting_user/{}'.format('no-one'))
    assert len(rv.json) == 0
    user_404 = None
    try:
        user_404 = Setting.get_by_user_or_404(item_id=item['id'], user='not-here')
    except Exception as e:
        assert '404 Not Found:' in str(e)
    assert user_404 is None


def test_get_property(client):
    key = random_string()
    test_value = random_string()
    # test add a thing
    add_setting(client, key=key, value=test_value)
    setting = Setting.query.filter_by(key=key).first()
    rv = client.get('/setting_get_key/{}'.format(key))
    assert rv.status_code == 200
    assert rv.json['prop_test'] == 'prop:' + test_value
    assert rv.json['prop_error'] == 'division by zero'
    assert rv.json['prop_datetime'] == str(setting.created).split('.')[0]
    assert rv.json['prop_test_dict'] == {'prop': test_value}
    assert set(rv.json['prop_set']) == set([3, 1, 2, 'four'])


def test_relationships(client):
    key = random_string()
    # test add
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value='test-value'))
    # add relation
    setting = Setting.query.filter_by(setting_type='test').first()
    client.post(f'/sub_setting_add/{setting.id}', data=dict(flong='blong', setting=setting))
    # see if returned
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(rv.json) == 1
    assert len(rv.json[0]['sub_settings']) == 1
    assert rv.json[0]['sub_settings'][0]['flong'] == 'blong'


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
    assert rv.status_code == 400
    assert rv.data == b'Deletion not allowed.  Magic value!'


def test_column_conversion(client):
    # create
    key = random_string()
    value = '12.34'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, splitter=value))
    # get
    item = Setting.query.filter_by(key=key).first()
    assert item.as_dict['splitter'] == '12,34'
    assert item.as_dict['zero'] == 'Error:"division by zero". Failed to convert [zero] type:VARCHAR(123)'


def test_update_create_type_conversion(client):
    # create
    key = random_string()
    value = '1234'
    rv = client.post('/setting_add', data=dict(setting_type='test', key=key, value=value))
    assert rv.status_code == 302
    item = Setting.query.filter_by(key=key).first()
    assert item
    # default bool type conversion
    # json
    rv = client.put('/setting_update/{}'.format(item.id), json=dict(active=False))
    assert rv.status_code == 200
    assert rv.data == b'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item.active == 'n'
    # query parameters as strings so bool converter does not work
    rv = client.put('/setting_update/{}'.format(item.id), query_string=dict(active='y'))
    assert rv.status_code == 200
    assert rv.data == b'Updated'
    item = Setting.query.filter_by(key=key).first()
    assert item.active == 'y'
    # add conversion type
    old_convert_type = Setting.convert_types
    Setting.convert_types = [{'type': int, 'method': lambda n: n * 2}]
    rv = client.put('/setting_update/{}'.format(item.id), json=dict(number=100))
    Setting.convert_types = old_convert_type
    assert rv.status_code == 200
    assert rv.data == b'Updated'
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
    assert 'created' not in rv.json
    assert 'updated' not in rv.json
    assert rv.status_code == 200
    assert 'created' not in item.as_dict
    assert 'updated' in item.as_dict


def test_get_delete_put_post(client):
    key = random_string()
    # create using post
    rv = client.post('/setting_post', data=dict(setting_type='test', key=key, value='test-value', number=10))
    assert rv.status_code == 200
    item = Setting.query.get_or_404(rv.json['id'])
    assert item
    assert rv.json['value'] == 'test-value'
    assert item.value == 'test-value'
    assert item.number == 0
    # update using post
    new_value = random_string()
    rv = client.post('/setting_post/{}'.format(item.id),
                     data=dict(setting_type='test', key=key, value=new_value, number=10))
    assert rv.status_code == 200
    assert rv.json['message'] == 'Updated'
    # test update_properties are returned
    assert rv.json['properties']['prop_test'] == 'prop:' + new_value
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == new_value
    assert item.number == 10
    # post item not found
    rv = client.post('/setting_post/{}'.format(random.randint(100, 999)),
                     data=dict(setting_type='test', key=key, value='new-value', number=10))
    assert rv.status_code == 404
    # post fail validation
    rv = client.post('/setting_post/{}'.format(item.id), data=dict(key=''))
    assert rv.status_code == 400
    assert rv.data == b'Missing key'
    # update using put
    new_value = random_string()
    new_number = random.randint(0, 999)
    rv = client.put('/setting_put/{}'.format(item.id),
                    json=dict(setting_type='test', key=key, value=new_value, number=new_number))
    assert rv.status_code == 200
    assert rv.json['message'] == 'Updated'
    assert rv.json['properties']['prop_test'] == 'prop:' + new_value
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == new_value
    assert item.number == new_number
    # put fail validation
    rv = client.put('/setting_put/{}'.format(item.id), data=dict(key=''))
    print(rv)
    assert rv.status_code == 400
    assert rv.data == b'Missing key'
    # create post fails
    rv = client.post('/setting_post', data=dict(flong='fling'))
    assert rv.status_code == 400
    assert rv.data == b'Missing key'


def test_create_update_json(client):
    # create
    key = random_string()
    value = random_string()
    rv = client.post('/setting_post', json=dict(setting_type='test', key=key, value=value, number=10))
    assert rv.status_code == 200
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == value
    value=random_string()
    rv = client.post(f'/setting_post/{item.id}', json=dict(setting_type='test', key=key, value=value, number=10))
    assert rv.status_code == 200
    item = Setting.query.filter_by(key=key).first()
    assert item
    assert item.value == value


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
    assert rv.data == b'Error updating item: Missing key'
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
    assert rv.data == b'Error creating item: create_fields is empty'
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
    assert rv.data == b'Error updating item: update_fields is empty'
    # json
    rv = client.put('/setting_update/{}'.format(item.id), json=dict(setting_type='test', key=key, value='test-value'))
    assert rv.status_code == 500
    assert rv.data == b'Error updating item: update_fields is empty'
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
    Setting.model_props = {}
    item = Setting(setting_type=setting_type, key=key, value=test_value)
    db.session.add(item)
    db.session.commit()
    item = Setting.query.get_or_404(item.id)
    # get by id
    rv = client.get('/setting_get_json/{}'.format(item.id))
    assert rv.json['value'] == test_value
    assert rv.json['key'] == key
    assert rv.json['setting_type'] == setting_type
    rv = client.get('/setting_get_json/{}'.format(item.id + 100))
    assert rv.status_code == 200
    assert rv.json == {}
    # get first
    rv = client.get('/setting_json_first/{}'.format(item.key))
    assert rv.json['value'] == test_value
    assert rv.json['key'] == key
    assert rv.json['setting_type'] == setting_type
    assert client.get('/setting_json_first/{}'.format(random_string())).json == {}


def test_get_0_is_not_null(client):
    key = random_string()
    item = Setting(id=0, setting_type='hello', value=random_string(), key=key)
    db.session.add(item)
    db.session.commit()
    # should get a list
    rv = client.get('/setting_get_all')
    assert rv.status_code == 200
    assert len(rv.json) == 1
    assert rv.json[0]['key'] == key
    # should get one item not a list
    rv = client.get('/setting_get/0')
    assert rv.status_code == 200
    assert rv.json['key'] == key


def test_timestamp_is_updated_and_can_be_overridden(client):
    key = random_string()
    item = Setting(setting_type='hello', value=random_string(), key=key)
    db.session.add(item)
    db.session.commit()
    new_value = random_string()
    item = Setting.query.get_or_404(item.id)
    sub_item = item.add_sub(new_value)
    sub_item_id = sub_item.id
    updated_when_created = sub_item.sub_updated
    # update using put
    new_value = random_string()
    assert 200 == client.put('/sub_setting_put/{}'.format(sub_item_id), json=dict(flong=new_value)).status_code
    updated_item = SubSetting.query.get_or_404(sub_item_id)
    assert updated_item.flong == new_value
    # test custom update works and that timestamp_fields works
    assert updated_when_created > updated_item.sub_updated
