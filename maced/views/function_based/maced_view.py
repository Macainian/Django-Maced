import json
import logging

import sys
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from maced.utils.constants import MERGE, ADD, CLONE, EDIT, DELETE, GET, INFO, AUTHENTICATE, ALL_ACTION_TYPES
from maced.utils.errors import MacedProgrammingError
from maced.utils.item_action_helpers import get_and_validate_kwargs, get_post_data, convert_foreign_keys_to_objects
from maced.utils.item_actions import merge_item, add_item, clone_item, edit_item, delete_item, get_item, info_item, \
    get_authentication
from maced.utils.misc import serialize_item_action_data


logger = logging.getLogger("maced")

if (sys.version_info > (3, 0)):
    STR_UNICODE_TUPLE = (str, )
else:
    STR_UNICODE_TUPLE = (str, unicode)


@transaction.atomic
@csrf_exempt
def maced_view(request, **kwargs):
    # need_authentication is a bool that defaults to True and is used to determined whether a login is required
    # item_name_field_name is what the name value will correspond to in the database. This defaults to name.
    #       It will be used like ObjectToCreate(name=some_name), where name is the default value but it could be
    #       something else.
    # item_model is the model that the item is referring to. This is the class, not an instance.
    # model_dependency_tuples is the info supplied by the kwargs that is related to selects using objects for their
    #       options.
    # data is the necessary info to send back through the ajax call in order to handle the frontend properly.
    # fields_to_save are the fields found in the post
    # item_name is the name field's value that was found in the post
    # item_id is the id of the first item being used. If you are using add or authenticate, this will be None.
    # item2_id is the id of the second item being used. This only applies to merge.

    # Make sure kwargs were set up right
    kwargs_result = get_and_validate_kwargs(**kwargs)

    # This will be a tuple as long as it succeeded, otherwise it will be an HttpResponse
    if not isinstance(kwargs_result, tuple):
        return kwargs_result

    need_authentication = kwargs_result[0]
    item_name_field_name = kwargs_result[1]
    item_model = kwargs_result[2]
    model_dependency_tuples = kwargs_result[3]
    required_fields = kwargs_result[4]
    hidden_field_tuples = kwargs_result[5]

    data = {}

    # Authenticate the user
    if request.user.is_authenticated or not need_authentication:
        data["authenticated"] = True
    else:
        data["authenticated"] = False

        return HttpResponse(content=json.dumps(data))

    # Get the action_type
    if "action_type" not in request.POST:
        message = "action_type is missing from the post."
        logger.error(message)

        return HttpResponse(content=message, status=500)

    action_type = request.POST["action_type"]

    if action_type not in ALL_ACTION_TYPES:
        message = "action_type of \"" + str(action_type) + "\" is not valid."
        logger.error(message)

        return HttpResponse(content=message, status=500)

    if action_type == AUTHENTICATE:
        action_result = get_authentication(request=request, need_authentication=need_authentication)
    else:
        # Get all the fields that were given in the post, along with the item_name (the value associated with the
        # item_name_field_name)
        fields_result = get_post_data(
            request=request, item_model=item_model, item_name_field_name=item_name_field_name, action_type=action_type,
            required_fields=required_fields, hidden_field_tuples=hidden_field_tuples
        )

        # This will be a tuple as long as it succeeded, otherwise it will be an HttpResponse
        if not isinstance(fields_result, tuple):
            return fields_result

        fields_to_save = fields_result[0]
        item_name = fields_result[1]
        item_id = fields_result[2]
        item2_id = fields_result[3]

        # If merging, adding, or editing, we ned to convert the number values for foreign keys into their actual objects
        if action_type == MERGE or action_type == ADD or action_type == EDIT:
            conversion_result = convert_foreign_keys_to_objects(fields_to_save, model_dependency_tuples, action_type)

            # This will be a bool as long as it succeeded, otherwise it will be an HttpResponse. Since there are no safe
            # failures for this, there will never need to be a False returned.
            if not isinstance(conversion_result, bool):
                return conversion_result

        # Branch off to whichever action we are performing
        if action_type == MERGE:
            action_result = merge_item(
                item_model=item_model, fields_to_save=fields_to_save, item_name=item_name, item1_id=item_id,
                item2_id=item2_id, item_name_field_name=item_name_field_name
            )
        elif action_type == ADD:
            action_result = add_item(item_model=item_model, fields_to_save=fields_to_save, item_name=item_name)
        elif action_type == CLONE:
            action_result = clone_item()
        elif action_type == EDIT:
            action_result = edit_item(
                item_model=item_model, fields_to_save=fields_to_save, item_name=item_name, item_id=item_id
            )
        elif action_type == DELETE:
            action_result = delete_item(item_model=item_model, item_id=item_id)
        elif action_type == GET:
            action_result = get_item(item_model, model_dependency_tuples=model_dependency_tuples, item_id=item_id)
        elif action_type == INFO:
            action_result = info_item()
        else:
            raise MacedProgrammingError(
                "action_type is valid but is not being supported. This is a problem with maced. Please notify us at " +
                "https://github.com/Macainian/Django-Maced/issues"
            )

    # This will be a dictionary as long as it succeeded, otherwise it will be an HttpResponse
    if not isinstance(action_result, dict):
        return action_result

    data_json_string = serialize_item_action_data(action_result)

    # This will be a string as long as it succeeded, otherwise it will be an HttpResponse
    if not isinstance(data_json_string, STR_UNICODE_TUPLE):
        return data_json_string

    return HttpResponse(content=data_json_string)
