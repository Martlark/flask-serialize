flask-serialize
===============

|PyPI Version|

DB Model JSON serialization with PUT, POST write for Flask applications using SQLAlchemy
========================================================================================

Installation
------------

.. code:: bash

    pip install flask-serialize

Simple and quick to get going in two steps.
-------------------------------------------------

.1. Import and add the FlaskSerializeMixin mixin to a model:
    
.. code:: python

    from flask_serialize import FlaskSerializeMixin

    class Item(db.Model, FlaskSerializeMixin):
        id = db.Column(db.Integer, primary_key=True)
        # other fields ...

.2. Configure the route with the do all mixin method:

.. code:: python

    @app.route('/item/<int:item_id>')
    @app.route('/items')
    def items(item_id=None):
        return Item.get_delete_put_post(item_id)

.3. Done!  Returns JSON as a single item or a list with only a single route.

Flask-serialize is intended for joining a Flask SQLAlchemy Python backend with
a JavaScript Web client.  It allows read JSON serialization
from the db and easy to use write back of models using PUT and POST.

4 times faster than marshmallow for simple dict serialization.

It is not suitable for two way serialization.  Use
`marshmallow` or similar for more complicated systems.

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
            if len(self.key or '') < 1:
                raise Exception('Missing key')
    
            if len(self.setting_type or '') < 1:
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

    {message: "success message"}


Delete a single item.

.. code:: python

    @app.route('/delete_setting/<item_id>', methods=['DELETE'])
    def delete_setting( item_id ):
        return Setting.get_delete_put_post(item_id)

    Returns a Flask response with the result and item deleted as a json response:

.. code:: JavaScript

    {message: "success message", item: {"id":5, name: "gone"}}

Get all items as a json list.

.. code:: python

    @app.route('/get_setting_all', methods=['GET'])
    def get_setting_all():
        return Setting.get_delete_put_post()

    Returns a Flask response with a list of json objects, example:

.. code:: JavaScript

    [{id:1, value: "hello"},{id:2, value: "there"},{id:3, value: "programmer"}]

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
                alert("OK:"+response.message);
            }).fail((xhr, textStatus, errorThrown) => {
                alert(`Error: ${xhr.responseText}`);
            });
        }
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


Create a child database object:

As example: add a `Stat` object to a Survey object using the `request_create_form` convenience method.  The foreign key
to the parent `Survey` is provided as a `kwargs` parameter to the method.

.. code:: python

        @app.route('/stat/<int:survey_id>', methods=['POST'])
        def stat_add(survey_id=None):
            survey = Survey.query.get_or_404(survey_id)
            return Stat.request_create_form(survey_id=survey.id).as_dict

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
admin fields such as login_counts or security fields are excluded.  Do not put foreign keys or primary
keys here.

.. code:: python

    update_fields = []

Update Properties
-----------------

When returning a success code from a put or post update a dict
composed of the property values from the update_properties list is returned
as "properties".

.. code:: python

    update_properties = []

Example return JSON:

.. code:: python

    class ExampleModel(db.Model, FlaskSerializeMixin):
        update_fields = ['hat_size']

        @property
        def hat_size(self):
            return self.head_size * self.ear_width

.. code:: JavaScript

    // result update return message
    {message: "Updated", properties: {new_hat_size: 45.67} }

This can be used to communicate from the model on the server to the JavaScript code
interesting things from updates

Creation fields used when creating specification
------------------------------------------------

List of model fields to be read from a form or json when creating an object.  Do not put foreign keys or primary
keys here.

.. code:: python

    create_fields = []

Filtering json list results
---------------------------

Json result lists can be filtered by using the `prop_filters` on either
the `get_delete_put_post` method or the `json_list` method.

The filter consists of one or more properties in the json result and
the value that it must match.  Filter items will match against the
first prop_filter property to exactly equal the value.

Example:

.. code:: python

    result = get_delete_put_post(prop_filters = {'key':'dogs'})

Sorting json list results
-------------------------

Json result lists can be sorted by using the `order_by_field` or the `order_by_field_desc` properties.  To sort by id
ascending use this example:

.. code:: python

    order_by_field = 'id'

Update DateTime fields specification
-------------------------------------

`timestamp_fields` is a list of fields on the model to be set when updating or creating
with the value of `datetime.datetime.utcnow()`.  The default field names to update are: `['timestamp', 'updated']`.

Example:

.. code:: python


    class ExampleModel(db.Model, FlaskSerializeMixin):
        # ....
        modified = db.Column(db.DateTime, default=datetime.utcnow)
        timestamp_fields = ['modified']

Override the timestamp default of `utcnow()` by replacing the `timestamp_stamper` class property with your
own.  Example:

.. code:: python

    class ExampleModel(db.Model, FlaskSerializeMixin):
        # ....
        timestamp_stamper = datetime.datetime.now

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


Conversion types when writing to database during update and create
------------------------------------------------------------------

Add or replace to db conversion methods by using a list of dicts that specify conversions.

Default is:

.. code:: python

    convert_types = [{'type': bool, 'method': lambda v: 'y' if v else 'n'}]

* type: a python object type  
* method: a lambda or method to provide the conversion to a database acceptable value.

First the correct conversion will be attempted to be determined from the type of the updated or
new field value.  Then, an introspection from the destination column type will be used to get the
correct value converter type.

Notes:

* The order of convert types will have an effect. For example Python boolean type is derived from an int.  Make sure
  boolean appears in the list before any int convert type.

* To undertake a more specific column conversion use the `verify` method to explicitly set the class instance value.  The
  `verify` method is always called before a create or update to the database.

* When converting values from query strings or form values the type will always be `str`.

* To add or modify values from a Flask request object before they are applied to the instance use the ``before_update`` hook.
  ``verify`` is called after ``before_update``.


Mixin Helper methods and properties
===================================

``get_delete_put_post(item_id, user, prop_filters)``

Put, get, delete, post and get-all magic method handler.

* `item_id`: the primary key of the item - if none and method is 'GET' returns all items
* `user`: user to user as query filter.
* `prop_filters`: dictionary of key:value pairs to limit results when returning get-all.

====== ==============================================================================================================================
Method Operation
====== ==============================================================================================================================
GET    returns one item when `item_id` is a primary key.
GET    returns all items when `item_id` is None.
PUT    updates item using `item_id` as the id from request json data.  Calls the model verify before updating.
DELETE removes the item with primary key of `item_id` if self.can_delete does not throw an error. Returns the item removed.
POST   creates and returns a Flask response with a new item as json from form body data or JSON body data when `item_id` is None. Calls the model verify method before creating.
POST   updates an item from form data using `item_id`. Returns json response of {'message':'something'}.  Calls the model verify method before updating.
====== ==============================================================================================================================

On error returns a response of 'error message' with http status code of 400.

Set the `user` parameter to restrict a certain user.  Assumes that a model
relationship of user exists.

Prop filters is a dictionary of `property name`:`value` pairs.  Ie: {'group': 'admin'} to restrict list to the
admin group.  Properties or database fields can be used as the property name.

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

``before_update(self, data_dict)``

.. code:: python

    def dict_list(cls, query_result):
        """
        param: data_dict: a dictionary of new data to apply to the item
        return: the new data_dict to use when updating
        """

Hook to call before any of `update_from_dict`, `request_update_form`, `request_update_json` is called so that
you may alter or add update values before the item is written in preparation for update to db.  NOTE: copy data_dict to
a normal dict as it may be an Immutable type from the request object.

        data_dict: a dictionary of new data to apply to the item
        return: the new data_dict to use when updating

``dict_list()``

.. code:: python

    def dict_list(cls, query_result):
        """
        return a list of dictionary objects from the sql query result
        :param query_result: sql alchemy query result
        :return: list of dict objects
        """

``form_page(cls, item_id=None)``

Do all the work for creating and editing items using a template and a wtf form.

Prerequisites.

Setup the class properties to use your form items.

* `form` - WTForm Class - **Required**.
* `form_route_create` - **Required**. Name of the method to redirect after create, uses: url_for(cls.form_route_create, item_id=id)
* `form_route_update` - **Required**. Name of the method to redirect after updating, uses: url_for(cls.form_route_update, item_id=id)
* `form_template` - **Required**. Location of the template file to allow edit/add
* `form_update_format` - Format string to format flash message after update. `item` (the model instance) is passed as the only parameter.  Set to '' or None to suppress flash.
* `form_create_format` - Format string to format flash message after create. `item` (the model instance) is passed as the only parameter.  Set to '' or None to suppress flash.
* `form_update_title_format` - Format string to format title template value when editing. `item` (the model instance) is passed as the only parameter.
* `form_create_title_format` - Format string to format title template value when creating. `cls` (the model class) is passed as the only parameter.

The routes must use item_id as the parameter for editing. Use no parameter when creating.

Example:

To allow the Setting class to use a template and WTForm to create and edit items.  In this example after create the index page is
loaded, using the method `page_index`.  After update, the same page is reloaded with the new item values in the form.

Add these property overrides to the Setting Class.

.. code:: python

    # form_page
    form = EditForm
    form_route_update = 'route_setting_form'
    form_route_create = 'page_index'
    form_template = 'setting_edit.html'
    form_new_title_format = 'New Setting'

Add this form.

.. code:: python

    class EditForm(FlaskForm):
        value = StringField('value')

Setup these routes.

.. code:: python

    @app.route('/setting_form_edit/<int:item_id>', methods=['POST', 'GET'])
    @app.route('/setting_form_add', methods=['POST'])
    def route_setting_form(item_id=None):
        return Setting.form_page(item_id)

Template.

The template file needs to use WTForms to render the given form. `form`, `item`, `item_id` and `title` are passed as template
variables.

Example to update using POST, NOTE: only POST and GET are supported by form submit:

.. code:: html

    <h3>{{title}}</h3>
    <form method="POST" submit="{{url_for('route_setting_form', item_id=item.id)}}">
      <input name="value" value="{{form.value.data}}">
      <input type="submit">
    </form>

Example to create using POST:

.. code:: html

    <h3>{{title}}</h3>
    <form method="POST" submit="{{url_for('route_setting_form')}}">
      <input name="value" value="{{form.value.data}}">
      <input type="submit">
    </form>

``json_list(query_result)``

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

``json_filter_by(**kw_args)``

Return a flask list response in json format using a filter_by query.

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

``json_first(**kwargs)``

Return the first result in json format using filter_by arguments.

Example:

.. code:: python

    @bp.route('/score/<course>', methods=['GET'])
    @login_required
    def score(course):
        return Score.json_first(class_name=course)

``previous_field_value``

A dictionary of the previous field values before an update is applied from a dict, form or json update operation. Helpful
in the `verify` method to see if field values are to be changed.

Example:

.. code:: python

    def verify(self, create=False):
        previous_value = self.previous_field_value.get('value')
        if previous_value != self.value:
            current_app.logger.warning(f'value is changing from {previous_value}')

``request_create_form(**kwargs)``

Use the contents of a Flask request form or request json data to create a item
in the database.   Calls verify(create=True).  Returns the new item or throws error.
Use kwargs to set the object properties of the newly created item.

Example:

Create a score item with the parent being a course.

.. code:: python

    @bp.route('/score/<course_id>', methods=['POST'])
    @login_required
    def score(course_id):
        course = Course.query.get_or_404(course_id)
        return Score.request_create_form(course_id=course.id).as_dict

``request_update_form()``

Use the contents of a Flask request form or request json data to update an item
in the database.   Calls verify().  Returns True on success.

Example:

Update a score item.

/score/6?value=23.4

.. code:: python

    @bp.route('/score/<int:score_id>', methods=['PUT'])
    @login_required
    def score(score_id):
        score = Score.query.get_or_404(score_id)
        if Score.request_update_form():
            return 'ok'
        else:
            return 'update failed'

Release Notes
-------------

* 1.1.6 - Make sure all route returns use jsonify as required for older Flask versions.  Add before_update hook.
* 1.1.5 - Add previous_field_value array that is set during update.  Allows comparing new and previous values during verify.
* 1.1.4 - Fix doco typos and JavaScript examples.  Add form_page method.  Improve test and example apps.  Remove Python 2, 3.4 testing and support.
* 1.1.3 - Fix duplicate db writes.  Return item on delete.  Remove obsolete code structures.  Do not update with non-existent fields.
* 1.1.2 - Add 400 http status code for errors, remove error dict.  Improve documentation.
* 1.1.0 - Suppress silly errors. Improve documentation.
* 1.0.9 - Add kwargs to request_create_form to pass Object props to be used when creating the Object instance
* 1.0.8 - Cache introspection to improve performance.  All model definitions are cached after first use.  It is no longer possible to alter model definitions dynamically.
* 1.0.7 - Add json request body support to post update.
* 1.0.5 - Allow sorting of json lists.

Licensing
---------

- Apache 2.0

.. |PyPI Version| image:: https://img.shields.io/pypi/v/flask-serialize.svg
   :target: https://pypi.python.org/pypi/flask-serialize

