flask-serialize
===============
Read / Write JSON serialization of models for Flask applications using SQLAlchemy
---------------------------------------------------------------------------------

|PyPI Version|

Add as a Mixin (FlaskSerializeMixin).  This adds the properties and methods for serialization.

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

    @app.route('/get_setting/<item_id>', METHODS=['GET'])
    def get_setting( item_id ):
        return Setting.get_delete_put(item_id)

Delete a single item.

.. code:: python

    @app.route('/delete_setting/<item_id>', METHODS=['DELETE'])
    def delete_setting( item_id ):
        return Setting.get_delete_put(item_id)

Get all items as a json list.

.. code:: python

    @app.route('/get_setting_all', METHODS=['GET'])
    def get_setting_all():
        return Setting.get_delete_put()

Updating from a json object in the flask put request
    
JQuery:

.. code:: javascript

    function put(setting_id) {
        return $.ajax({
            url: `/update_setting/${setting_id}`,
            method: 'PUT',
            contentType: "application/json",
            data: {setting_type:'x',value:'100'},
        }).then(() => alert('updated'));
    }

Flask route:  

.. code:: python

    @app.route('/update_setting/<int:item_id>', methods=['PUT'])
    def update_setting(item_id):
        return Setting.get_delete_put(item_id)

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

Updating fields specification
-----------------------------

List of model fields to be read from a form or json when updating an object.  Normally
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

column_type_converters = {}

Where the key is the column type name of the database column 
and the value is a method to provide the conversion.

Example:

To convert VARCHAR(100) to a string:

.. code:: python

    column_type_converters['VARCHAR(100)'] = lambda v: str(v)

Conversion types (to database) add or replace update/create
--
A list of dicts that specify conversions.

Default is:

.. code:: python

    convert_types = [{'type': bool, 'method': lambda v: 'y' if v else 'n'}]

* type: a python object type  
* method: a lambda or method to provide the conversion to a database acceptable value.

Mixin Helper methods and properties
===================================

.. code:: python

    @property
    def as_dict(self):
        """
        the sql object as a dict without the excluded fields
        :return: dict
        """
        
    @property
    def as_json(self):
        """
        the sql object as a json object without the excluded fields
        :return: json object
        """

    def dict_list(cls, query_result):
        """
        return a list of dictionary objects from the sql query result
        :param query_result: sql alchemy query result
        :return: list of dict objects
        """
        
    @classmethod
    def json_list(cls, query_result):
        """
        return a list in json format from the query_result
        :param query_result: sql alchemy query result
        :return: json list of results
        """

Example:

.. code:: python

    @bp.route('/address/list', methods=['GET'])
    @login_required
    def address_list():
        items = Address.query.filter_by(user=current_user)
        return Address.json_list(items)

Licensing
---------

- Apache 2.0

.. |PyPI Version| image:: https://img.shields.io/pypi/v/flask-serialize.svg
   :target: https://pypi.python.org/pypi/flask-serialize

