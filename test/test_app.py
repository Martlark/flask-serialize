import json
import random
import string
import time
from http import HTTPStatus
from datetime import datetime
from pathlib import Path
from sqlalchemy import text, exc
from sqlalchemy.exc import OperationalError

import flask_unittest


from test.test_flask_app import app, db, Setting, SubSetting, SimpleModel, DateTest


def random_string(length=20):
    """
    return a <length> long character random string of ascii_letters
    :param length: {int} number of characters to return
    :return:
    """
    return "".join(random.sample(string.ascii_letters, length))


# =========================
# TESTS
# =========================


class TestBase(flask_unittest.AppClientTestCase):
    def setUp(self, app, client) -> None:
        """
        setup common reports and database connections

        :param app:
        :param client:
        :return:
        """
        with app.app_context():
            db.drop_all()
            db.create_all()

    def create_app(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "Testing"
        app.config["WTF_CSRF_ENABLED"] = False
        app.testing = True
        yield app

    def tearDown(self, app, client):
        db.session.execute(text("drop table if exists test_table"))
        db.session.remove()


class TestAll(TestBase):
    def add_setting(self, client, key=random_string(), value="test-value", number=0):
        rv = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=key, value=value, number=number),
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        assert item
        return item

    def test__fs_order_by_field__(self, app, client):
        # add plenty
        count = 10
        for z in range(count):
            self.add_setting(client, key=str(z), value=str(z + 1))

        Setting.__fs_order_by_field__ = "id"
        rv = client.get("/setting_get_all")
        assert rv.status_code == 200
        json_settings = rv.json
        assert len(json_settings) == count
        sorted_list = sorted(json_settings, key=lambda i: i["id"])
        for z in range(count):
            assert json_settings[z]["id"] == sorted_list[z]["id"]
        # ascending.
        Setting.__fs_order_by_field__ = "value"
        rv = client.get("/setting_get_all")
        json_settings = rv.json
        sorted_list = sorted(json_settings, key=lambda i: i["value"])
        for z in range(count):
            assert json_settings[z]["value"] == sorted_list[z]["value"]
        Setting.__fs_order_by_field__ = None
        Setting.__fs_order_by_field_desc__ = "value"
        # descending
        rv = client.get("/setting_get_all")
        json_settings = rv.json
        sorted_list = sorted(json_settings, key=lambda i: i["value"], reverse=True)
        for z in range(count):
            assert json_settings[z]["value"] == sorted_list[z]["value"]

    def test_get_filter(self, app, client):
        key_1 = random_string()
        key_2 = random_string()
        # test add
        self.add_setting(client, key=key_1)
        self.add_setting(client, key=key_2)
        rv = client.get("/setting_get_all")
        assert rv.status_code == 200
        assert len(rv.json) == 2
        rv = client.get(f"/setting_get_all?key={key_1}")
        assert rv.json[0]["key"] == key_1
        assert len(rv.json) == 1
        rv = client.get(f"/setting_get_all?key={key_2}")
        assert len(rv.json) == 1
        assert rv.json[0]["key"] == key_2

    def test_get_all(self, app, client):
        rv = client.get("/setting_get_all")
        assert rv.status_code == 200
        assert len(rv.json) == 0
        key = random_string()
        # test add
        item = self.add_setting(client, key=key)
        rv = client.get("/setting_get_all")
        assert rv.status_code == 200
        assert len(rv.json) == 1
        assert rv.json[0]["key"] == key
        with app.app_context():
            # filter by
            rv = Setting.fs_json_filter_by(key=key)
            assert rv.json[0]["key"] == key
        # all as dict list
        result = Setting.query.all()
        fs_dict_list = Setting.fs_dict_list(result)
        assert len(fs_dict_list) == 1
        assert fs_dict_list[0]["key"] == key

    def test_get_user(self, app, client):
        key = random_string()
        # test add 2 settings
        client.post(
            "/setting_add", data=dict(setting_type="test", key=key, value="test-value")
        )
        test_user_name = random_string()
        client.post(
            "/setting_add",
            data=dict(
                setting_type="test", key=key, value="test-value", user=test_user_name
            ),
        )
        rv = client.get("/setting_user/{}".format(test_user_name))
        assert len(rv.json) == 1
        item = rv.json[0]
        assert item["user"] == test_user_name
        item_id = item["id"]
        rv = client.get("/setting_id_user/{}/{}".format(item_id, test_user_name))
        assert rv.json["user"] == test_user_name
        # should not be found
        rv = client.get("/setting_id_user/{}/{}".format(item_id, random_string()))
        assert rv.status_code == 404
        # get all by user
        rv = client.get("/setting_user/{}".format("no-one"))
        assert len(rv.json) == 0
        user_404 = None
        try:
            user_404 = Setting.fs_get_by_user_or_404(item_id, user="not-here")
        except Exception as e:
            assert "404 Not Found:" in str(e)
        assert user_404 is None
        #
        rv = client.put(f"/setting_update/{item_id}", data=dict(value="123456789"))
        assert 200 == rv.status_code
        try:
            user_404 = Setting.fs_get_by_user_or_404(
                item_id=item_id, user=test_user_name
            )
        except Exception as e:
            assert "404 Not Found:" in str(e)
        assert user_404 is None
        rv = client.get("/setting_get/{}".format(item_id))
        assert 403 == rv.status_code

    def test_get_property(self, app, client):
        key = random_string()
        test_value = random_string()
        flong_value = random_string()
        # test add a thing
        self.add_setting(client, key=key, value=test_value, number=2)
        setting = Setting.query.filter_by(key=key).first()
        self.assertIsNotNone(setting)
        setting.add_sub(flong_value)
        setting_created = setting.created
        setting_number = setting.number

        rv = client.get("/setting_get_key/{}".format(key))
        assert rv.status_code == 200
        assert rv.json["prop_test"] == "prop:" + test_value

        assert rv.json["prop_datetime"] == str(setting_created).split(".")[0]
        assert rv.json["prop_test_dict"] == {"prop": test_value}
        assert rv.json["prop_complex"] == str(
            complex(setting_number, setting_number * 2)
        )
        assert set(rv.json["prop_set"]) == set([3, 1, 2, "four"])
        assert rv.json["last_sub_setting"]["flong"] == flong_value

    def test_relationships(self, app, client):
        key = random_string()
        # test add
        rv = client.post(
            "/setting_add", data=dict(setting_type="test", key=key, value="test-value")
        )
        # add relation
        setting = Setting.query.filter_by(setting_type="test").first()
        client.post(
            f"/sub_setting_add/{setting.id}", data=dict(flong="blong", setting=setting)
        )
        # see if returned
        rv = client.get("/setting_get_all")
        assert rv.status_code == 200
        assert len(rv.json) == 1
        assert len(rv.json[0]["sub_settings"]) == 1
        assert rv.json[0]["sub_settings"][0]["flong"] == "blong"

    def test_prop_filters(self, app, client):
        # test add
        filter_key = random_string()
        for _ in range(10):
            client.post(
                "/setting_add",
                data=dict(
                    setting_type="test", key=random_string(), value=random_string()
                ),
            )

        client.post(
            "/setting_add",
            data=dict(setting_type="test", key=filter_key, value=random_string()),
        )
        rv = client.get(f"/setting_get_all?key={filter_key}")
        assert 200 == rv.status_code
        assert 1 == len(rv.json)
        assert filter_key == rv.json[0]["key"]

    def test_private_field(self, app, client):
        # create
        excluded_key = "private"
        value = "123789"
        rv = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=excluded_key, value=value),
        )

        # value is excluded from dict list
        query = Setting.query.filter_by(setting_type="test")
        items = Setting.fs_dict_list(query)
        assert "key" not in items[0]

    def test__fs_can_access___update(self, app, client):
        # create
        excluded_key = random_string()
        value = "123456789"
        rv = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=excluded_key, value=value),
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=excluded_key).first()
        excluded_id = item.id
        key = random_string()
        value = random_string()
        client.post(
            "/setting_add",
            data=dict(setting_type="test", key=key, value=value, user="Robert"),
        )
        key = random_string()
        value = random_string()
        client.post(
            "/setting_add", data=dict(setting_type="test", key=key, value=value)
        )

        # one value is excluded
        with app.app_context():
            r = Setting.fs_json_first(key=excluded_key)
            assert r.status_code == 200
            assert r.response == [b"{}\n"]
        # value is excluded from dict list
        query = Setting.query.filter_by(setting_type="test")
        items = Setting.fs_dict_list(query)
        assert len(items) == 2
        with app.app_context():
            r = Setting.fs_json_list(query)
            l = json.loads(r.response[0])
            assert len(l) == 2
        # try to update
        rv = client.put(
            "/setting_update/{}".format(excluded_id), json=dict(active=False)
        )
        assert rv.status_code != 200
        assert b"PUT Error updating item: Update not allowed.  Magic value!" == rv.data

        result_list = Setting.fs_query_by_access(setting_type="test")
        assert len(result_list) == 2
        result_list = Setting.fs_query_by_access(user="Andrew", setting_type="test")
        assert len(result_list) == 1  # no robert

    def test__can_update_returns_false(self, app, client):
        # test return False
        excluded_key = random_string()
        value = "9999"
        rv = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=excluded_key, value=value),
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=excluded_key).first()
        rv = client.post(f"/setting_update_post/{item.id}", data=dict(active=False))
        assert 403 == rv.status_code

        rv = client.post(f"/setting_post/{item.id}", data=dict(active=False))
        assert 403 == rv.status_code, rv.data

    def test__fs_can_delete__(self, app, client):
        # create
        key = random_string()
        value = "1234"
        rv = client.post(
            "/setting_add", data=dict(setting_type="test", key=key, value=value)
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert item.value == value
        rv = client.delete("/setting_delete/{}".format(item.id))
        assert rv.status_code == 400
        assert rv.data == b"Deletion not allowed.  Magic value!"

    def test_column_conversion(self, app, client):
        # create
        key = random_string()
        value = "12.34"
        j_value = dict(a=123, b=True)
        rv = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=key, lob=value, j=json.dumps(j_value)),
        )
        # get
        item = Setting.query.filter_by(key=key).first()
        assert item.fs_as_dict["lob"] == value
        self.assertEqual(j_value, item.fs_as_dict["j"], item.fs_as_dict)

    def test_update_create_type_conversion(self, app, client):
        # create
        key = random_string()
        value = "1234"
        rv = client.post(
            "/setting_add", data=dict(setting_type="test", key=key, value=value)
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        assert item
        # default bool type conversion
        # json
        rv = client.put("/setting_update/{}".format(item.id), json=dict(active=False))
        assert rv.status_code == 200, rv.data
        assert b"Updated" == rv.data, rv.data
        item = Setting.query.filter_by(key=key).first()
        assert "n" == item.active, item
        # query parameters as strings so bool converter does not work
        rv = client.put(
            "/setting_update/{}".format(item.id), query_string=dict(active="y")
        )
        assert rv.status_code == 200
        assert rv.data == b"Updated"

        item = Setting.query.filter_by(key=key).first()
        assert "y" == item.active
        flong = random_string()
        rv = client.post("/sub_setting_add/{}".format(item.id), data=dict(flong=flong))
        item = SubSetting.query.filter_by(flong=flong).first()
        ss_id = item.id
        ss = client.get("/sub_setting_get/{}".format(ss_id))
        assert ss.json["id"] == ss_id
        # bool type conversion
        for new_boolean in [True, False]:
            rv = client.put(
                "/sub_setting_put/{}".format(ss_id), json=dict(boolean=new_boolean)
            )
            assert 200 == rv.status_code, rv
            ss = SubSetting.query.get_or_404(ss_id)
            assert new_boolean == ss.boolean

    def test_bad_convert_type(self, app, client):
        value = random_string()
        rv = client.post(
            "/badmodel",
            data=dict(value=value),
        )
        assert 200 == rv.status_code
        assert "Failed to convert [value]" in rv.data.decode("utf-8"), rv

    def test_convert_type(self, app, client):
        # add conversion type
        key = random_string()
        value = random_string()
        response = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=key, value=value, floaty=123.456),
        )
        self.assertEqual(HTTPStatus.FOUND, response.status_code, response)
        item = Setting.query.filter_by(key=key).first()

        float_value_to_convert = 23.4
        int_value_to_convert = 45
        convert_multiple = 2
        rv = client.put(
            "/setting_update/{}".format(item.id),
            json=dict(number=int_value_to_convert, floaty=float_value_to_convert),
        )
        assert rv.status_code == 200
        assert rv.data == b"Updated"
        item = Setting.query.filter_by(key=key).first()
        # explicit double conversion type
        assert int_value_to_convert * convert_multiple == item.number

    def test_sqlite_datetime_convert_type(self, app, client):
        # test sqlite conversion types
        date_value = "2004-05-23"
        rv = client.post("/datetest", data=dict(a_date=date_value))
        assert rv.status_code == 200, rv.data
        item = DateTest.query.first()
        assert item.a_date == datetime.strptime(date_value, "%Y-%m-%d")
        date_value = "2010-05-23"
        rv = client.put("/datetest/{}".format(item.id), json=dict(a_date=date_value))
        assert rv.status_code == 200, rv.data
        item = DateTest.query.first()
        # explicit double conversion type
        assert item.a_date == datetime.strptime(date_value, "%Y-%m-%d")

    def test_excluded(self, app, client):
        # create
        key = random_string()
        value = "1234"
        rv = client.post(
            "/setting_add", data=dict(setting_type="test", key=key, value=value)
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        # test non-serialize fields excluded
        rv = client.get("/setting_get/{}".format(item.id))
        assert "created" not in rv.json
        assert "updated" not in rv.json
        assert rv.status_code == 200
        assert "created" not in item.fs_as_dict
        assert "updated" in item.fs_as_dict

    def test__fs_before_update__(self, app, client):
        key = random_string()
        test_value = random_string()
        # create using post
        rv = client.post(
            "/setting_post",
            data=dict(setting_type="test", key=key, value=test_value, number=10),
        )
        assert rv.status_code == 200
        item = Setting.query.get_or_404(rv.json["id"])
        assert item
        assert rv.json["value"] == test_value
        assert item.value == test_value
        assert item.number == 20
        # update using post - missing active should become 'n' via __fs_before_update__ hook
        new_value = random_string()
        rv = client.post(
            "/setting_post/{}".format(item.id),
            data=dict(setting_type="test", key=key, value=new_value, number=10),
        )
        assert rv.status_code == 200
        assert rv.json["message"] == "Updated"
        item = Setting.query.get_or_404(item.id)
        assert "n" == item.active

    def test_fs_get_delete_put_post(self, app, client):
        key = random_string()
        # create using post
        rv = client.post(
            "/setting_post",
            data=dict(setting_type="test", key=key, value="test-value", number=10),
        )
        assert rv.status_code == 200
        item = Setting.query.get_or_404(rv.json["id"])
        assert item
        assert rv.json["value"] == "test-value"
        assert item.value == "test-value"
        assert item.number == 20
        # update using post
        new_value = random_string()
        rv = client.post(
            "/setting_post/{}".format(item.id),
            data=dict(setting_type="test", key=key, value=new_value, number=10),
        )
        assert rv.status_code == 200
        assert rv.json["message"] == "Updated"
        # test __fs_update_properties__ are returned
        assert rv.json["properties"]["prop_test"] == "prop:" + new_value
        assert rv.json["item"]["key"] == key
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert item.value == new_value
        assert 20 == item.number
        # post item not found
        rv = client.post(
            "/setting_post/{}".format(random.randint(100, 999)),
            data=dict(setting_type="test", key=key, value="new-value", number=10),
        )
        assert 404 == rv.status_code
        # put not valid in something meant for post
        rv = client.put("/setting_post")
        assert 405 == rv.status_code
        # post fail validation
        rv = client.post("/setting_post/{}".format(item.id), data=dict(key=""))
        assert 400 == rv.status_code
        assert rv.data == b"Missing key"
        # update using put
        new_value = random_string()
        new_number = random.randint(0, 999)
        rv = client.put(
            "/setting_put/{}".format(item.id),
            json=dict(setting_type="test", key=key, value=new_value, number=new_number),
        )
        assert rv.status_code == 200
        assert rv.json["message"] == "Updated"
        assert rv.json["properties"]["prop_test"] == "prop:" + new_value
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert item.value == new_value
        assert item.number == new_number * 2
        # put fail validation
        rv = client.put("/setting_put/{}".format(item.id), data=dict(key=""))
        print(rv)
        assert rv.status_code == 400
        assert rv.data == b"Missing key"
        # create post fails
        rv = client.post("/setting_post", data=dict(flong="fling"))
        assert rv.status_code == 400
        assert rv.data == b"Missing key"

    def test_create_update_json(self, app, client):
        # create
        key = random_string()
        value = random_string()
        rv = client.post(
            "/setting_post",
            json=dict(setting_type="test", key=key, value=value, number=10),
        )
        assert rv.status_code == 200
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert item.value == value
        value = random_string()
        dt_now = datetime.utcnow()
        rv = client.post(
            f"/setting_post/{item.id}",
            json=dict(
                setting_type="test",
                key=key,
                value=value,
                number=10,
                scheduled=dt_now.strftime(Setting.__fs_scheduled_date_format__),
            ),
        )
        assert rv.status_code == 200, rv.data
        after_commit = Path("after_commit.tmp").read_text()
        assert after_commit == f""" __fs_after_commit__: {False} {item.id}"""
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert item.value == value
        assert item.scheduled.strftime(
            Setting.__fs_scheduled_date_format__
        ) == dt_now.strftime(Setting.__fs_scheduled_date_format__)

    def test_create_update_delete(self, app, client):
        # create
        key = random_string()
        value = random_string()
        rv = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=key, value=value, number=10),
        )
        assert rv.status_code == 302, rv.data
        item = Setting.query.filter_by(key=key).first()
        after_commit = Path("after_commit.tmp").read_text()
        assert after_commit.startswith(f""" __fs_after_commit__: {True} {item.id}""")
        assert item
        assert item.value == value
        # test that number is not set on creation as it is not included in __fs_create_fields__
        assert item.number == 20
        old_updated = item.updated

        new_value = random_string()
        item.fs_update_from_dict(dict(value=new_value))
        assert item.__fs_previous_field_value__["value"] == value
        assert item.value == new_value
        # set to new value
        new_value = random_string()
        rv = client.post(
            "/setting_edit/{}".format(item.id), data=dict(value=new_value, number=100)
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert item.value == new_value
        assert item.number == 200
        # check updated is changing
        assert old_updated != item.updated
        # set to ''
        rv = client.post("/setting_edit/{}".format(item.id), data=dict(value=""))
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert not item.value
        # fail validation
        rv = client.post("/setting_edit/{}".format(item.id), data=dict(key=""))
        assert rv.status_code == 500
        assert b"Error updating item: Missing key" in rv.data
        # delete
        rv = client.delete("/setting_delete/{}".format(item.id))
        assert rv.status_code == 200
        assert rv.json["item"]["id"] == item.id
        item = Setting.query.filter_by(key=key).first()
        assert not item

    def test_no_db(self, app, client):
        # create
        old_db = Setting.db
        date_value = "2004-05-23"
        DateTest.db = None
        rv = client.post("/datetest", data=dict(a_date=date_value))
        DateTest.db = old_db
        assert rv.status_code == 400, rv.data
        assert 'FlaskSerializeMixin property "db" is not set' in rv.data.decode("utf-8")
        rv = client.post("/datetest", data=dict(a_date=date_value))
        new_id = rv.json["id"]
        DateTest.db = None
        rv = client.put(f"/datetest/{new_id}", data=dict(a_date=date_value))
        assert 'FlaskSerializeMixin property "db" is not set' in rv.data.decode("utf-8")
        rv = client.delete(f"/datetest/{new_id}", data=dict(a_date=date_value))
        assert 'FlaskSerializeMixin property "db" is not set' in rv.data.decode("utf-8")
        DateTest.db = old_db

    def test_form_page(self, app, client):
        # create
        key = random_string()
        rv = client.post(
            "/setting_form_add",
            data=dict(setting_type="test", key=key, value="test-value", number=10),
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        after_commit = Path("after_commit.tmp").read_text()
        assert after_commit.startswith(f""" __fs_after_commit__: {True} {item.id}""")
        assert item
        assert item.value == "test-value"
        # test that number is not set on creation as it is not included in __fs_create_fields__
        assert item.number == 20
        # set to new value
        new_value = random_string()
        rv = client.post(
            "/setting_form_edit/{}".format(item.id),
            data=dict(
                id=item.id, setting_type="test", key=key, value=new_value, number=100
            ),
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first()
        assert item
        assert item.value == new_value
        assert item.number == 200
        # set to ''
        rv = client.post(
            "/setting_form_edit/{}".format(item.id),
            data=dict(id=item.id, setting_type="test", key=key, value=""),
        )
        assert rv.status_code == 302
        item = Setting.query.filter_by(key=key).first_or_404()
        assert not item.value
        # fail validation
        rv = client.post(
            "/setting_form_edit/{}".format(item.id),
            data=dict(id=item.id, setting_type="test", key=""),
        )
        assert rv.status_code == 200
        assert b"Missing key" in rv.data

    def test_default__fs_create_fields__(self, app, client):
        key = random_string()
        value = random_string()
        prop_test = random_string()
        # add
        old___fs_create_fields__ = Setting.__fs_create_fields__
        # remove fields
        Setting.__fs_create_fields__ = []
        rv = client.post(
            "/setting_add",
            data=dict(setting_type="test", key=key, value=value, prop_test=prop_test),
        )
        assert 302 == rv.status_code, rv.data
        # assert it was created
        item = Setting.query.filter_by(key=key).first()
        assert item.key == key, item
        assert item.value == value, item
        assert item.prop_test == "prop:" + value, item
        Setting.__fs_create_fields__ = old___fs_create_fields__

    def test_simple_model__fs_update_fields__(self, app, client):
        value = random_string()
        # add
        with app.app_context():
            item = SimpleModel(value=value)
            db.session.add(item)
            db.session.commit()
            item = SimpleModel.query.filter_by(value=value).first_or_404()
            # form
            value = random_string()
            prop = random_string()
            rv = client.post(
                "/simple_edit/{}".format(item.id), data=dict(value=value, prop=prop)
            )
            assert 200 == rv.status_code, rv.data
            assert rv.json["item"]["value"] == value, rv.data
            assert b"Updated" in rv.data, rv.data
            # json
            value = random_string()
            rv = client.put(
                "/simple_edit/{}".format(item.id), json=dict(value=value, id="dskdsf")
            )
            assert 200 == rv.status_code, rv.data
            assert rv.json["item"]["value"] == value, rv.data
            assert rv.json["item"]["prop"] == "prop:" + value, rv.data
            assert b"Updated" in rv.data, rv.data

    def test_override_datetime_conversion(self, app, client):
        key = random_string()
        test_value = random_string()
        # test add a thing
        item = self.add_setting(client, key=key, value=test_value)
        sub_setting = SubSetting(setting=item, flong=random_string(5))
        db.session.add(sub_setting)
        db.session.commit()
        item = Setting.query.filter_by(key=key).first()
        sub = item.sub_settings[0]
        unix_time = int(time.mktime(sub.created.timetuple())) * 1000
        assert type(sub.fs_as_dict["created"]) == int
        assert sub.fs_as_dict["created"] == unix_time

    def test_fs_json_get(self, app, client):
        key = random_string()
        test_value = random_string()
        setting_type = random_string()
        # test add setting
        Setting.__model_props = {}
        with app.app_context():
            item = Setting(setting_type=setting_type, key=key, value=test_value)
            db.session.add(item)
            db.session.commit()
            item = Setting.query.get_or_404(item.id)
            # get by id
            rv = client.get("/setting_get_json/{}".format(item.id))
            assert rv.json["value"] == test_value
            assert rv.json["key"] == key
            assert rv.json["setting_type"] == setting_type
            rv = client.get("/setting_get_json/{}".format(item.id + 100))
            assert rv.status_code == 200
            assert rv.json == {}
            # get first
            rv = client.get("/setting_fs_json_first/{}".format(item.key))
            assert rv.json["value"] == test_value
            assert rv.json["key"] == key
            assert rv.json["setting_type"] == setting_type
            assert (
                client.get("/setting_fs_json_first/{}".format(random_string())).json
                == {}
            )

    def test_get_0_is_not_null(self, app, client):
        key = random_string()
        with app.app_context():
            item = Setting(id=0, setting_type="hello", value=random_string(), key=key)
            db.session.add(item)
            db.session.commit()
            # should get a list
            rv = client.get("/setting_get_all")
            assert rv.status_code == 200
            assert len(rv.json) == 1
            assert rv.json[0]["key"] == key
            # should get one item not a list
            rv = client.get("/setting_get/0")
            assert rv.status_code == 200
            assert rv.json["key"] == key

    def test_timestamp_is_updated_and_can_be_overridden(self, app, client):
        key = random_string()
        with app.app_context():
            item = Setting(setting_type="hello", value=random_string(), key=key)
            db.session.add(item)
            db.session.commit()
            new_value = random_string()
            item = Setting.query.get_or_404(item.id)
            sub_item = item.add_sub(new_value)
            sub_item_id = sub_item.id
            updated_when_created = sub_item.sub_updated
            # update using put
            new_value = random_string()
            assert (
                200
                == client.put(
                    "/sub_setting_put/{}".format(sub_item_id),
                    json=dict(flong=new_value),
                ).status_code
            )
            updated_item = SubSetting.query.get_or_404(sub_item_id)
            assert updated_item.flong == new_value
            # test custom update works and that __fs_timestamp_fields__ works
            assert updated_when_created > updated_item.sub_updated

    def test_user(self, app, client):
        test_value = random_string()
        user_name = random_string()
        # test add user
        # get by id
        rv = client.post("/user", data={"name": user_name})
        assert rv.json["name"] == user_name
        user_id = rv.json["id"]
        # add data
        rv = client.post(f"/user_add_data/{user_id}", data={"data": test_value})
        assert rv.json["name"] == user_name
        assert test_value in [item.get("value") for item in rv.json["data_items"]]
