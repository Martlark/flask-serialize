import json
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
    # fields to be updated
    update_fields = []
    # fields used when creating
    create_fields = []
    # fields used to set the update date/time
    timestamp_fields = ['updated', 'timestamp']
    # list of property names that are relationships to be included in serialization
    relationship_fields = []
    # add your own converters here
    column_type_converters = {}
    # add or replace conversion types
    convert_types = [{'type': bool, 'method': lambda v: 'y' if v else 'n'}]
    # this is required to be set for updating/deletion functions
    db = None

    @classmethod
    def to_date_short(cls, d):
        """
        convert the given date field to a short date / time without fractional seconds
        :param d: datetime.datetime
        :return: {String} the short date
        """
        return str(d).split('.')[0]

    @classmethod
    def get_by_user_or_404(cls, item_id, user):
        """
        return the object with the given id that is owned by the given user
        :param item_id: object id
        :param param: the user to use as a filter, assumes relationship name is user
        :return: the object
        :throws: 404 exception if not found
        """
        item = cls.query.filter_by(id=item_id, user=user).first()
        if not item:
            abort(404)
        return item

    @classmethod
    def json_list(cls, query_result):
        """
        return a list in json format from the query_result
        :param query_result: sql alchemy query result
        :return: json list of results
        """
        return jsonify([item.__as_exclude_json_dict() for item in query_result])

    @classmethod
    def dict_list(cls, query_result):
        """
        return a list of dictionary objects from the sql query result
        :param query_result: sql alchemy query result
        :return: list of dict objects
        """
        return [item.__as_exclude_json_dict() for item in query_result]

    @property
    def as_json(self):
        """
        the sql object as a json object without the excluded fields
        :return: json object
        """
        return jsonify(self.__as_exclude_json_dict())

    def __as_exclude_json_dict(self):
        """
        private: get a dict that is used to serialize to web clients
        :return: dictionary
        """
        return {k: v for k, v in self.as_dict.items() if k not in self.exclude_json_serialize_fields}

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

        def property_converter(s):
            if isinstance(s, dict):
                try:
                    converted_value = json.dumps(s)
                    return converted_value
                except:
                    pass
            return s

        def relationship_converter(s):
            return [item.as_dict for item in s]

        # built in converters

        __converters = {'DATETIME': lambda date_value: str(date_value).split('.')[0], 'PROPERTY': property_converter,
                        'RELATIONSHIP': relationship_converter}

        d = {}
        # SQL columns
        field_list = self.__table__.columns
        # add extra properties that are not from here
        field_list += [EasyDict(name=p, type='PROPERTY') for p in dir(self.__class__) if
                       isinstance(getattr(self.__class__, p), property)]
        field_list += [EasyDict(name=p, type='RELATIONSHIP') for p in self.relationship_fields]
        exclude_fields = ['as_dict', 'as_json'] + self.exclude_serialize_fields
        # add custom converters
        for converter, method in self.column_type_converters.items():
            __converters[converter] = method

        for c in field_list:
            if c.name in exclude_fields:
                continue
            try:
                v = getattr(self, c.name)
            except:
                v = ''
            c_type = str(c.type)

            if c_type in __converters and v is not None:
                try:
                    d[c.name] = __converters[c_type](v) if __converters[c_type] else v
                except Exception as e:
                    d[c.name] = 'Error:{}  Failed to covert using {}'.format(e, c_type)
            elif v is None:
                d[c.name] = ''
            else:
                d[c.name] = v

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
        for field in self.update_fields:
            if field in request.form:
                value = request.form.get(field)
                setattr(self, field, self.__convert_value(value))

        self.verify()
        self.update_timestamp()
        self.db.session.add(self)
        self.db.session.commit()
        return True

    @classmethod
    def request_create_form(cls):
        """
        create new item from a form in the current request object
        throws error if something wrong
        :return: the new created item
        """
        new_item = cls()
        # field_list = cls.__table__.columns

        for field in cls.create_fields:
            value = request.form.get(field)
            # cls_column = getattr(cls, field)
            # cls_column_type = str(cls_column.type.python_type)  # str,datetime.datetime,float,int
            setattr(new_item, field, new_item.__convert_value(value))

        new_item.verify(create=True)
        new_item.update_timestamp()
        cls.db.session.add(new_item)
        cls.db.session.commit()
        return new_item

    def request_update_json(self):
        """
        Update an item from json data, probably from a PUT or PATCH.
        Throws exception if not valid
        :return: True if item updated
        """
        try:
            json_data = request.get_json(force=True)
        except Exception as e:
            current_app.logger.exception(e)
            json_data = request.values

        for f in self.update_fields:
            if f in json_data:
                value = json_data[f]
                setattr(self, f, self.__convert_value(value))

        self.verify()
        self.update_timestamp()
        self.db.session.add(self)
        self.db.session.commit()
        return True

    def update_timestamp(self):
        """
        update any timestamp fields with the current local time/date
        """
        for field in self.timestamp_fields:
            if hasattr(self, field):
                setattr(self, field, datetime.now())

    def update_from_dict(self, data_dict):
        """
        uses a dict to update fields
        :param data_dict:
        :return:
        """
        for field in self.update_fields:
            if field in data_dict:
                setattr(self, field, data_dict[field])

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

    @classmethod
    def get_delete_put(cls, item_id=None, user=None):
        """
        get, delete or update with JSON a single model item
        :param item_id: the key of the item - if none and method is get returns all items
        :param user: user to add as query item.
        :return: json object: {error, message}, or the item.  error == None for correct operation
        """
        item = None
        if user and item_id:
            item = cls.get_by_user_or_404(item_id, user=user)
        if item_id:
            item = cls.query.get(item_id)
        elif request.method == 'GET':
            # get a list of items
            if user:
                return cls.json_list(cls.query.filter_by(user=user))
            else:
                return cls.json_list(cls.query.all())

        if not item:
            abort(404)

        # get a single item
        if request.method == 'GET':
            return item.as_json

        # delete a single item
        elif request.method == 'DELETE':
            try:
                item.can_delete()
                cls.db.session.delete(item)
                cls.db.session.commit()
            except Exception as e:
                return jsonify(dict(error=str(e), message=''))

            return jsonify(dict(error=None, message='Deleted'))

        # PUT save the modified item
        try:
            item.request_update_json()
        except Exception as e:
            return jsonify(dict(error=str(e), message=''))

        return jsonify(dict(error=None, message='Updated'))
