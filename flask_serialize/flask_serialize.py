from datetime import datetime

from flask import request, jsonify, abort, current_app
from easydict import EasyDict


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
    http_error_code = 400
    # list of fields used to set the update date/time
    timestamp_fields = ['updated', 'timestamp']
    # method to be used to timestamp with update_timestamp method
    timestamp_stamper = datetime.utcnow
    # list of property names that are relationships to be included in serialization
    relationship_fields = []
    # add your own converters here
    column_type_converters = {}
    # add or replace conversion types
    convert_types = [{'type': bool, 'method': lambda v: 'y' if v else 'n'}]
    # properties or fields to return when updating using get or post
    update_properties = []
    # db is required to be set for updating/deletion functions
    db = None
    # cache model properties
    model_props = {}
    # current version
    version = '1.1.2'

    def to_date_short(self, d):
        """
        convert the given date field to a short date / time without fractional seconds

        :param d: {datetime.datetime} the value to convert
        :return: {String} the short date
        """
        return str(d).split('.')[0]

    @classmethod
    def get_by_user_or_404(cls, item_id, user):
        """
        return the object with the given id that is owned by the given user

        :param item_id: object id
        :param user: the user to use as a filter, assumes relationship name is user
        :return: the object
        :throws: 404 exception if not found
        """
        item = cls.query.filter_by(id=item_id, user=user).first()
        if not item:
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
        :return: flask response with json item, or {} if not found
        """
        item = cls.query.get(item_id)
        if not item:
            return jsonify({})
        return item.as_json

    @classmethod
    def json_list(cls, query_result, prop_filters=None):
        """
        Return a list in json format from the query_result.
        When order_by_field is defined sort by that field in ascending order.

        :param query_result: sql alchemy query result
        :param prop_filters: dictionary of filter elements to restrict results
        :return: flask response with json list of results
        """
        # ascending
        items = [item.__as_exclude_json_dict() for item in query_result]

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

        :param query_result: sql alchemy query result
        :return: list of dict objects
        """
        return [item.__as_exclude_json_dict() for item in query_result]

    @property
    def as_json(self):
        """
        the sql object as a json object without the excluded fields

        :return: flask response json object
        """
        return jsonify(self.__as_exclude_json_dict())

    def clear_cache(self):
        self.model_props = {}

    def set_column_type_converter(self, col_type, method):
        self.column_type_converters[col_type] = method
        self.model_props = {}

    def __as_exclude_json_dict(self):
        """
        private: get a dict that is used to serialize to web clients
        without fields in exclude_json_serialize_fields and exclude_serialize_fields

        :return: dictionary
        """
        return {k: v for k, v in self.as_dict.items() if k not in self.exclude_json_serialize_fields}

    def property_converter(self, value):
        """
        convert datetime and set to a json compatible format.
        override this method to alter default

        :param value: value to convert
        :return: the new value
        """
        if isinstance(value, datetime):
            return self.to_date_short(value)
        if isinstance(value, set):
            return list(value)
        return value

    @staticmethod
    def relationship_converter(relationships):
        """
        convert a child SQLalchemy result set into a python
        dictionary list.

        :param relationships: SQLAlchemy result set
        :return: list of dict objects
        """
        return [item.as_dict for item in relationships]

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
        # can be replaced dynamically using column_type_converters
        d = {}
        props = self.model_props.get(self.__table__)
        if not props:
            props = EasyDict()
            props.converters = {'DATETIME': self.to_date_short, 'PROPERTY': self.property_converter,
                                'RELATIONSHIP': self.relationship_converter}

            # SQL columns
            props.exclude_fields = ['as_dict', 'as_json'] + self.exclude_serialize_fields
            field_list = self.__table__.columns
            # add extra properties that are not from here
            field_list += [EasyDict(name=p, type='PROPERTY') for p in dir(self.__class__) if
                           isinstance(getattr(self.__class__, p), property)]
            field_list += [EasyDict(name=p, type='RELATIONSHIP') for p in self.relationship_fields]
            # add custom converters
            for converter, method in self.column_type_converters.items():
                props.converters[converter] = method
            # exclude fields / props
            props.field_list = []
            for f in field_list:
                if f.name not in props.exclude_fields:
                    f.c_type = str(f.type)
                    f.converter = props.converters.get(f.c_type)
                    props.field_list.append(f)

            self.model_props[self.__table__] = props

        for c in props.field_list:
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

    def __convert_value(self, value):
        """
        convert the value based upon type to a representation suitable for saving to the db
        override built in conversions by setting the value of convert_types. ie:
        convert_types = [{'type':bool, 'method': lambda x: not x}]

        :param value:
        :return: the converted value
        """
        for t in self.convert_types:
            if isinstance(value, t['type']):
                value = t['method'](value)
                return value
        return value

    def request_update_form(self):
        """
        update/create the item using form data from the request object
        only present fields are updated
        throws error if validation fails

        :return: True when complete
        """
        if request.content_type == 'application/json':
            self.request_update_json()
        else:
            self.update_from_dict(request.form)
        self.verify()
        self.update_timestamp()
        self.db.session.add(self)
        self.db.session.commit()
        return True

    @classmethod
    def request_create_form(cls, **kwargs):
        """
        create a new item from a form in the current request object
        throws error if something wrong. Use **kwargs to set the object properties of the newly created item.

        :return: the new created item
        """
        new_item = cls(**kwargs)
        # field_list = cls.__table__.columns

        if len(new_item.create_fields or '') == 0:
            raise Exception('create_fields is empty')

        try:
            json_data = request.get_json(force=True)
            if len(json_data) > 0:
                for field in cls.create_fields:
                    value = json_data.get(field)
                    setattr(new_item, field, new_item.__convert_value(value))
        except:
            for field in cls.create_fields:
                value = request.form.get(field)
                setattr(new_item, field, new_item.__convert_value(value))

        new_item.verify(create=True)
        new_item.update_timestamp()
        cls.db.session.add(new_item)
        cls.db.session.commit()
        return new_item

    def request_update_json(self):
        """
        Update an item from request json data, probably from a PUT or PATCH.
        Throws exception if not valid

        :return: True if item updated
        """

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
        update any timestamp fields using the Class timestamp method
        """
        for field in self.timestamp_fields:
            if hasattr(self, field):
                setattr(self, field, self.timestamp_stamper())

    def update_from_dict(self, data_dict):
        """
        uses a dict to update fields of the model instance

        :param data_dict:
        :return:
        """
        if len(self.update_fields or '') == 0:
            raise Exception('update_fields is empty')

        for field in self.update_fields:
            if field in data_dict:
                setattr(self, field, self.__convert_value(data_dict[field]))

    def can_delete(self):
        """
        raise a message if deletion is not allowed

        :return:
        """
        pass

    def verify(self, create=False):
        """
        raise exception if item is not valid for put/patch/post

        :param: create - True if verification is for a new item
        """
        pass

    def return_properties(self):
        """
        when returning success codes from a put/post update return a dict
        composed of the property values from the update_properties list.
        ie:
        return jsonify({'message': 'Updated', 'properties': item.return_properties()})
        this can be used to communicate from the model on the server to the JavaScript code
        interesting things from updates

        :return: dictionary of properties
        """
        props = {}
        for prop in self.update_properties:
            props[prop] = self.property_converter(getattr(self, prop))
        return props

    @classmethod
    def get_delete_put_post(cls, item_id=None, user=None, prop_filters=None):
        """
        get, delete, post, put with JSON/FORM a single model item

        :param item_id: the primary key of the item - if none and method is 'GET' returns all items
        :param user: user to user as query filter.
        :param prop_filters: dictionary of key:value pairs to limit results to.
        :return: json object: {error, message}, or the item.  error == None for correct operation
        """
        item = None
        if user is not None and item_id is not None:
            item = cls.get_by_user_or_404(item_id, user=user)
        elif item_id is not None:
            item = cls.query.get_or_404(item_id)
        elif request.method == 'GET':
            # no item id get a list of items
            if user:
                result = cls.query.filter_by(user=user)
            else:
                result = cls.query.all()
            return cls.json_list(result, prop_filters=prop_filters)

        if not item:
            if request.method == 'POST':
                try:
                    return cls.request_create_form().as_json
                except Exception as e:
                    return str(e), cls.http_error_code

            abort(404)

        # get a single item
        if request.method == 'GET':
            return item.as_json

        elif request.method == 'POST':
            # update single item
            try:
                item.request_update_form()
            except Exception as e:
                return str(e), cls.http_error_code
            return dict(message='Updated', properties=item.return_properties())

        elif request.method == 'DELETE':
            # delete a single item
            try:
                item.can_delete()
                cls.db.session.delete(item)
                cls.db.session.commit()
            except Exception as e:
                return str(e), cls.http_error_code

            return dict(error=None, message='Deleted')

        # PUT, save the modified item
        try:
            item.request_update_json()
        except Exception as e:
            return str(e), cls.http_error_code

        return dict(error=None, message='Updated', properties=item.return_properties())

    @classmethod
    def json_first(cls, **kwargs):
        """
        return the first result in json format using the filter_by arguments

        :param kwargs: SQLAlchemy query.filter_by arguments
        :return: flask response json item or {} if no result
        """
        item = cls.query.filter_by(**kwargs).first()
        if not item:
            return {}
        return item.as_json
