import yaml
import re
from rest_helpers import routes,jsonapi_objects, binding, validators, type_deserializers, routes

SWAGGER_AUGMENT_DEFAULT_KEY = "augment_default"
SWAGGER_EXTRA_DEFINITION_KEY = "extra_definition"
SWAGGER_DOCUMENTATION_KEY = "doc"
SWAGGER_PARAMETER_KEY = "parameters"
SWAGGER_JSONAPI_RESPONSE_DEFINITION_KEY = "jsonapi_response"

_swagger_object_classes = [jsonapi_objects.ErrorResponse, jsonapi_objects.SuccessResponse]

def get_swagger_service_description(source):
    """
    This function gets the full swagger spec for a given service.
    
    Arguments:
        source {dict|func|class} -- The source can be either a dictionary containing the high
                                    level description of the service or a func/class whose
                                    docstring contains the service high level description as a
                                    yaml blob under a 'Swagger doc:' line.
    
    Returns:
        dict -- the swagger description of the service.
    """

    default_service_description = {
        "swagger": "2.0",
        "info": {
            "description" : "A new service",
            "version" : "1.0.0",
            "title" : "New Service title",
            "contact" : {
                "email": "noreply@abc.com"
            }
        },
        "host": "service.domain.com",
        "basePath": "",
        "tags":[],
        "schemes": ["http"],
        "paths":get_swagger_paths(),
        "definitions":get_swagger_definitions()
    }

    if isinstance(source, dict):
        augment_dic = source
    else:
        augment_dic =  _get_swagger_part(source, SWAGGER_DOCUMENTATION_KEY)

    _update(default_service_description, augment_dic)

    return default_service_description


def swagger_object(cls):
    _swagger_object_classes.append(cls)
    return cls


def get_swagger_definitions():
    return_value = {}
    for swagger_obj in _swagger_object_classes:
        if issubclass(swagger_obj, jsonapi_objects.Resource):
            swagger_obj_type = _get_swagger_type(swagger_obj)

            jsonapi_response_def = _get_swagger_part(swagger_obj, SWAGGER_JSONAPI_RESPONSE_DEFINITION_KEY)
            if jsonapi_response_def is not None:
                inner_type = "{0}_data".format(swagger_obj_type)
                swagger_array_obj_type = "{0}_array".format(swagger_obj_type)
                return_value[swagger_obj_type] = {
                    "type": "object",
                    "allOf": [{"$ref": "#/definitions/response"}],
                    "properties":{
                        "data": {"$ref":"#/definitions/{0}".format(inner_type)}
                        }
                }
                return_value[swagger_array_obj_type] = {
                    "type": "object",
                    "allOf": [{"$ref": "#/definitions/response"}],
                    "properties":{
                        "data": {
                            "type":"array",
                            "items":{
                                "$ref": "#/definitions/{0}".format(inner_type)
                            }
                        }
                    }
                }

                return_value[inner_type] = {
                    "type": "object",
                    "properties":{
                        "attributes":{
                            "type": "object",
                            "properties": jsonapi_response_def
                        }
                    }
                }
            else:
                return_value[swagger_obj_type] = _get_swagger_part(swagger_obj, SWAGGER_DOCUMENTATION_KEY)


        extra_definitions = _get_swagger_part(swagger_obj, SWAGGER_EXTRA_DEFINITION_KEY)
        _update(return_value, extra_definitions)
    return return_value


def get_swagger_paths():
    return_value = {}
    for route in routes._swagger_routes:
        existing_doc = _get_swagger_part(route.view_function, SWAGGER_DOCUMENTATION_KEY)
        key = "/"+route.rule.replace("<","{").replace(">","}").strip(" /")
        if key not in return_value:
            return_value[key] = {}

        _update(return_value[key], _get_default_swagger_path(route))
        _update(return_value[key][next(iter(return_value[key].keys()))], existing_doc)

        augment_dic = _get_swagger_part(route.view_function, SWAGGER_AUGMENT_DEFAULT_KEY)
        if augment_dic is not None:
            _update(return_value[key], { route.options["methods"][0].lower() : augment_dic})
    return return_value


def _get_swagger_type(resource_class):
    return resource_class.resource_type.replace("/","")


def _get_swagger_part(function_or_class, key="doc"):
    doc = function_or_class.__doc__

    swagger_key = "Swagger {0}:".format(key)
    if doc is not None and swagger_key in doc:
        swagger_text = doc.split(swagger_key)[1]
        swagger_text = swagger_text.split("end swagger")[0]
        return yaml.load(swagger_text)

    return None

#region default paths
def _get_default_swagger_path(route):
    return_value = None

    if type(route) == routes.get_resource_route:
        return_value = _get_default_swagger_path_for_get_route(route)
    elif type(route) == routes.get_all_resources_route:
        return_value = _get_default_swagger_path_for_get_all_route(route)
    elif type(route) == routes.put_resource_route:
        return_value = _get_default_swagger_path_for_put_route(route)
    elif type(route) == routes.operation_resource_route:
        return_value = _get_default_swagger_path_for_op_route(route)
    elif type(route) == routes.group_operation_resource_route:
        return_value = _get_default_swagger_path_for_group_op_route(route)
    elif type(route) == routes.patch_resource_route:
        return_value = _get_default_swagger_path_for_patch_resource_route(route)

    return return_value


def _get_default_swagger_path_for_get_route(route):
    return_value = {
        "get":{
            "tags":[route.resource_class.resource_type],
            "summary": "Get by name".format(type=route.resource_class.resource_type),
            "description":"",
            "operationId": "GET_{type}".format(type=route.resource_class.resource_type),
            "produces": ["application/json"],
            "parameters": _get_parameters(route),
            "responses":{
                "200":
                {
                    "description": "successful operation",
                    "schema":
                    {
                        "$ref": "#/definitions/{type}".format(type=_get_swagger_type(route.resource_class)),
                    }
                },
                "404":
                {
                    "description": "Not found: the requested {type} could not be found.".format(type=route.resource_class.resource_type),
                    "schema":
                    {
                        "$ref": "#/definitions/error",
                    }
                }
            }
        }
    }

    return return_value


def _get_default_swagger_path_for_get_all_route(route):
    return_value = {
        "get":{
            "tags":[route.resource_class.resource_type],
            "summary": "Get all".format(type=route.resource_class.resource_type),
            "description":"",
            "operationId": "GET_ALL_{type}".format(type=route.resource_class.resource_type),
            "produces": ["application/json"],
            "parameters": _get_parameters(route),
            "responses":{
                "200":
                {
                    "description": "successful operation",
                    "schema":
                    {
                        "$ref": "#/definitions/{type}_array".format(type=_get_swagger_type(route.resource_class))
                    }
                }
            }
        }
    }

    return return_value

def _get_default_swagger_path_for_put_route(route):
    parameters = [p for p in  _get_parameters(route) if p.get("in") != "body"]
    parameters.append({
                "in": "body",
                "name": "body",
                "description": "Object to be created.",
                "required": True,
                "schema":{ "$ref": "#/definitions/{type}".format(type=_get_swagger_type(route.resource_class)) }
            })
            
    return_value = {
        "put":{
            "tags":[route.resource_class.resource_type],
            "summary": "Create or edit".format(type=route.resource_class.resource_type),
            "description":"",
            "operationId": "PUT_{type}".format(type=route.resource_class.resource_type),
            "produces": ["application/json"],
            "consumes": ["application/json"],
            "parameters": parameters,
            "responses":{
                "200":
                {
                    "description": "successful operation",
                    "schema":
                    {
                        "$ref": "#/definitions/{type}".format(type=_get_swagger_type(route.resource_class)),
                    }
                },
                "400":
                {
                    "description": "The body of the request is improperly formed.".format(type=route.resource_class.resource_type),
                    "schema":
                    {
                        "$ref": "#/definitions/error",
                    }
                }
            }
        }
    }

    return return_value

def _get_default_swagger_path_for_patch_resource_route(route):
    return_value = {
        "patch":{
            "tags":[route.resource_class.resource_type],
            "summary": "Patch resource".format(type=route.resource_class.resource_type),
            "description":"",
            "operationId": "PATCH_{type}".format(type=route.resource_class.resource_type),
            "produces": ["application/json"],
            "parameters": _get_parameters(route),
            "responses":{
                "200":
                {
                    "description": "successful operation",
                    "schema":
                    {
                        "$ref": "#/definitions/{type}".format(type=_get_swagger_type(route.resource_class)),
                    }
                },
                "400":
                {
                    "description": "The body of the request is improperly formed.".format(type=route.resource_class.resource_type),
                    "schema":
                    {
                        "$ref": "#/definitions/error",
                    }
                }
            }
        }
    }
    return return_value

def _get_default_swagger_path_for_op_route(route):
    return_value = {
        "post":{
            "tags":[route.resource_class.resource_type],
            "summary": "Operation {operation_name}".format(operation_name=route.operation_name, type=route.resource_class.resource_type),
            "description":"",
            "operationId": "POST_{operation_name}_{type}".format(operation_name=route.operation_name, type=route.resource_class.resource_type),
            "produces": ["application/json"],
            "parameters": _get_parameters(route, route.operation_name),
            "responses":{
                "200":
                {
                    "description": "successful operation",
                    "schema":
                    {
                        "$ref": "#/definitions/{type}".format(type=_get_swagger_type(route.resource_class)),
                    }
                },
                "400":
                {
                    "description": "The body of the request is improperly formed.".format(type=route.resource_class.resource_type),
                    "schema":
                    {
                        "$ref": "#/definitions/error",
                    }
                }
            }
        }
    }

    return return_value

def _get_default_swagger_path_for_group_op_route(route):
    return_value = {
        "post":{
            "tags":[route.resource_class.resource_type],
            "summary": "Group operation {operation_name}".format(operation_name=route.operation_name, type=route.resource_class.resource_type),
            "description":"",
            "operationId": "POST_GR_{operation_name}_{type}".format(operation_name=route.operation_name, type=route.resource_class.resource_type),
            "produces": ["application/json"],
            "parameters": _get_parameters(route, route.operation_name),
            "responses":{
                "200":
                {
                    "description": "successful operation",
                    "schema":
                    {
                        "$ref": "#/definitions/{type}".format(type=_get_swagger_type(route.resource_class)),
                    }
                },
                "400":
                {
                    "description": "The body of the request is improperly formed.".format(type=route.resource_class.resource_type),
                    "schema":
                    {
                        "$ref": "#/definitions/error",
                    }
                }
            }
        }
    }

    return return_value


#endregion


def _get_parameters(route, operation_name=None):
    parameter_names = re.finditer("<(\w+)>", route.rule)

    action = "to get." if operation_name is None else "to apply {operation_name} on".format(operation_name=operation_name)
    parameters = [
    {
        "name":p.group(1),
        "in":"path",
        "description":"Name of the {type} {action}".format(type=route.resource_class.resource_type, action=action) if isinstance(route, routes.base_resource_route) else "",
        "required":True,
        "type":"string"
    } for p in parameter_names]

    version_parameter = next((p for p in parameters if p["name"]=="rest_helper_version"), None)
    if version_parameter is not None:
        version_parameter["description"] = "Version of the api to use."
        version_parameter["enum"] = sorted(list(route.versionner().supported_versions.keys()), reverse=True)

    if route.id in binding._input_decorators:
        swagger_parameter_dict = _get_swagger_part(route.real_view_function, SWAGGER_PARAMETER_KEY) or {}

        def merge(x,y):
            if y is None:
                return None
            x.update(y)
            return x

        query_decorators = (p for p in binding._input_decorators[route.id] if isinstance(p, binding.from_query_string))
        query_parameters = [
        merge({
            "name":p.query_field,
            "in":"query",
            "required": not p.has_default,
            "type": _get_parameter_type(p.type)
        }, swagger_parameter_dict.get(p.query_field,{})) for p in query_decorators]
        parameters += [x for x in query_parameters if x is not None]

        header_decorators = (p for p in binding._input_decorators[route.id] if isinstance(p, binding.from_header))
        header_parameters = [
        merge({
            "name":p.header_field,
            "in":"header",
            "required": not p.has_default,
            "type": _get_parameter_type(p.type),
            "description": swagger_parameter_dict.get(p.header_field)
        }, swagger_parameter_dict.get(p.header_field,{})) for p in header_decorators]

        parameters += [x for x in header_parameters if x is not None]

        body_parameters = [p for p in binding._input_decorators[route.id] if isinstance(p, binding.from_json_body) or isinstance(p, binding.field_from_json_body)]
        if any(body_parameters) and  ("body" not in swagger_parameter_dict or swagger_parameter_dict["body"] is not None):
            body_parameters = [
            merge({
                "name":"body",
                "in":"body",
                "required": any(not p.has_default for p in body_parameters)
                },
                swagger_parameter_dict.get("body", {}))
            ]

            if body_parameters is not None:
                parameters += body_parameters
        """
        body_decorators = (p for p in binding._input_decorators[route.id] if isinstance(p, binding.from_json_body))
        body_parameters = [
        {
            "name":"body",
            "in":"body",
            "required": not p.has_default,
            "type": "object"
        } for p in body_decorators]

        parameters += body_parameters

        field_from_body_decorators = (p for p in binding._input_decorators[route.id] if isinstance(p, binding.field_from_json_body))
        field_from_body_parameters = [
        {
            "name":p.json_field,
            "in":"body",
            "required": not p.has_default,
            "type": _get_parameter_type(p.type)
        } for p in field_from_body_decorators]

        parameters += field_from_body_parameters
        """

    if type(route) == routes.get_all_resources_route and route.page_size is not None:
        parameters.append({
            "name":"page",
            "in":"query",
            "description":"The page number.",
            "required":False,
            "type":"integer"
        })

    return parameters


def _get_parameter_type(p_type):
    if p_type == bool:
        return "boolean"
    elif p_type == int:
        return "integer"
    else:
        return "string"


def _update(d, u):
    """
    Updates dictionary d with values from u recursively.
    when updating a lidt, the last two element of the key
    are taken in account :
      - >+: add all elements of the list to the list
      - >-: remove all elements of the list from the list
      - else replace the list

    Arguments:
        d {dict} -- the dictionary to be updated.
        u {dict} -- the dictionary containing the update.
    
    Returns:
        dict -- the updated dictionary.
    """
    if u is None:
        return d

    for _k, v in u.items():
        # The following block allows us to add a modifer
        # in the last two character of a key ">X"
        if isinstance(_k, str) and len(_k)>2 and _k[-2] == ">":
            k=_k[0:-2]
            modifier=_k[-1]
        else:
            k = _k
            modifier=None

        if (k in d or isinstance(d,list) and k<len(d)) and isinstance(v, dict):
            _update(d[k], v)
        elif k in d and (isinstance(v,list) or modifier=='-') and isinstance(d[k],list):
            if modifier == '+':
                d[k] += v
            elif modifier == '-':
                for el in v:
                    if re.match("\[[0-9]+\]", str(el)):
                        index = int(el[1:-1])
                        del d[k][index]
                    else:
                        d[k].remove(el)
            else:
                d[k] = v
        else:
            d[k] = v
    return d