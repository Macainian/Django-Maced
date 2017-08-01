import inspect
import logging

import sys
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from maced.utils.constants import GET, MERGE, ADD, EDIT, CLONE
from maced.utils.misc import prettify_string

logger = logging.getLogger("maced")

if sys.version_info > (3, 0):
    STR_UNICODE_TUPLE = (str, )
else:
    STR_UNICODE_TUPLE = (str, unicode)


def get_and_validate_kwargs(**kwargs):
    if "need_authentication" in kwargs:
        need_authentication = kwargs["need_authentication"]

        if not isinstance(need_authentication, bool):
            message = "need_authentication must be a bool"
            logger.error(message)

            return HttpResponse(content=message, status=500)
    else:
        need_authentication = True

    if "item_name_field_name" in kwargs:
        item_name_field_name = kwargs["item_name_field_name"]
    else:
        item_name_field_name = "name"

    # Get the item class
    if "item_model" in kwargs:
        item_model = kwargs["item_model"]

        # This should really be checking if it is a model, not a class.
        if not inspect.isclass(item_model):
            message = "item_model was not a class."
            logger.error(message)

            return HttpResponse(content=message, status=500)
    else:
        message = "item_model was not in the kwargs."
        logger.error(message)

        return HttpResponse(content=message, status=500)

    # Get any model_dependency_tuples
    if "model_dependency_tuples" in kwargs:
        model_dependency_tuples = kwargs["model_dependency_tuples"]

        if isinstance(model_dependency_tuples, list):
            count = 0

            for model_dependency_tuple in model_dependency_tuples:
                if isinstance(model_dependency_tuple, tuple):
                    if len(model_dependency_tuple) == 2 or len(model_dependency_tuple) == 3:
                        if isinstance(model_dependency_tuple[0], STR_UNICODE_TUPLE):
                            # This should really be checking if it is a model, not a class.
                            if inspect.isclass(model_dependency_tuple[1]):
                                if len(model_dependency_tuple) == 3:
                                    if isinstance(model_dependency_tuple[2], bool):
                                        if not model_dependency_tuple[2]:
                                            message = "Select object model number " + str(count) + \
                                                      "'s tuple's inheritance bool must not be False."
                                            logger.error(message)

                                            return HttpResponse(content=message, status=500)
                                    else:
                                        message = "Select object model number " + str(count) + \
                                                  "'s tuple's inheritance bool is not a bool."
                                        logger.error(message)

                                        return HttpResponse(content=message, status=500)
                            else:
                                message = "Select object model number " + str(count) + \
                                          "'s tuple's model is not a class."
                                logger.error(message)

                                return HttpResponse(content=message, status=500)
                        else:
                            message = "Select object model number " + str(count) + \
                                      "'s tuple's field name is not a string."
                            logger.error(message)

                            return HttpResponse(content=message, status=500)
                    else:
                        message = "Select object model number " + str(count) + " is a tuple of size " + \
                                  str(len(model_dependency_tuple)) + " but should be size of 2 like this " + \
                                  "(field_name, class), or a size of 3 like this " + \
                                  "(pointer_field_name, parent_class, True)"
                        logger.error(message)

                        return HttpResponse(content=message, status=500)
                else:
                    message = "Select object model number " + str(count) + " is not a tuple."
                    logger.error(message)

                    return HttpResponse(content=message, status=500)

                count += 1
        else:
            message = "select_object_models must be a list."
            logger.error(message)

            return HttpResponse(content=message, status=500)
    else:
        model_dependency_tuples = None

    if "required_fields" in kwargs:
        required_fields = kwargs["required_fields"]

        if isinstance(required_fields, list):
            for i in range(len(required_fields)):
                if not isinstance(required_fields[i], STR_UNICODE_TUPLE):
                    message = "Required field number " + str(i) + " is not a string."
                    logger.error(message)

                    return HttpResponse(content=message, status=500)
        else:
            message = "required_fields must be a list."
            logger.error(message)

            return HttpResponse(content=message, status=500)
    else:
        required_fields = []

    required_fields.append(item_name_field_name)

    # Get any hidden_field_tuples
    if "hidden_field_tuples" in kwargs:
        hidden_field_tuples = kwargs["hidden_field_tuples"]

        if isinstance(hidden_field_tuples, list):
            count = 0

            for hidden_field_tuple in hidden_field_tuples:
                if isinstance(hidden_field_tuple, tuple):
                    if len(hidden_field_tuple) == 2:
                        if isinstance(hidden_field_tuple[0], STR_UNICODE_TUPLE):
                            if not isinstance(hidden_field_tuple[1], STR_UNICODE_TUPLE) and hidden_field_tuple[1] is not None:
                                message = "Hidden field tuple number " + str(count) + \
                                          "'s model is not a string nor None."
                                logger.error(message)

                                return HttpResponse(content=message, status=500)
                        else:
                            message = "Hidden field tuple number " + str(count) + \
                                      "'s field name is not a string."
                            logger.error(message)

                            return HttpResponse(content=message, status=500)
                    else:
                        message = "Hidden field tuple number " + str(count) + " is a tuple of size " + \
                                  str(len(hidden_field_tuple)) + " but should be size of 2 like this " + \
                                  "(field_name_for_created_by_or_updated_by, attribute_name_in_user_model). For " + \
                                  "the second part of the tuple, it is referring to request.user.ATTRIBUTE_NAME, " + \
                                  "if you are using user itself, use None."
                        logger.error(message)

                        return HttpResponse(content=message, status=500)
                else:
                    message = "Hidden field tuple number " + str(count) + " is not a tuple."
                    logger.error(message)

                    return HttpResponse(content=message, status=500)

                count += 1
        else:
            message = "hidden_field_tuples must be a list."
            logger.error(message)

            return HttpResponse(content=message, status=500)
    else:
        hidden_field_tuples = None

    return \
        need_authentication, item_name_field_name, item_model, model_dependency_tuples, required_fields, \
        hidden_field_tuples


# It is assumed that required_fields and hidden_field_tuples have been validated by this point.
# They should have been checked in get_and_validate_kwargs_view().
def get_post_data(request, item_model, item_name_field_name, action_type, required_fields, hidden_field_tuples):
    # Get all fields on the model
    fields = item_model._meta.fields

    fields_to_save = {}
    missing_field_names = []

    # Build a list of potential fields to fill in
    for field in fields:
        fields_to_save[field.name] = request.POST.get(field.name, "")
        field_is_missing = False

        if fields_to_save[field.name] == "":
            if hidden_field_tuples:
                for hidden_field_tuple in hidden_field_tuples:
                    if field.name == hidden_field_tuple[0]:
                        if hidden_field_tuple[1] is None:
                            fields_to_save[field.name] = request.user
                        else:
                            fields_to_save[field.name] = getattr(request.user, hidden_field_tuple[1]).id

                        break
                else:
                    # For-else means if it wasn't found
                    field_is_missing = True
            else:
                field_is_missing = True

            if field_is_missing:
                missing_field_names.append(field.name)
                fields_to_save.pop(field.name, None)

    message = ""
    has_missing_required_fields = False

    if action_type == MERGE or action_type == ADD or action_type == CLONE or action_type == EDIT:
        # Check if other required fields are missing from the post
        for missing_field_name in missing_field_names:
            if missing_field_name in required_fields:
                message += prettify_string(missing_field_name) + " is required. "
                has_missing_required_fields = True

        # If anything was missing, return an error with the list of missing required fields
        if has_missing_required_fields:
            logger.error(message)

            return HttpResponse(content=message, status=500)

        item_name = fields_to_save[item_name_field_name]  # This will be in the list if we made it this far
    else:
        item_name = None

    item_id = None
    item2_id = None

    if "item_id" in request.POST:
        item_id = request.POST["item_id"]

    # This will only be sent if it is a merge
    if "item2_id" in request.POST:
        item2_id = request.POST["item2_id"]

    return fields_to_save, item_name, item_id, item2_id


# It is assumed that model_dependency_tuples has been validated by this point.
# It should have been checked in get_and_validate_kwargs_view().
def convert_foreign_keys_to_objects(fields_to_save, model_dependency_tuples, action_type):
    if model_dependency_tuples is None:
        return True  # True just means it succeeded (there was nothing to do).

    for model_dependency_tuple in model_dependency_tuples:
        field_name1 = model_dependency_tuple[0]

        # If this entry is for inheritance and we are not doing a get_item call
        if len(model_dependency_tuple) == 3 and action_type != GET:
            continue

        for field_name2, field_value in fields_to_save.items():
            if field_name2 == field_name1:
                if field_value == "":
                    break

                try:
                    fields_to_save[field_name2] = model_dependency_tuple[1].objects.get(id=field_value)
                except ObjectDoesNotExist:
                    message = "Tried to load id " + field_value + " on model named \"" + \
                              model_dependency_tuple[1].__name__ + "\" to be used with field named \"" + \
                              field_name2 + "\". (item_action_helpers:convert_foreign_keys_to_objects)"
                    logger.error(message)

                    return HttpResponse(content=message, status=500)
                break
        else:
            message = "Could not find field name of \"" + field_name1 + "\" associated with the model named \"" + \
                      model_dependency_tuple[1].__name__ + "\" in fields_to_save. Check for typos in " + \
                      "kwargs and item_names. (item_action_helpers:convert_foreign_keys_to_objects)"
            logger.error(message)

            return HttpResponse(content=message, status=500)

    return True  # True just means it succeeded.


# It is assumed that model_dependency_tuples has been validated by this point.
# It should have been checked in get_and_validate_kwargs_view().
def convert_objects_to_foreign_keys(fields_to_load, model_dependency_tuples):
    if model_dependency_tuples is None:
        return True  # True just means it succeeded (there was nothing to do).

    for model_dependency_tuple in model_dependency_tuples:
        field_name1 = model_dependency_tuple[0]

        for field_name2, field_value in fields_to_load.items():
            if field_name2 == field_name1:
                try:
                    fields_to_load[field_name2] = field_value.id
                except AttributeError:
                    message = "Tried to get id from model but \"" + field_value.__class__.__name__ + \
                              "\" is not a model. Please check kwargs and item_names for a field named \"" + \
                              field_name2 + "\" and check for typos. " + \
                              "(item_action_helpers:convert_objects_to_foreign_keys)"
                    logger.error(message)

                    return HttpResponse(content=message, status=500)
                break
        else:
            message = "Could not find field name of \"" + field_name1 + "\" associated with the model named \"" + \
                      model_dependency_tuple[1].__name__ + "\" in fields_to_load. Check for typos in " + \
                      "kwargs and item_names. (item_action_helpers:convert_objects_to_foreign_keys)"
            logger.error(message)

            return HttpResponse(content=message, status=500)

    return True  # True just means it succeeded (there was nothing to do).
