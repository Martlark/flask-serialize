from flask import flash, redirect, url_for, request, render_template


class FormPageMixin:
    # form_page properties
    form_page_form = None  # name of the form to use
    form_page_route_update = (
        form_page_route_create
    ) = ""  # method names for successful redirect
    form_page_template = ""  # template for editing
    # all these called with .format(cls) or .format(item) as appropriate
    form_page_update_format = "Updated {}"
    form_page_create_format = "Created {}"
    form_page_new_title_format = "New {}"
    form_page_update_title_format = "Edit {}"

    @classmethod
    def form_page(cls, item_id=None):
        """
        Do all the work for creating and editing items using a template and a wtf form.
        Prerequisites.

        cls.form = WTFFormClass
        cls.form_route_create = Name of the method to redirect after create, uses: url_for(cls.form_route_create, item_id=id)
        cls.form_route_update = Name of the method to redirect after updating, uses: url_for(cls.form_route_update, item_id=id)
        cls.form_template = 'Location of the template file to allow edit/add'

        WTFFormClass - needs to have a hidden id with the name 'id'

        :param item_id: Item_id if editing, otherwise None
        :return: templates and redirects as required
        """
        form = cls.form_page_form()
        if item_id:
            item = cls.query.get_or_404(item_id)
            title = cls.form_page_update_title_format.format(item)
        else:
            title = cls.form_page_new_title_format.format(cls)
            item = dict(id=None)

        if form.validate_on_submit():
            try:
                if item_id:
                    item.fs_request_update_form()
                    msg = cls.form_page_update_format.format(item)
                    if msg:
                        flash(msg)
                    return redirect(
                        url_for(cls.form_page_route_update, item_id=item_id)
                    )
                else:
                    new_item = cls.fs_request_create_form()
                    msg = cls.form_page_create_format.format(new_item)
                    if msg:
                        flash(msg)
                    return redirect(
                        url_for(cls.form_page_route_create, item_id=new_item.id)
                    )
            except Exception as e:
                flash(str(e), category="danger")
        elif request.method == "GET":
            if not item_id:
                # new blank form
                item = cls()

            form = cls.form_page_form(obj=item)

        if form.errors:
            flash(
                "".join(
                    [
                        f'{form[f].label.text}: {"".join(e)} '
                        for f, e in form.errors.items()
                    ]
                ),
                category="danger",
            )

        return render_template(
            cls.form_page_template, title=title, item_id=item_id, item=item, form=form
        )
