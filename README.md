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

Get a single item as json.

    @app.route('/get_setting/<item_id>', METHODS=['GET'])
    def get_setting( item_id )
        return Setting.get_delete_put(item_id)

Delete a single item.

    @app.route('/delete_setting/<item_id>', METHODS=['DELETE'])
    def delete_setting( item_id )
        return Setting.get_delete_put(item_id)

Get all items as a json list.

    @app.route('/get_setting_all', METHODS=['GET'])
    def get_setting_all()
        return Setting.get_delete_put()

Updating from a json object in the flask put request
    
Javascript (KnockoutJS Example):

    put() {
        return $.ajax({
            url: `/update_setting/${this.id()}`,
            method: 'PUT',
            contentType: "application/json",
            data: ko.toJSON(this),
        }).then(() => alert('updated'));
    }

Flask route:  
    
    @bp.route('/update_setting/<int:item_id>', methods=['PUT'])
    @admin_required
    def update_setting(item_id):
        return Setting.get_delete_put(item_id)

Create or update from a WTF form:

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
                        flash(_('Your changes have been saved.'))
                    except Exception as e:
                        flash(str(e), category='danger')
                    return redirect(url_for('setting_edit', item_id=item_id))
                else:
                    try:
                        new_item = Setting.request_create_form()
                        flash(_('Setting created.'))
                        return redirect(url_for('setting_edit', item_id=new_item.id))
                    except Exception as e:
                        flash('Error creating item: ' + str(e))
                        
            return render_template(
                    'setting_edit.html',
                    item=item,
                    title='Edit or Create item',
                    form=form
                )
