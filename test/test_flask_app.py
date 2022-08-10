import os
import random
import string
import time
from datetime import datetime, timedelta

from flask import Flask, redirect, url_for, Response, request, render_template, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    IntegerField,
    ValidationError,
    validators,
    DecimalField,
    SubmitField,
)

from flask_serialize.flask_serialize import (
    FlaskSerialize,
    FlaskSerializeMixin,
)
from flask_serialize.form_page import FormPageMixin

app = Flask("test_app")
app.testing = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
FlaskSerializeMixin.db = db
fs_mixin = FlaskSerialize(db)

# =========================
# TINY TEST FLASK APP
# =========================


def random_string(length=20):
    """
    return a <length> long character random string of ascii_letters
    :param length: {int} number of characters to return
    :return:
    """
    return "".join(random.sample(string.ascii_letters, length))


class EditForm(FlaskForm):
    setting_type = StringField("setting_type", [validators.DataRequired()])
    key = StringField("key")
    value = StringField("value")
    number = IntegerField("number")
    deci = DecimalField("deci")
    j = StringField("j")
    submit = SubmitField()


@app.route("/")
@app.route("/<item_id>")
def page_index(item_id=None):
    settings = Setting.query.all()
    return render_template(
        "index.html",
        title="Flask Serialize Tester",
        settings=settings,
        key=random_string(),
        setting_type=random_string(),
        value=random_string(),
    )


# Get all items as a json list.
# post, put update
# and get single
@app.route("/setting_post", methods=["POST", "PUT"])
@app.route("/setting_post/<int:item_id>", methods=["POST"])
@app.route("/setting_get_all", methods=["GET"])
@app.route("/setting_post/<int:item_id>", methods=["POST"])
@app.route("/setting_put/<int:item_id>", methods=["PUT"])
@app.route("/setting_get/<int:item_id>", methods=["GET"])
@app.route("/setting_user/<user>", methods=["GET"])
@app.route("/setting_id_user/<int:item_id>/<user>", methods=["GET"])
def route_setting_fs_get_delete_put_post(item_id=None, user=None):
    key = request.args.get("key")
    if key and request.method == "GET":
        return Setting.fs_get_delete_put_post(item_id, prop_filters={"key": key})
    return Setting.fs_get_delete_put_post(item_id, user)


@app.route("/sub_setting_delete/<int:item_id>", methods=["DELETE"])
@app.route("/sub_setting_put/<int:item_id>", methods=["PUT", "POST"])
@app.route("/sub_setting_get/<int:item_id>", methods=["GET"])
def route_sub_setting_fs_get_delete_put_post(item_id=None, user="fake"):
    return SubSetting.fs_get_delete_put_post(item_id, user)


@app.route("/simple_add", methods=["POST"])
@app.route("/simple_edit/<int:item_id>", methods=["PUT", "POST"])
def route_simple_fs_get_delete_put_post(item_id=None, user=None):
    return SimpleModel.fs_get_delete_put_post(item_id, user)


@app.route("/setting_get_json/<int:item_id>", methods=["GET"])
def route_setting_get_json(item_id):
    return Setting.fs_json_get(item_id)


@app.route("/setting_fs_json_first/<key>", methods=["GET"])
def route_setting_fs_json_first(key):
    return Setting.fs_json_first(key=key)


@app.route("/setting_get_key/<key>", methods=["GET"])
def route_setting_get_key(key):
    """
    get the first item that matches by a setting key

    :param key:
    :return:
    """
    return Setting.query.filter_by(key=key).first().fs_as_json


@app.route("/setting_json_api/<int:id>", methods=["GET"])
def route_setting_get_json_api_key(id):
    """
    get the first item that matches by a setting key

    :param key:
    :return:
    """
    item = Setting.query.get(id)
    return item.json_api()


# Delete a single item.


@app.route("/setting_delete/<int:item_id>", methods=["DELETE"])
def route_setting_delete(item_id):
    return Setting.fs_get_delete_put_post(item_id)


@app.route("/setting_update/<int:item_id>", methods=["PUT"])
def route_setting_update(item_id):
    """
    update from a json object

    :param item_id: item to update
    :return:
    """
    item = Setting.query.get_or_404(item_id)
    try:
        item.fs_request_update_json()
    except Exception as e:
        print(e)
        return Response("PUT Error updating item: " + str(e), 500)
    return "Updated"


@app.route("/setting_update_post/<int:item_id>", methods=["PUT", "POST"])
def route_setting_update_post(item_id):
    """
    update from a json object

    :param item_id: item to update
    :return:
    """
    item = Setting.query.get_or_404(item_id)
    try:
        if not item.fs_request_update_form():
            return Response("update not allowed", 403)
    except Exception as e:
        print(e)
        return Response("POST Error updating item: " + str(e), 500)
    return "Updated"


@app.route("/sub_setting_add/<int:setting_id>", methods=["POST"])
def route_sub_setting_add(setting_id):
    """
    add as a child using kwargs on request create form

    :param setting_id:
    :return:
    """
    setting = Setting.query.get_or_404(setting_id)
    try:
        SubSetting.fs_request_create_form(setting_id=setting.id)
    except Exception as e:
        return str(e), 500
    return redirect(url_for("route_setting_edit_add", item_id=setting_id))


@app.route("/setting_edit/<int:item_id>", methods=["POST", "GET"])
@app.route("/setting_add", methods=["POST"])
def route_setting_edit_add(item_id=None):
    if item_id:
        item = Setting.query.get_or_404(item_id)
    else:
        item = {}
    form = EditForm(obj=item)

    if form.validate_on_submit():
        if item_id:
            try:
                item.fs_request_update_form()
            except Exception as e:
                print(e)
                return Response("Error updating item: " + str(e), 500)
            return redirect(url_for("route_setting_edit_add", item_id=item_id))
        else:
            try:
                Setting.fs_request_create_form()
                return redirect(url_for("page_index"))
            except Exception as e:
                print(e)
                return Response("Error creating item: " + str(e), 500)
    for err in form.errors:
        flash("**form error** {} {}".format(str(err), form.errors[err]))

    return render_template(
        "setting_edit.html", item=item, title="Edit Setting", form=form
    )


@app.route("/setting_form_edit/<int:item_id>", methods=["POST", "GET"])
@app.route("/setting_form_add", methods=["POST"])
def route_setting_form(item_id=None):
    new_item = Setting.form_page(item_id)
    return new_item


@app.route("/datetest", methods=["POST"])
@app.route("/datetest/<int:item_id>", methods=["PUT", "DELETE"])
def route_datetest(item_id=None):
    return DateTest.fs_get_delete_put_post(item_id)


@app.route("/badmodel", methods=["GET", "POST"])
@app.route("/badmodel/<int:item_id>", methods=["GET", "PUT", "DELETE"])
def route_badmodel(item_id=None):
    return BadModel.fs_get_delete_put_post(item_id)


@app.route("/user", methods=["GET", "POST"])
@app.route("/user/<int:item_id>", methods=["GET", "PUT", "DELETE"])
def route_user(item_id=None):
    return User.fs_get_delete_put_post(item_id)


@app.route("/user_add_data/<int:item_id>", methods=["POST"])
def route_user_add_data(item_id):
    value = request.form.get("data", "")
    user = User.query.get_or_404(item_id)
    user_data = UserData(user=user, value=value)
    db.session.add(user_data)
    db.session.commit()
    return user.fs_as_json


# =========================
# MODELS
# =========================


class SubSetting(fs_mixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    sub_updated = db.Column(db.DateTime, default=datetime.utcnow)

    setting_id = db.Column(db.Integer, db.ForeignKey("setting.id"))

    fake_user = db.Column(db.String(120), index=True, default="fake")
    flong = db.Column(db.String(120), index=True, default="flang")
    boolean = db.Column(db.Boolean, default=True)

    __fs_user_field__ = "fake_user"
    __fs_update_properties__ = __fs_create_fields__ = __fs_update_fields__ = [
        "flong",
        "boolean",
    ]
    __fs_convert_types__ = {
        str(bool): lambda v: (type(v) == bool and v) or str(v).lower() == "true"
    }

    @staticmethod
    def one_day_ago():
        return datetime.utcnow() - timedelta(days=1)

    def __fs_to_date_short__(self, date_value):
        """
        override DATETIME conversion behaviour to return unix time

        :param date_value:
        :return:
        """
        if not date_value:
            return 0

        return int(time.mktime(date_value.timetuple())) * 1000

    __fs_timestamp_fields__ = ["sub_updated"]
    __fs_timestamp_stamper__ = one_day_ago


class User(fs_mixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    data_items = db.relationship(
        "UserData", backref="user", cascade="all, delete-orphan"
    )

    __fs_relationship_fields__ = ["data_items"]


class UserData(fs_mixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(120), default="value")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))


class Single(fs_mixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wang = db.Column(db.String(120), default="wang")
    setting_id = db.Column(db.Integer, db.ForeignKey("setting.id"))


class DateTest(fs_mixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    a_date = db.Column(db.DateTime, default=datetime.utcnow)
    __fs_update_fields__ = __fs_create_fields__ = ["a_date"]


class Setting(FlaskSerializeMixin, FormPageMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    setting_type = db.Column(db.String(120), index=True, default="misc")
    key = db.Column(db.String(120), index=True)
    value = db.Column(db.String(3000), default="")
    number = db.Column(db.Integer, default=0)
    active = db.Column(db.String(1), default="y")
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(10), default="Andrew")
    floaty = db.Column(db.Float(), default=1.1)
    deci = db.Column(db.Numeric(2), default=0.0)
    # converter fields
    j = db.Column(db.JSON, default={"number_1": 1, "bool_true": True})
    lob = db.Column(db.LargeBinary())
    # relationships
    sub_settings = db.relationship(
        "SubSetting", backref="setting", cascade="all, delete-orphan"
    )
    single = db.relationship(
        "Single", backref="setting", uselist=False, cascade="all, delete-orphan"
    )

    # serializer fields
    __fs_update_fields__ = [
        setting_type,
        "value",
        "key",
        "active",
        "number",
        floaty,
        "scheduled",
        "deci",
        "lob",
        j,
    ]
    __fs_create_fields__ = [
        setting_type,
        "value",
        "key",
        "active",
        "user",
        "floaty",
        "number",
        "deci",
        "lob",
        j,
    ]

    __fs_exclude_serialize_fields__ = [created]
    __fs_exclude_json_serialize_fields__ = ["updated"]
    __fs_relationship_fields__ = [sub_settings, "single"]
    __fs_update_properties__ = ["prop_test"]
    __fs_order_by_field__ = "value"
    # lob
    __fs_column_type_converters__ = {"LOB": lambda v: str(v)}
    # convert types
    __fs_scheduled_date_format__ = "%Y-%m-%d %H:%M:%S"
    __fs_convert_types__ = {
        str(bool): lambda v: "y"
        if (type(v) == bool and v) or str(v).lower() == "true"
        else "n",
        str(int): lambda n: int(n) * 2,
        str(datetime): lambda n: datetime.strptime(
            n, Setting.__fs_scheduled_date_format__
        ),
    }
    # form_page
    form_page_form = EditForm
    form_page_route_update = "route_setting_form"
    form_page_route_create = "page_index"
    form_page_template = "setting_edit.html"
    form_page_new_title_format = "New Setting"

    @property
    def last_sub_setting(self):
        if len(self.sub_settings) > 0:
            return self.sub_settings[-1]
        else:
            return None

    def __fs_before_update__(self, data_dict):
        d = dict(data_dict)
        d["active"] = d.get("active", "n")
        return d

    def __fs_after_commit__(self, create=False):
        with open("after_commit.tmp", "w") as f:
            f.write(f""" __fs_after_commit__: {create} {self.id}""")

    # checks if Flask-Serialize can access
    def __fs_can_access__(self):
        if self.value == "123456789":
            return False
        return True

    # checks if Flask-Serialize can access
    def __fs_can_update__(self):
        if self.value == "9999":
            return False
        if not self.__fs_can_access__():
            raise Exception("Update not allowed.  Magic value!")
        return True

    # checks if Flask-Serialize can delete
    def __fs_can_delete__(self):
        if self.value == "1234":
            raise Exception("Deletion not allowed.  Magic value!")
        return True

    # checks if Flask-Serialize can create/update
    def __fs_verify__(self, create=False):
        if len(self.key or "") < 1:
            raise ValidationError("Missing key")

        if self.value == "666":
            raise ValidationError("Value is Devils Number")

        if len(self.setting_type or "") < 2:
            raise ValidationError("Insufficient setting type")

        if create:
            self.add_single("flang")

    def __fs_private_field__(self, field_name):
        if field_name.upper() == "KEY" and self.key == "private":
            return True
        return False

    @property
    def prop_test(self):
        return "prop:" + self.value

    @property
    def prop_complex(self):
        return complex(self.number, self.number * 2)

    @property
    def prop_error(self):
        return "prop:" + str(1 / 0)

    @property
    def prop_test_dict(self):
        return {"prop": self.value}

    @property
    def prop_datetime(self):
        return self.created

    @property
    def prop_set(self):
        return set([1, 2, 3, "four"])

    def add_sub(self, flong):
        sub = SubSetting(setting=self, flong=flong)
        db.session.add(sub)
        db.session.commit()
        return sub

    def add_single(self, flong):
        sing = Single(setting=self, wang=flong)
        db.session.add(sing)
        return sing

    def __repr__(self):
        return "Setting {}".format(self.key)


class SimpleModel(fs_mixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(30), default="")

    @property
    def prop(self):
        return "prop:" + self.value

    def __repr__(self):
        return "<SimpleModel %r>" % (self.value)


class BadModel(fs_mixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(30), default="")
    __fs_column_type_converters__ = {"VARCHAR": lambda x: x / 0}

    def __repr__(self):
        return "<BadModel %r>" % (self.value)


if __name__ == "__main__":
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "Testing"
    app.config["WTF_CSRF_ENABLED"] = False
    db.create_all()
    app.run(debug=True, port=5055)
