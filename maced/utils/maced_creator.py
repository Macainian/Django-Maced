# This is 3 files in one. Used to be maced_creator.py, build_functions.py, and get_html_code_functions.py, but Python
#       2.7 sucks and doesn't allow recursive imports. Now all 3 files are here in 1 and separated by large spacing.

import inspect
import json
from copy import deepcopy

from django.core.urlresolvers import reverse
from django.shortcuts import render

from maced.utils.constants import PRIMARY_ACTION_TYPES, VALID_INPUT_TYPES, VALID_SELECT_TYPES, ADD, EDIT, MERGE, DELETE, \
    CLONE, INFO
from maced.utils.misc import validate_select_options, prettify_string


# The main function to craft html code for each item. This is the only function that should be called directly besides
#       finalize_context_for_items().
# item_name is the name of the model in most cases. You could potentially have 2 of the same model on a page, however
#       this will currently requires you to have 2 sets of urls which is kind of dumb, but still possible.
# item_html_name is the name that will show up on the frontend to the users. This is also the name used on the modals.
# item_model is the class of the model. Be sure to send in the class, not the instance of the class.
# item_name_field_name is the name of the field that stores the name for this model. Example: You have a model called
#       Gender. It will have some kind of field to identify the gender by. This will likely be called "name", but
#       could be called anything so it is required to be able to identify the object on the frontend.
# field_list is the specially formatted list of fields and their info. For more information please refer to the
#       README.md file.
# name_of_app_with_url is the name of the app that has the urls that will be used for performing all of the actions
#       from maced. Please note that url names should be named according to AppName.maced_ItemName. Example:
#       App name is component_manager and the item is component. The url name should be
#       "component_manager.maced_component"
# current_item_id is the id of the item that will be selected by default on the frontend when you first land on the
#       page. If you do not need one preselected, use 0. Since it can be tedious to get the current_item_id for each
#       object if you have several for a page, you can simply use the get_current_item_id(model_instance, field_name)
#       function. Just pass it your related model and the field name of the field that this item represents. Example:
#       You have a model called Person with an attribute called City but it is not a required field for this Person
#       object. You want City to be a maced item, but you don't want to have to check if city is there for this
#       person, because if it doesn't you won't be able to say person.city.id because id isn't on None. Of course, you
#       can do this manually, but if you have several of these, it could be annoying and the code will look cluttered.
#       Instead use get_current_item_id(person, "city") and it will do the work for you and raise errors appropriately.
#       If city isn't set for this person, it will return 0, which will result in the first select item to be
#       preselected (should be a blank entry in the select in this case since city isn't required).
# allow_empty simply sets whether or not a blank will be inserted into the select. This defaults to True. Set this to
#       False if you want this field to be required. One caveat is that if you don't have any instances of this model
#       in the system yet and you make it required, nothing will prevent it from allowing you to submit the form and
#       will have to be handled on the backend. Perhaps this can be changed in the future.
# field_to_order_by is the field to order your select by. It defaults to None which converts to item_name_field_name.
#       Note that you can add "-" in front of the field_to_order_by to make it descending order.
# is_used_only_for_maced_fields is used to signal that this will not be used on the page directly, but as a part of
#       another maced item as a maced field. Defaults to False since this is less common. If you need to use it as both
#       a maced item and a maced field for another maced item, then keep this as False and all will be fine.
def add_item_to_context(context, item_name, item_model, item_name_field_name, field_list,
                        name_of_app_with_url, current_item_id, item_html_name=None, allow_empty=True,
                        field_to_order_by=None, is_used_only_for_maced_fields=False):
    if not isinstance(context, dict):
        raise TypeError("Please provide a valid context")

    if not isinstance(item_name, (str, unicode)):
        raise TypeError("item_name must be a string")

    if not inspect.isclass(item_model):
        raise TypeError("item_model must be a class")

    if not isinstance(item_name_field_name, (str, unicode)):
        raise TypeError("object_name_field_name must be a string")

    if not isinstance(field_list, list):
        raise TypeError("field_list must be a list")

    if not isinstance(name_of_app_with_url, (str, unicode)):
        raise TypeError("name_of_app_with_url must be a string")

    if not isinstance(current_item_id, int):
        raise TypeError("current_item_id must be a integer")

    if not isinstance(item_html_name, (str, unicode)) and item_html_name is not None:
        raise TypeError("item_html_name must be a string or None")

    if not isinstance(allow_empty, bool):
        raise TypeError("allow_empty must be a bool")

    if not isinstance(field_to_order_by, (str, unicode)) and field_to_order_by is not None:
        raise TypeError(
            "field_to_order_by must be a string that is the name of the field you want to order your objects by or None"
        )

    if not isinstance(is_used_only_for_maced_fields, bool):
        raise TypeError("is_used_only_for_maced_fields must be a bool")

    if "maced_data" not in context:
        context["maced_data"] = {}

    if "maced_modals" not in context:
        context["maced_modals"] = ""

    if "individual_maced_modals" not in context:
        context["individual_maced_modals"] = {}

    maced_data = context["maced_data"]

    if "item_names" not in maced_data:
        maced_data["item_names"] = []

    if "items_to_remove" not in maced_data:
        maced_data["items_to_remove"] = []

    if "field_names" not in maced_data:
        maced_data["field_names"] = {}

    if "field_identifiers" not in maced_data:
        maced_data["field_identifiers"] = {}

    if "urls" not in maced_data:
        maced_data["urls"] = {}

    if "item_names_with_ignored_alerts" not in maced_data:
        maced_data["item_names_with_ignored_alerts"] = []

    if item_name in maced_data["item_names"]:
        raise ValueError("Duplicate item var name of " + str(item_name))

    if is_used_only_for_maced_fields:
        maced_data["items_to_remove"].append(item_name)
    else:
        maced_data["item_names"].append(item_name)

    if item_html_name is None:
        item_html_name = prettify_string(item_name)

    if field_to_order_by is None:
        field_to_order_by = item_name_field_name

    initialize_fields_for_item_in_maced_data(maced_data=maced_data, item_name=item_name)
    context[item_name + "_dependencies"] = []

    # Get all items of this type
    items = get_items(item_model=item_model, field_to_order_by=field_to_order_by)

    # Create an item_options_list which is a list of tuples defined as (id_of_the_item, name_of_the_item). This will
    # be used in the merge function.
    item_options_list = [(item.id, getattr(item, item_name_field_name)) for item in items]

    # Constructs url
    url = build_url(item_name=item_name, name_of_app_with_url=name_of_app_with_url)

    # Add the get url to the context
    maced_data["urls"][item_name] = url

    # Make a builder so we can reuse it later for maced fields
    context[item_name + "_builder"] = build_builder(
        item_name=item_name, item_html_name=item_html_name, item_model=item_model, field_to_order_by=field_to_order_by,
        url=url, item_options_list=item_options_list, field_list=field_list, allow_empty=allow_empty
    )

    # All the special html that is built in python
    html_code_dictionary = build_html_code(
        context=context, item_options_list=item_options_list, item_name=item_name, item_html_name=item_html_name,
        field_list=field_list
    )

    # The final step of putting it all together to make 2 sets of html; one for the item on the page and one for the modal that pops up.
    maced_html_code, maced_modal_html_code = build_templates(
        builder=context[item_name + "_builder"], html_code_dictionary=html_code_dictionary, item_id=current_item_id
    )

    context[item_name + "_item"] = maced_html_code
    context["individual_maced_modals"][item_name] = maced_modal_html_code  # This will be added to "maced_modals" later
    context[item_name + "_item_options_list"] = item_options_list


# A nice helper function to simplify code for whoever is using this app. Since current_item_id is required, this makes
# getting it much easier. In many cases you don't need a current_item_id and should use 0 instead.
def get_current_item_id(model_instance, field_name):
    if model_instance is None:
        return 0

    if not isinstance(field_name, (str, unicode)):
        raise TypeError("field_name must be a string")

    if field_name == "":
        raise ValueError("field_name must not be an empty string")

    split_field_names = field_name.split(".")
    parent = model_instance
    path = model_instance.__class__.__name__

    for split_field_name in split_field_names:
        if not hasattr(parent, split_field_name):
            raise ValueError(path + " does not have the field named " + str(split_field_name))

        field = getattr(parent, split_field_name)

        if field is None:
            return 0

        parent = field
        path += "." + split_field_name

    # Ignore this warning. It is not possible to have a split_field_names length of 0, and even if it were possible,
    # catching that situation doesn't stop compilers from complaining about this anyway.
    return field.id


# This function just does some serialization before pushing to the frontend. MUST be called after all html code has been
# generated and should only be called once
def finalize_context_for_items(context, login_url=None):
    if "maced_data" not in context:
        raise RuntimeError("maced_items is not configured correctly. Please check why maced_data is missing from the context.")

    maced_data = context["maced_data"]

    if "urls" not in maced_data or "field_names" not in maced_data or "field_identifiers" not in maced_data:
        raise RuntimeError(
            "ERROR: maced_items is not configured correctly. Please check why urls and/or field_names and/or "
            "field_identifiers is missing from the context."
        )

    maced_data["urls"] = json.dumps(maced_data["urls"])
    maced_data["field_names"] = json.dumps(maced_data["field_names"])
    maced_data["field_identifiers"] = json.dumps(maced_data["field_identifiers"])
    maced_data["login_url"] = json.dumps(login_url)

    delete_list = ("_builder", "_item_options_list", "_dependencies")

    for key in context.keys():
        if any(delete_item in key for delete_item in delete_list):
            del context[key]

    for item_name in maced_data["items_to_remove"]:
        del context[item_name + "_item"]
        del context["individual_maced_modals"][item_name]

    for item_name in context["individual_maced_modals"]:
        context["maced_modals"] += context["individual_maced_modals"][item_name]


# original_dictionary is the dictionary that is being built up for a particular maced_item object.
#   When it is complete, it should be sent to get_context_data_for_maced_items to be added to the context.
# item_name is the name of the model.
# field_type is small set of predefined constants to support various html input types.
# field_html_name is the name that will be shown to the user for the modal that pops up after clicking add, edit, merge
#   or delete
# field_name is the name of the field on the model
# extra_info is an optional parameter that is used for special purposes depending on the item_type if the type uses it.
#   Example: Select uses extra_info for options information
def insert_items_html_code(original_dictionary, item_name, field_type, field_html_name, field_name, extra_info=None):
    if field_type == "maced":
        for action_type in PRIMARY_ACTION_TYPES:
            original_dictionary[item_name][action_type] += get_items_html_code_for_maced(item_name, action_type, field_html_name, field_name, extra_info)
    elif field_type == "text":
        for action_type in PRIMARY_ACTION_TYPES:
            original_dictionary[item_name][action_type] += get_items_html_code_for_text(item_name, action_type, field_html_name, field_name)
    elif field_type == "color":
        for action_type in PRIMARY_ACTION_TYPES:
            original_dictionary[item_name][action_type] += get_items_html_code_for_color(item_name, action_type, field_html_name, field_name)
    elif field_type == "select":
        for action_type in PRIMARY_ACTION_TYPES:
            original_dictionary[item_name][action_type] += get_items_html_code_for_select(item_name, action_type, field_html_name, field_name, extra_info)
    else:
        raise TypeError("field_type of " + str(field_type) + " is not supported yet. (maced_items.py:insert_items_html_code())")


# Later, restrictions will be applied to incorporate permissions/public/private/etc.
def get_items(item_model, field_to_order_by=None):
    if field_to_order_by is None:
        items = item_model.objects.all()
    else:
        items = item_model.objects.all().order_by(field_to_order_by)

    return items






















def build_html_code(context, item_options_list, item_name, item_html_name, field_list):
    maced_data = context["maced_data"]
    html_code_dictionary = {}
    html_code_dictionary[item_name] = {}

    for action_type in PRIMARY_ACTION_TYPES:
        html_code_dictionary[item_name][action_type] = ""

    maced_object_option_html_code = get_html_code_for_options(item_options_list)

    # Merge has special html before the regular html
    merge_context = {}
    merge_context["item_name"] = item_name
    merge_context["item_html_name"] = item_html_name
    merge_context["maced_object_option_html_code"] = maced_object_option_html_code
    html_code_dictionary[item_name][MERGE] = render(
        request=None, template_name="maced/merge_table_row_1.html", context=merge_context
    ).content

    # Create html input fields for each field on the model
    for field in field_list:
        extra_info = None

        if "name" not in field:
            raise ValueError("Field in field_list is missing \"name\"")

        if "type" not in field:
            field["type"] = "text"

        if field["type"] not in VALID_INPUT_TYPES:
            raise ValueError(
                "Field named \"" + str(field["name"]) + "\" in field_list for \"" + str(item_name) + "\" has a type " +
                "of \"" + str(field["type"]) + "\" which is invalid"
            )

        if field["type"] == "select":
            if "select_type" not in field:
                field["select_type"] = "object"

            if field["select_type"] not in VALID_SELECT_TYPES:
                raise ValueError(
                    "The select for the field named \"" + str(field["name"]) + "\" has a type of \"" +
                    str(field["select_type"]) + "\" which is invalid"
                )

            if "options" in field:
                extra_info = field["options"]

                # Will raise errors if invalid, else it move on
                validate_select_options(extra_info, field, item_name, field["select_type"])
            else:
                raise ValueError(
                    "Field \"" + str(field["name"]) + "\" in field_list for \"" + str(item_name) + "\" " +
                    "is set to type \"select\", but doesn't have \"options\""
                )

        if field["type"] == "maced":
            if "maced_name" not in field:
                field["maced_name"] = field["name"]

            if field["maced_name"] + "_item" not in context:
                raise ValueError(
                    "Field named \"" + str(field["name"]) + "\" in field_list for \"" + str(item_name) + "\"" +
                    " is set as type \"maced\" and is referencing \"" + str(field["maced_name"]) + "\" but it is not " +
                    "in the context. Please make sure you have created a maced item for it and ensure that it is " +
                    "created prior to this one. If you are trying to use an object with a name different from the " +
                    "name given for \"name\" for this field, please use \"maced_name\" to specify the name you want. " +
                    "By default, \"name\" is used."
                )

            if item_name + "_dependencies" not in context:
                raise RuntimeError("\"" + item_name + "_dependencies\" was not in the context. Did you overwrite it?")

            if field["maced_name"] + "_builder" not in context:
                raise RuntimeError("\"" + item_name + "_builder\" was not in the context. Did you overwrite it?")

            # Add this maced item as a dependency of the main item
            dependency = {}
            dependency["maced_name"] = field["maced_name"]
            dependency["builder"] = context[field["maced_name"] + "_builder"]

            context[item_name + "_dependencies"].append(dependency)

            extra_info = {}
            extra_info["maced_item_html_code"] = context[field["maced_name"] + "_item"]
            extra_info["maced_name"] = field["maced_name"]
            extra_info["context"] = context

        if "html_name" not in field:
            field["html_name"] = prettify_string(field["name"])

        # Form the html based on the info from field
        insert_items_html_code(html_code_dictionary, item_name, field["type"], field["html_name"], field["name"], extra_info)

        # Lastly add the field info to the context
        maced_data["field_names"][item_name].append(field["name"])
        maced_data["field_identifiers"][item_name].append(field["name"])

    # Merge has special html after the regular html
    html_code_dictionary[item_name][MERGE] += "</table>"

    return html_code_dictionary


def build_url(item_name, name_of_app_with_url):
    url_name = name_of_app_with_url + ".maced_" + item_name
    url = reverse(url_name)

    return url


def build_builder(item_name, item_html_name, item_model, field_to_order_by, url, item_options_list, field_list, allow_empty):
    builder = {}
    builder["item_name"] = item_name
    builder["item_html_name"] = item_html_name
    builder["items"] = get_items(item_model, field_to_order_by)
    builder["item_options_list"] = item_options_list
    builder["field_list"] = field_list
    builder["url"] = url
    builder["allow_empty"] = allow_empty

    return builder


def build_templates(builder, html_code_dictionary, item_id):
    subcontext = deepcopy(builder)
    item_name = subcontext["item_name"]

    subcontext["item_id"] = item_id
    subcontext["add_html_code"] = html_code_dictionary[item_name][ADD]
    subcontext["edit_html_code"] = html_code_dictionary[item_name][EDIT]
    subcontext["merge_html_code"] = html_code_dictionary[item_name][MERGE]
    subcontext["delete_html_code"] = html_code_dictionary[item_name][DELETE]

    maced_html_code = render(request=None, template_name="maced/container.html", context=subcontext).content
    maced_modal_html_code = render(request=None, template_name="maced/modal_list.html", context=subcontext).content

    return maced_html_code, maced_modal_html_code
























# MACED
def get_items_html_code_for_maced(item_name, action_type, field_html_name, field_name, maced_info):
    context = maced_info["context"]
    item_options_list = context[maced_info["maced_name"] + "_item_options_list"]

    if action_type == ADD or action_type == EDIT:
        maced_name = maced_info["maced_name"]
        maced_data = context["maced_data"]
        item_path = item_name + "-" + field_name
        full_item_name = get_prefixed_item_path(action_type, item_path)
        initialize_fields_for_item_in_maced_data(maced_data, full_item_name)

        # This function will handle the field_name, field_identifier, item_name, and url additions to the context
        html_code = get_html_code_for_maced_fields(
            context=context, maced_name=maced_name, action_type=action_type, item_path=item_path
        )
    elif action_type == MERGE:
        options_html_code = get_html_code_for_options(item_options_list)

        html_code = get_merge_html_code_for_select(item_name, field_html_name, field_name, options_html_code)
    else:
        options_html_code = get_html_code_for_options(item_options_list)

        html_code = '<b class="maced">' + field_html_name + ': </b>'
        html_code += '<select class="maced form-control" id="' + action_type + '-' + item_name + '-' + field_name + '-input" '

        if action_type == DELETE or action_type == CLONE or action_type == INFO:
            html_code += 'disabled '

        html_code += '>' + options_html_code + '</select>'

    return html_code


# TEXT
def get_items_html_code_for_text(item_name, action_type, field_html_name, field_name):
    if action_type == MERGE:
        return get_merge_html_code_for_text(item_name, field_html_name, field_name)

    html_code = '<b class="maced">' + field_html_name + ': </b>'
    html_code += '<input type="text" class="maced form-control" id="' + action_type + '-' + item_name + '-' + field_name + '-input" '

    if action_type == DELETE or action_type == CLONE or action_type == INFO:
        html_code += 'disabled '

    html_code += '/>'

    return html_code


def get_merge_html_code_for_text(item_name, field_html_name, field_name):
    # Create row name
    html_code = '<tr class="maced">'
    html_code += '<th class="maced">' + field_html_name + ': </th>'

    # Create left panel
    html_code += \
        '<td class="maced">' \
            '<input type="text" class="maced form-control" id="merge-' + item_name + '1-' + field_name + '-input" readonly />' \
        '</td>'

    html_code += '<th class="maced"> <button type="button" class="maced glyphicon glyphicon-arrow-right" style="color: Green; font-size: 20px"></button> </th>'

    # Create middle panel
    html_code += \
        '<td class="maced" style="background-color: #F7D358;">' \
            '<input type="text" class="maced form-control" id="merge-' + item_name + '-' + field_name + '-input" />' \
        '</td>'

    html_code += '<th class="maced"> <button type="button" class="maced glyphicon glyphicon-arrow-left" style="color: Green; font-size: 20px"></button> </th>'

    # Create right panel for merge
    html_code += \
        '<td class="maced">' \
            '<input type="text" class="maced form-control" id="merge-' + item_name + '2-' + field_name + '-input" readonly />' \
        '</td>'

    html_code += '</tr>'

    return html_code


# COLOR
def get_items_html_code_for_color(item_name, action_type, field_html_name, field_name):
    if action_type == MERGE:
        return get_merge_html_code_for_color(item_name, field_html_name, field_name)

    html_code = '<b class="maced">' + field_html_name + ': </b>'
    html_code += '<input type="color" class="maced form-control" id="' + action_type + '-' + item_name + '-' + field_name + '-input" value="#00FF00" '

    if action_type == DELETE or action_type == CLONE or action_type == INFO:
        html_code += 'disabled '

    html_code += '/>'

    return html_code


def get_merge_html_code_for_color(item_name, field_html_name, field_name):
    # Create row name
    html_code = '<tr class="maced">'
    html_code += '<th class="maced">' + field_html_name + ': </th>'

    # Create left panel
    html_code += \
        '<td class="maced">' \
            '<input type="color" class="maced form-control" id="merge-' + item_name + '1-' + field_name + '-input" value="#00FF00" disabled />' \
        '</td>'

    # Create middle panel
    html_code += \
        '<td class="maced" style="background-color: #F7D358;">' \
            '<input type="color" class="maced form-control" id="merge-' + item_name + '-' + field_name + '-input" value="#00FF00" />' \
        '</td>'

    # Create right panel for merge
    html_code += \
        '<td class="maced">' \
            '<input type="color" class="maced form-control" id="merge-' + item_name + '2-' + field_name + '-input" value="#00FF00" disabled />' \
        '</td>'

    html_code += '</tr>'

    return html_code


# SELECT
def get_items_html_code_for_select(item_name, action_type, field_html_name, field_name, options_info):
    options_html_code = get_html_code_for_options(options_info)

    if action_type == MERGE:
        return get_merge_html_code_for_select(item_name, field_html_name, field_name, options_html_code)

    html_code = '<b class="maced">' + field_html_name + ': </b>'
    html_code += '<select class="maced form-control" id="' + action_type + '-' + item_name + '-' + field_name + '-input" '

    if action_type == DELETE or action_type == CLONE or action_type == INFO:
        html_code += 'disabled '

    html_code += '>' + options_html_code + '</select>'

    return html_code


def get_merge_html_code_for_select(item_name, field_html_name, field_name, options_html_code):
    # Create row name
    html_code = '<tr class="maced">'
    html_code += '<th class="maced">' + field_html_name + ': </th>'

    # Create left panel
    html_code += \
        '<td class="maced">' \
            '<select class="maced form-control" id="merge-' + item_name + '1-' + field_name + '-input" readonly ' \
                'onfocus="this.defaultIndex=this.selectedIndex;" onchange="this.selectedIndex=this.defaultIndex;">' + \
                options_html_code + \
            '</select>' \
        '</td>'

    # Create middle panel
    html_code += \
        '<td class="maced" style="background-color: #F7D358;">' \
            '<select class="maced form-control" id="merge-' + item_name + '-' + field_name + '-input">' + options_html_code + '</select>' \
        '</td>'

    # Create right panel for merge
    html_code += \
        '<td class="maced">' \
            '<select class="maced form-control" id="merge-' + item_name + '2-' + field_name + '-input" readonly ' \
                'onfocus="this.defaultIndex=this.selectedIndex;" onchange="this.selectedIndex=this.defaultIndex;">' + \
                options_html_code + \
            '</select>' \
        '</td>'

    html_code += '</tr>'

    return html_code


# OPTIONS FOR SELECT
def get_html_code_for_options(options_list, selected_index=None):
    html_code = ''

    for i in range(len(options_list)):
        html_code += '<option class="maced" value="' + str(options_list[i][0]) + '" '

        if i == selected_index:
            html_code += 'selected'

        html_code += '> ' + str(options_list[i][1]) + ' </option>'

    return html_code


# OTHER
# Search dependencies and change their ids to the full path
def get_html_code_for_maced_fields(context, maced_name, action_type, item_path):
    dependencies = context[maced_name + "_dependencies"]
    maced_data = context["maced_data"]
    html_code_to_return = ""

    for dependency in dependencies:
        childs_maced_name = dependency["maced_name"]
        parents_name_for_child = dependency["parents_name_for_child"]
        child_builder = deepcopy(dependency["builder"])  # Let's build some children. :)
        child_item_path = item_path + "-" + parents_name_for_child

        # Modify the item_name to the complex path
        full_child_name = get_prefixed_item_path(action_type, child_item_path)
        initialize_fields_for_item_in_maced_data(maced_data, full_child_name)
        child_builder["item_name"] = full_child_name

        # Build the special python-html
        html_code_dictionary = build_html_code(
            context=context, item_options_list=child_builder["item_options_list"],
            item_name=child_builder["item_name"], item_html_name=child_builder["item_html_name"],
            field_list=child_builder["field_list"]
        )

        # Build the templates
        maced_html_code, maced_modal_html_code = build_templates(
            builder=child_builder, html_code_dictionary=html_code_dictionary, item_id=0
        )

        # Add the template to the blob
        html_code_to_return += maced_html_code

        # Add the modal the the list of modals
        context["maced_modals"] += maced_modal_html_code

        # Add the other pieces to the context. maced_data is a part of the context
        maced_data["item_names"].append(full_child_name)
        maced_data["urls"][full_child_name] = maced_data["urls"][childs_maced_name]

        # Now go recursive and go down a child generation and add it to the blob
        html_code_to_return += get_html_code_for_maced_fields(
            context=context, maced_name=childs_maced_name, action_type=action_type,
            item_path=child_item_path
        )

    builder = deepcopy(context[maced_name + "_builder"])

    # Modify the item_name to the complex path
    full_name = get_prefixed_item_path(action_type, item_path)
    builder["item_name"] = full_name

    # Build the special python-html
    html_code_dictionary = build_html_code(
        context=context, item_options_list=builder["item_options_list"], item_name=builder["item_name"],
        item_html_name=builder["item_html_name"], field_list=builder["field_list"]
    )

    # Build the templates
    maced_html_code, maced_modal_html_code = build_templates(
        builder=builder, html_code_dictionary=html_code_dictionary, item_id=0
    )

    # Add the template to the blob
    html_code_to_return += maced_html_code

    # Add the modal the the list of modals
    context["maced_modals"] += maced_modal_html_code

    # Add the other pieces to the context. maced_data is part of the context
    maced_data["item_names"].append(full_name)
    maced_data["urls"][full_name] = maced_data["urls"][maced_name]

    return html_code_to_return


# Gets the special path for a given action_type
def get_prefixed_item_path(action_type, path):
    return action_type + "_type-" + path


# Simply creates an entry into the maced_data dictionary as a list so that things can be appended later.
def initialize_fields_for_item_in_maced_data(maced_data, item_name):
    maced_data["field_names"][item_name] = []
    maced_data["field_identifiers"][item_name] = []
