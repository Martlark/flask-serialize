from datetime import datetime

from flask import request, jsonify, abort, current_app
from permissive_dict import PermissiveDict


class FlaskSerializeMixin:
    """
    Base mix in class to implement serialization and update methods for use
    with Flask and SQL Alchemy models
    """
    # fields that should not be exposed by serialization
    exclude_serialize_fields = []
    exclude_json_serialize_fields = []
    # list of fields to be used when updating
    update_fields = []
    # list of fields used when creating
    create_fields = []
    # order by ascending field
    order_by_field = None
    order_by_field_desc = None
    # default error code
    __http_error_code = 400
    # list of fields used to set the update date/time
    timestamp_fields = ['updated', 'timestamp']
    # method to be used to timestamp with update_timestamp method
    timestamp_stamper = datetime.utcnow
    # list of property names that are relationships to be included in serialization
    relationship_fields = []
    # add your own converters here
    column_type_converters = {}
    # add or replace conversion types
    convert_types = [{'type': bool, 'method': lambda v: 'y' if v else 'n'},
                     {'type': bytes, 'method': lambda v: v.encode()}]
    __json_types = [str, dict, list, int, float, bool]
    # default field name when restricting to a particular user
    fs_user_field = 'user'
    # properties or fields to return when updating using get or post
    update_properties = []
    # db is required to be set for updating/deletion functions
    db = None
    # cache model properties
    __model_props = {}
    # previous values of an instance before update attempted
    previous_field_value = {}
    # current version
    __version__ = '1.4.0'

    def before_update(self, data_dict):
        """
        hook to call before any update_from_dict so that you may alter update values
        before the item is written in preparation for update to db

        :param data_dict: the new data to apply to the item
        :return: the new data_dict to use for updating
        """
        return data_dict

    def to_date_short(self, d):
        """
        convert the given date field to a short date / time without fractional seconds

        :param d: {datetime.datetime} the value to convert
        :return: {String} the short date
        """
        return str(d).split('.')[0]

    @classmethod
    def query_by_access(cls, user=None, **kwargs):
        """
        filter a query result to that optionally owned by the given user and
        can_access()

        :param query: SQLAlchemy query
        :param user: the user to use as a filter, default relationship name is user (fs_user_field)
        :return: a list of query results
        """

        if user:
            kwargs[cls.fs_user_field] = user

        query = cls.query.filter_by(**kwargs)
        items = [item for item in query if item.can_access()]

        return items

    @classmethod
    def get_by_user_or_404(cls, item_id, user=None):
        """
        return the object with the given primary key id that is optionally owned by the given user and
        can_access()

        :param item_id: object primary key, id
        :param user: the user to use as a filter, default relationship name is user (fs_user_field)
        :return: the object
        :throws: 404 exception if not found
        """

        kwargs = {'id': item_id}
        if user:
            kwargs[cls.fs_user_field] = user
        item = cls.query.filter_by(**kwargs).first_or_404()
        if not item.can_access():
            abort(404)
        return item

    @classmethod
    def json_filter_by(cls, **kwargs):
        """
        return a list in json format using the filter_by arguments

        :param kwargs: SQLAlchemy query.filter_by arguments
        :return: flask response with json list of results
        """
        results = cls.query.filter_by(**kwargs)
        return cls.json_list(results)

    @classmethod
    def json_get(cls, item_id):
        """
        return an item in json format using the item_id as a primary key

        :param item_id: {primary key} the primary key of the item to get
        :return: flask response with json item, or {} if not found or no access
        """
        item = cls.query.get(item_id)
        if not item or not item.can_access():
            return jsonify({})
        return item.as_json

    @classmethod
    def json_list(cls, query_result, prop_filters=None):
        """
        Return a list in json format from the query_result.
        When order_by_field is defined sort by that field in ascending order.
        Only returns those that can_access()

        :param query_result: sql alchemy query result
        :param prop_filters: dictionary of filter elements to restrict results
        :return: flask response with json list of results
        """
        # ascending
        items = [item.__as_exclude_json_dict() for item in query_result if item.can_access()]

        if len(items) > 0 and cls.order_by_field:
            items = sorted(items, key=lambda i: i[cls.order_by_field])

        # descending
        if len(items) > 0 and cls.order_by_field_desc:
            items = sorted(items, key=lambda i: i[cls.order_by_field_desc], reverse=True)

        if prop_filters:
            filtered_result = []
            for item in items:
                for k, v in prop_filters.items():
                    if item.get(k) == v:
                        filtered_result.append(item)
                        break
            items = filtered_result

        return jsonify(items)

    @classmethod
    def dict_list(cls, query_result):
        """
        return a list of dictionary objects from the sql query result
        without exclude_serialize_fields fields
        for only those than can_access()

        :param query_result: sql alchemy query result
        :return: list of dict objects
        """
        return [item.__as_exclude_json_dict() for item in query_result if item.can_access()]

    @property
    def as_json(self):
        """
        the sql object as a json response without the excluded fields

        :return: flask response json object
        """
        return jsonify(self.__as_exclude_json_dict())

    def fs_private_field(self, field_name):
        return False

    def __as_exclude_json_dict(self):
        """
        private: get a dict that is used to serialize to web clients
        without fields in exclude_json_serialize_fields and exclude_serialize_fields
        excludes any private_field

        :return: dictionary
        """
        return {k: v for k, v in self.as_dict.items() if
                k not in self.exclude_json_serialize_fields}

    def property_converter(self, value):
        """
        convert to a json compatible format.

        * complex - just uses str conversion
        * datetime - short format as per to_date_short
        * set - becomes a list
        * anything else not supported by json becomes a str

        override or extend this method to alter defaults

        :param value: value to convert
        :return: the new value
        """
        if isinstance(value, datetime):
            return self.to_date_short(value)
        if isinstance(value, set):
            return list(value)
        if isinstance(value, FlaskSerializeMixin):
            return value.as_dict
        if type(value) not in self.__json_types:
            return str(value)
        return value

    @staticmethod
    def __relationship_converter(relationships):
        """
        convert a child SQLAlchemy result set into a python
        dictionary list.

        :param relationships: SQLAlchemy result set
        :return: list of dict objects
        """
        if isinstance(relationships, FlaskSerializeMixin):
            return relationships.as_dict
        return [item.as_dict for item in relationships]

    @staticmethod
    def __lob_converter(value):
        """
        convert a LOB into a decoded string

        :param value: lob to convert
        :return: decoded string
        """
        if not value:
            return ''
        value = value.decode()
        return value

    def __get_props(self):
        """
        get the properties for this table to be used for introspection

        :return: properties EasyDict
        """
        props = self.__model_props.get(self.__table__)
        if not props:
            props = PermissiveDict(name=self.__table__.name)
            props.converters = {'DATETIME': self.to_date_short,
                                'PROPERTY': self.property_converter,
                                'RELATIONSHIP': self.__relationship_converter,
                                'NUMERIC': float,
                                'DECIMAL': float,
                                'LOB': self.__lob_converter,
                                'BLOB': self.__lob_converter,
                                'CLOB': self.__lob_converter,
                                }

            # SQL columns
            props.exclude_fields = ['as_dict', 'as_json'] + self.exclude_serialize_fields
            field_list = self.__table__.columns
            for f in field_list:
                props.id = str(getattr(self, f.name, '')) if f.primary_key else props.id
            # add extra properties that are not from here
            field_list += [PermissiveDict(name=p, type='PROPERTY') for p in dir(self.__class__) if
                           isinstance(getattr(self.__class__, p), property)]
            field_list += [PermissiveDict(name=p, type='RELATIONSHIP') for p in self.relationship_fields]
            # add custom converters
            for converter, method in self.column_type_converters.items():
                props.converters[converter] = method
            # exclude fields / props
            props.field_list = []
            for f in field_list:
                if f.name not in props.exclude_fields:
                    f.c_type = str(f.type).split('(')[0]
                    f.converter = props.converters.get(f.c_type)
                    if not f.converter:
                        # any non json supported types gets a str
                        if getattr(f.type, 'python_type', None) not in self.__json_types:
                            f.converter = str
                    props.field_list.append(f)

            self.__model_props[self.__table__] = props
        return props

    @property
    def as_dict(self):
        """
        convert a sql alchemy query result item to dict
        override these properties to control the result:

        * relationship_fields - follow relationships listed
        * exclude_serialize_fields - exclude listed fields from serialization
        * column_type_converters - add additional sql column type converters to DATETIME, PROPERTY and RELATIONSHIP
        :return {dictionary} the item as a dict
        """

        # built in converters
        # can be replaced using column_type_converters
        d = {}

        for c in self.__get_props().field_list:
            if not self.fs_private_field(c.name):
                try:
                    d[c.name] = v = getattr(self, c.name, '')
                except Exception as e:
                    v = str(e)

                if v is None:
                    d[c.name] = ''
                elif c.converter:
                    try:
                        d[c.name] = c.converter(v)
                    except Exception as e:
                        d[c.name] = 'Error:"{}". Failed to convert [{}] type:{}'.format(e, c.name, c.c_type)
        return d

    def json_api_dict(self):
        """
        start of returning as JSON_API.  Unused

        :return: {id, name, attributes(dict)}
        """
        props = self.__get_props()
        d = dict(id=props.id, type=props.name, attributes=self.as_dict)
        return jsonify(d)

    def json_api_list(self, query_result):
        """
        start of returning as JSON_API.  Unused
        returns a list of items where can_access() from query_result

        :param query_result:
        :return: list of {id, name, attributes(dict)}
        """
        dict_list = self.dict_list(query_result=query_result)
        d = dict(data=[item.json_api_dict() for item in dict_list])
        return jsonify(d)

    def __get_update_field_type(self, field, value):
        """
        get the type of the update to db field from cached table properties

        :param field:
        :return: class of the type
        """
        props = self.__get_props()
        if props:
            for f in props.field_list:
                if f.name == field:
                    if f.c_type.startswith("VARCHAR") or f.c_type.startswith("CHAR") or f.c_type.startswith("TEXT"):
                        return str
                    if f.c_type.startswith("INTEGER"):
                        return int
                    if f.c_type.startswith("FLOAT") or f.c_type.startswith("REAL") or f.c_type.startswith("NUMERIC"):
                        return float
                    if f.c_type.startswith("DATE") or f.c_type.startswith("TIME"):
                        return datetime
                    if f.c_type.startswith("BOOLEAN"):
                        return bool
                    if 'LOB' in f.c_type:
                        return bytes

        return None

    def __convert_value(self, name, value):
        """
        convert the value based upon type to a representation suitable for saving to the db
        override built in conversions by setting the value of convert_types. ie:
        first uses bare value to determine type and then
        uses db derived values
        convert_types = [{'type':bool, 'method': lambda x: not x}]

        :param value:
        :return: the converted value
        """
        for t in self.convert_types:
            if isinstance(value, t['type']):
                value = t['method'](value)
                return value

        instance_type = self.__get_update_field_type(name, value)
        if instance_type:
            for t in self.convert_types:
                if instance_type == t['type']:
                    value = t['method'](value)
                    return value
        return value

    @classmethod
    def request_create_form(cls, **kwargs):
        """
        create a new item from a form in the current request object
        throws error if something wrong. Use **kwargs to set the object properties of the newly created item.

        :return: the new created item
        """
        new_item = cls(**kwargs)

        if len(new_item.create_fields or '') == 0:
            raise Exception('create_fields is empty')

        try:
            json_data = request.get_json(force=True)
            if len(json_data) > 0:
                for field in cls.create_fields:
                    if field in json_data:
                        value = json_data.get(field)
                        setattr(new_item, field, new_item.__convert_value(field, value))
        except:
            for field in cls.create_fields:
                if field in request.form:
                    value = request.form.get(field)
                    setattr(new_item, field, new_item.__convert_value(field, value))

        new_item.verify(create=True)
        new_item.update_timestamp()
        cls.db.session.add(new_item)
        cls.db.session.commit()
        return new_item

    def request_update_form(self):
        """
        update/create the item using form data from the request object
        only present fields are updated
        throws error if validation or can_update() fails

        :return: True when complete
        """
        if request.content_type == 'application/json' or request.method == 'PUT':
            return self.request_update_json()
        else:
            self.update_from_dict(request.form)
        if not self.can_update():
            return False
        self.verify()
        self.update_timestamp()
        self.db.session.add(self)
        self.db.session.commit()
        return True

    def request_update_json(self):
        """
        Update an item from request json data or PUT params, probably from a PUT or PATCH.
        Throws exception if not valid or can_update() fails

        :return: True if item updated
        """

        if not self.can_update():
            return False
        try:
            json_data = request.get_json(force=True)
        except Exception as e:
            json_data = request.values
            if len(json_data) == 0:
                current_app.logger.exception(e)

        self.update_from_dict(json_data)

        self.verify()
        self.update_timestamp()
        self.db.session.add(self)
        self.db.session.commit()
        return True

    def update_timestamp(self):
        """
        update any timestamp fields using the Class timestamp method if those fields exist

        """
        for field in self.timestamp_fields:
            if hasattr(self, field):
                setattr(self, field, self.timestamp_stamper())

    def update_from_dict(self, data_dict):
        """
        uses a dict to update fields of the model instance.  sets previous values to
        self.previous_values[field_name] before the update

        :param data_dict: the data to update
        :return:
        """
        data_dict = self.before_update(data_dict)
        if len(self.update_fields or '') == 0:
            raise Exception('update_fields is empty')

        for field in self.update_fields:
            self.previous_field_value[field] = getattr(self, field)
            if field in data_dict:
                setattr(self, field, self.__convert_value(field, data_dict[field]))

    def can_access(self):
        """
        return True if allowed to access, return false if not

        :return: True/False
        """
        return True

    def can_update(self):
        """
        return True if allowed to update, raise an error if not allowed

        :return: True if can update
        """
        return self.can_access()

    def can_delete(self):
        """
        raise an exception if deletion is not allowed or True
        if deletion is allowed.  Default is can_update() returns false
        aborts with 403

        :return: True if can delete
        """
        if not self.can_update():
            abort(403)
        return True

    def verify(self, create=False):
        """
        raise exception if item is not valid for put/patch/post

        :param: create - True if verification is for a new item
        """
        pass

    def __return_properties(self):
        """
        when returning success codes from a put/post update return a dict
        composed of the property values from the update_properties list.
        ie:
        return jsonify({'message': 'Updated', 'properties': item.__return_properties()})
        this can be used to communicate from the model on the server to the JavaScript code
        interesting things from updates

        :return: dictionary of properties
        """
        return {prop: self.property_converter(getattr(self, prop)) for prop in self.update_properties}

    @classmethod
    def get_delete_put_post(cls, item_id=None, user=None, prop_filters=None):
        """
        get, delete, post, put with JSON/FORM a single model item

        * any access uses can_access() to check for accessibility
        * any update uses can_update() to check for update permission

        :param item_id: the primary key of the item - if none and method is 'GET' returns all items
        :param user: user to use as query filter.
        :param prop_filters: dictionary of key:value pairs to limit results to.
        :return: json object: {message}, or the item.  throws error when problem
        """
        item = None
        if user is not None and item_id is not None:
            item = cls.get_by_user_or_404(item_id, user=user)
        elif item_id is not None:
            item = cls.query.get_or_404(item_id)
            if not item.can_access():
                abort(404)
        elif request.method == 'GET':
            # no item id get a list of items
            if user:
                kwargs = {}
                kwargs[cls.fs_user_field] = user
                result = cls.query.filter_by(**kwargs)
            else:
                result = cls.query.all()
            return cls.json_list(result, prop_filters=prop_filters)

        try:
            if not item:
                if request.method == 'POST':
                    return cls.request_create_form().as_json
                abort(405)

            # get a single item
            if request.method == 'GET':
                return item.as_json

            elif request.method == 'POST' or request.method == 'PUT':
                # update single item
                item.request_update_form()
                return jsonify(dict(message='Updated', properties=item.__return_properties()))

            elif request.method == 'DELETE':
                # delete a single item
                item.can_delete()
                cls.db.session.delete(item)
                cls.db.session.commit()
                return jsonify(dict(item=item.as_dict, message='Deleted'))

        except Exception as e:
            return str(e), cls.__http_error_code

    @classmethod
    def json_first(cls, **kwargs):
        """
        return the first result in json response format using the filter_by arguments, or {} if no result
        or not can_access()

        :param kwargs: SQLAlchemy query.filter_by arguments
        :return: flask response json item or {} if no result
        """
        item = cls.query.filter_by(**kwargs).first()
        if not item or not item.can_access():
            return jsonify({})

        return item.as_json
