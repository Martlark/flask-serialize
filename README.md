# flask-serialize
Read / Write JSON serialization of models for Flask applications using SQLAlchemy
=================

Add as a Mixin (FlaskSerializeMixin).  This adds the properties and methods for serialization.

Simple usage:
-------------

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
    
        def __repr__(self):
            return '<Setting %r %r %r>' % (self.id, self.setting_type, self.value)
    
        def verify(self, create=False):
            if not self.key or len(self.key) < 1:
                raise Exception('Missing key')
    
            if not self.setting_type or len(self.setting_type) < 1:
                raise Exception('Missing setting type')

In your routes:
---------------

To get a single item as json.

    @app.route('/get_setting/<item_id>', METHODS=['GET'])
    def get_setting( item_id )
        return Setting.get_delete_put(item_id)

To delete a single item.

    @app.route('/delete_setting/<item_id>', METHODS=['DELETE'])
    def delete_setting( item_id )
        return Setting.get_delete_put(item_id)

To get all items as a json list.

    @app.route('/get_setting_all', METHODS=['GET'])
    def get_setting_all()
        return Setting.get_delete_put()
