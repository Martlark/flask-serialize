flask-serialize
===============

|PyPI Version|

DB Model JSON serialization and PUT/POST write for Flask applications using SQLAlchemy
=======================================================================================

Simple and quick to get going in two steps.
-------------------------------------------------

1. Import and add the FlaskSerializeMixin mixin to a model:
    
.. code:: python

    from flask-serialize import FlaskSerializeMixin

    class Item(db.Model, FlaskSerializeMixin):
        id = db.Column(db.Integer, primary_key=True)
        # other fields ...

2. Configure the route with the do all mixin method:

.. code:: python

    @app.route('/item/<int:item_id>')
    @app.route('/items')
    return Item.get_delete_put_post(item_id=None)

3. Done!  Returns a single item or a list of items in a single route.

Flask-serialize is intended for joining a Flask SQLAlchemy Python backend with
a JavaScript Web client.  It allows read JSON serialization
from the db and easy to use write back of models using PUT and POST.

It is not intended to be a full two way serialization package.  Use
`marshmallow` for more complicated systems.

Example:
========

Model setup:
------------

.. code:: python

    # example database model
    from flask_serialize import FlaskSerializeMixin

    # required to set class var db for writing to a database
    from app import db

    FlaskSerializeMixin.db = db

    class Setting(FlaskSerializeMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
    
        setting_type = db.Column(db.String(120), index=True, default='misc')
        key = db.Column(db.String(120), index=True)
        value = db.Column(db.String(30000), default='')
        active = db.Column(db.String(1), default='y')
        created = db.Column(db.DateTime, default=datetime.utcnow)
        updated = db.Column(db.DateTime, default=datetime.utcnow)
        
        # serializer fields
        create_fields = update_fields = ['setting_type', 'value', 'key', 'active']

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

Routes setup:
---------------

Get a single item as json.

.. code:: python

    @app.route('/get_setting/<item_id>', methods=['GET'])
    def get_setting( item_id ):
        return Setting.get_delete_put_post(item_id)

    Returns a Flask response with a json object, example:

.. code:: JavaScript

    {id:1, value: "hello"}

Put an update to a single item as json.

.. code:: python

    @app.route('/update_setting/<item_id>', methods=['PUT'])
    def update_setting( item_id ):
        return Setting.get_delete_put_post(item_id)

    Returns a Flask response with the result as a json object:

.. code:: JavaScript

    {error:"any error message", message: "success message"}


Delete a single item.

.. code:: python

    @app.route('/delete_setting/<item_id>', methods=['DELETE'])
    def delete_setting( item_id ):
        return Setting.get_delete_put_post(item_id)

    Returns a Flask response with the result as a json object:

.. code:: JavaScript

    {error:"any error message", message: "success message"}

Get all items as a json list.

.. code:: python

    @app.route('/get_setting_all', methods=['GET'])
    def get_setting_all():
        return Setting.get_delete_put_post()

    Returns a Flask response with a list of json objects, example:

.. code:: JavaScript

    [{id:1, value: "hello"},{id:2, value: "there"},{id:1, value: "programmer"}]

All of: get-all, get, put, post, and delete can be combined in one route.

.. code:: python

    @app.route('/setting/<int:item_id>', methods=['GET', 'PUT', 'DELETE', 'POST'])
    @app.route('/setting', methods=['GET', 'POST'])
    def route_setting_all(item_id=None):
        return Setting.get_delete_put_post(item_id)

Updating from a json object in the flask put request
    
JQuery example:

.. code:: javascript

    function put(setting_id) {
        return $.ajax({
            url: `/update_setting/${setting_id}`,
            method: 'PUT',
            contentType: "application/json",
            data: {setting_type:"x",value:"100"},
        }).then(response => {
            if( response.error ){
                alert("Error:"+response.error);
            }
            else {
                alert("OK:"+response.message);
            }
        });
    }

Flask route:  

.. code:: python

    @app.route('/update_setting/<int:item_id>', methods=['PUT'])
    def update_setting(item_id):
        return Setting.get_delete_put_post(item_id)

Create or update from a WTF form:

.. code:: python

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
                        flash('Your changes have been saved.')
                    except Exception as e:
                        flash(str(e), category='danger')
                    return redirect(url_for('setting_edit', item_id=item_id))
                else:
                    try:
                        new_item = Setting.request_create_form()
                        flash('Setting created.')
                        return redirect(url_for('setting_edit', item_id=new_item.id))
                    except Exception as e:
                        flash('Error creating item: ' + str(e))
                        
            return render_template(
                    'setting_edit.html',
                    item=item,
                    title='Edit or Create item',
                    form=form
                )

Options
=======

Exclude fields
--------------

List of model field names to not serialize at all.

.. code:: python

    exclude_serialize_fields = []
    
List of model field names to not serialize when return as json.

.. code:: python

    exclude_json_serialize_fields = []

Verify write and create
-----------------------

.. code:: python

    def verify(self, create=False):
        """
        raise exception if item is not valid for put/patch/post
        :param: create - True if verification is for a new item
        """

Override the mixin verify method to provide control and verification
when updating and creating model items.  Simply raise an exception
when there is a problem.  You can also modify `self` data before writing. See model example.

Controlling delete
------------------

.. code:: python

    def can_delete(self):
        """
        raise exception if item cannot be deleted
        """

Override the mixin can_delete to provide control over when an
item can be deleted.  Simply raise an exception
when there is a problem.  See model example.

Updating fields specification
-----------------------------

List of model fields to be read from a form or JSON when updating an object.  Normally
admin fields such as login_counts or security fields are excluded.

.. code:: python

    update_fields = []

Creation fields used when creating specification
------------------------------------------------

List of model fields to be read from a form when creating an object.

.. code:: python

    create_fields = []

Update date/time fields specification
-------------------------------------

List of fields on the model to be set when updating/creating 
with datetime.datetime.now()

Default is:

.. code:: python

    timestamp_fields = ['updated', 'timestamp']

Relationships list of property names that are to be included in serialization
-----------------------------------------------------------------------------

.. code:: python

    relationship_fields = []

In default operation relationships in models are not serialized.  Add any
relationship property name here to be included in serialization.

Serialization converters
------------------------
There are three built in converters to convert data from the database
to a good format for serialization:

* DATETIME - Removes the fractional second part and makes it a string
* PROPERTY - Enumerates and returns model added properties
* RELATIONSHIP - Deals with children model items.

Set one of these to None or a value to remove or replace it's behaviour.

Adding and overriding converter behaviour
-----------------------------------------

Add values to the class property:

.. code:: python

    column_type_converters = {}

Where the key is the column type name of the database column 
and the value is a method to provide the conversion.

Example:

To convert VARCHAR(100) to a string:

.. code:: python

    column_type_converters['VARCHAR(100)'] = lambda v: str(v)

To change DATETIME conversion behaviour, either change the DATETIME column_type_converter or
override the ``to_date_short`` method of the mixin.  Example:

.. code:: python

    import time

    class Model(db.model, FlaskSerializeMixin):
        # ...
        # ...
        def to_date_short(self, date_value):
            """
            convert a datetime.datetime type to
            a unix like milliseconds since epoch
            :param date_value: datetime.datetime {object}
            :return: number
            """
            if not date_value:
                return 0

            return int(time.mktime(date_value.timetuple())) * 1000


Conversion types (to database) add or replace update/create
-----------------------------------------------------------

Add or replace to db conversion methods by using a list of dicts that specify conversions.

Default is:

.. code:: python

    convert_types = [{'type': bool, 'method': lambda v: 'y' if v else 'n'}]

* type: a python object type  
* method: a lambda or method to provide the conversion to a database acceptable value.

Mixin Helper methods and properties
===================================

``get_delete_put_post()``

Put, get, delete, post and get-all magic method handler.
NOTE: renamed from ``get_delete_put()``.

====== ==============================================================================================================================
Method Operation
====== ==============================================================================================================================
GET    returns one item when `item_id` is a primary key
GET    returns all items when `item_id` is None
PUT    updates item using `item_id` as the id from request json data
DELETE removes the item with primary key of `item_id` if self.can_delete does not throw an error
POST   creates and returns a Flask response with a new item as json from form data when `item_id` is None
POST   updates an item from form data using `item_id`. Returns Flask response of {'message':'something', 'error':'any error message'}
====== ==============================================================================================================================

Set the `user` parameter to restrict a certain user.  Assumes that a model
relationship of user exists.

.. code:: python

    @property
    def get_delete_put_post(self, item_id=None, user=None):
        """
        get, delete or update with JSON a single model item
        post for form data
        :param item_id: the primary key id of the item - if none and method is get returns all items
        :param user: user to add as query item.
        :return: json object: {error, message}, or the item.  error == None for correct operation
        """

``as_dict``

.. code:: python

    @property
    def as_dict(self):
        """
        the sql object as a dict without the excluded fields
        :return: dict
        """

``as_json``

.. code:: python

    @property
    def as_json(self):
        """
        the sql object as a json object without the excluded dict and json fields
        :return: json object
        """

``dict_list()``

.. code:: python

    def dict_list(cls, query_result):
        """
        return a list of dictionary objects from the sql query result
        :param query_result: sql alchemy query result
        :return: list of dict objects
        """

``json_list()``

Return a flask response in json format from a sql alchemy query result.

.. code:: python

    @classmethod
    def json_list(cls, query_result):
        """
        return a list in json format from the query_result
        :param query_result: sql alchemy query result
        :return: flask response with json list of results
        """

Example:

.. code:: python

    @bp.route('/address/list', methods=['GET'])
    @login_required
    def address_list():
        items = Address.query.filter_by(user=current_user)
        return Address.json_list(items)

``json_filter_by()``

Return a flask response in json format using a filter_by query.

.. code:: python

    @classmethod
    def json_filter_by(cls, **kwargs):
        """
        return a list in json format using the filter_by arguments
        :param kwargs: SQLAlchemy query.filter_by arguments
        :return: flask response with json list of results
        """

Example:

.. code:: python

    @bp.route('/address/list', methods=['GET'])
    @login_required
    def address_list():
        return Address.filter_by(user=current_user)

``json_first``

.. code:: python

    def json_first(cls, **kwargs):
        """
        return the first result in json format using the filter_by arguments
        :param kwargs: SQLAlchemy query.filter_by arguments
        :return: flask response json item or {} if no result
        """

Licensing
---------

- Apache 2.0

.. |PyPI Version| image:: https://img.shields.io/pypi/v/flask-serialize.svg
   :target: https://pypi.python.org/pypi/flask-serialize

