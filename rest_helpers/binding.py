import functools
import json
import traceback
import inspect
import typing
import requests
import re
from urllib.parse import urlparse

from jose import jws,jwt

from rest_helpers import type_deserializers, validators
from rest_helpers.common import decorators
from rest_helpers.rest_exceptions import InvalidDataException, UnauthorizedException, ForbiddenException

_input_decorators = {}

class MissingFieldException(Exception):
    pass

class bind_hints(object):
    def __init__(self, framework_adapter):
        self.framework_adapter = framework_adapter


    def __call__(self, func):
        self.func = func

        return_value=func
        type_hints = self.func.__annotations__
        for field,hint in type_hints.items():
            potential_binding_decorator = hint[-1] if isinstance(hint, tuple) else hint

            # If it has the __wrapped__ attribute created by functools then it is
            # a decorator type not yet instanciated (Eg: argument:binding vs argument: binding())
            if hasattr(potential_binding_decorator, "__wrapped__"):
                potential_binding_decorator = potential_binding_decorator()
            if isinstance(potential_binding_decorator, base_binder):
                potential_binding_decorator.set_field(field)
                functools.update_wrapper(potential_binding_decorator, return_value)
                return_value = potential_binding_decorator(return_value)
                
        if return_value != func:
            functools.update_wrapper(return_value, func)
        return return_value

class base_binder(object):
    def __init__(self, framework_adapter, field=None, validator=None, deserializer=None, type=None):
        if (deserializer is not None) and (type is not None):
            raise Exception("deserializer and type cannot be provided at the same time.")

        self.func = None
        self.validator = validator
        self.deserializer = deserializer
        self.type = type
        self.framework_adapter = framework_adapter
        self.set_field(field)

    def __call__(self, f):
        self.func = f
        self.real_view_function = f

        while hasattr(self.real_view_function, "__wrapped__"):
            self.real_view_function = self.real_view_function.__wrapped__

        if self.type is None:
            type_hints = self.real_view_function.__annotations__
            self.type = type_hints.get(self.field, None)
            self.type = self.type[0] if isinstance(self.type, tuple) else self.type

        f_args = self.real_view_function.__code__.co_varnames[:self.real_view_function.__code__.co_argcount]

        try:
            arg_index = f_args.index(self.field)
        except ValueError:
            raise Exception("Argument {field} could not be found in function {function} arguments".format(field=self.field, function=self.real_view_function))

        self.has_default = f_args != None and self.real_view_function.__defaults__!=None and arg_index >= len(f_args) - len(self.real_view_function.__defaults__)
        self.default = self.real_view_function.__defaults__[arg_index - (len(f_args) - len(self.real_view_function.__defaults__))] if self.has_default else None

        if self.deserializer is None and self.type is not None:
            self.deserializer = type_deserializers.get_default_deserializer(self.type)

        if self.validator is None and self.type is not None:
            self.validator = validators.get_type_validators(self.type)

        async def return_value(*args, **kwargs):
            args = self.framework_adapter.set_request_args(args)
            kwargs = self.framework_adapter.set_request_kwargs(kwargs)
            return await _on_request_binding(self, *args, **kwargs)

        functools.update_wrapper(return_value, f)


        self.real_view_function_id = decorators.get_decorated_id(self.real_view_function)
        if self.real_view_function_id not in _input_decorators:
            _input_decorators[self.real_view_function_id] = []

        _input_decorators[self.real_view_function_id].append(self)

        return return_value

    async def get_value(self): #pragma no cover
        raise NotImplementedError()

    def set_field(self, field):
        self.field = field

class from_json_body(base_binder):
    __name__ = "from_json_body"
    def __init__(self, framework_adapter, field="data", validator=None, deserializer=None):
        """
        This class is to be used as a decorator:
        it will fill the parameter of a method by parsing the
        content of the body of the request.
        In particular, it will assign to the method argument named <field>
        the request content, deserialized from json to a dictionary.

        Additionally, a validator can be passed to automatically check the data.
        If the validation failed, a bad request is returned.

        Deserializer will be infered from type annotation.
        Field with a default value are considered optional.

        eg:
        request content =
        {
            field1: value1
            field2: value2
        }

        @from_json_body(field="myData")
        def method(myData):
            assert myData["field1"] == "value1"
            assert myData["field2"] == "value2"

        Arguments:
            framework_adapter {BaseFrameworkAdapter} -- The adapter used to interact with the framework

        Keyword Arguments:
            field {str} -- the name of the function argument to be filled (default: {"data"})
            validator {callable} -- a function that take the input as a value and returns a
                    tuple (bool,reason) to indicate if the input is valid or not (default: {None})
            deserializer {callable} -- a function or class used to deserialize the input to an object (default: {None}).
                                        Can be set to a schematics type or model

        """

        #TODO: test validation of object with : 1. a deserialiazer that has a validate method, a deserialized object that has a validate method.

        super(from_json_body, self).__init__(framework_adapter, field, validator, deserializer)

    async def get_value(self):
        return await _get_dict_from_json_body(self.framework_adapter)

# TODO: support optimization fot stacking
class field_from_json_body(base_binder):
    __name__ = "field_from_json_body"
    def __init__(self, framework_adapter, field=None, json_field=None, validator=None, deserializer=None):
        """
        This function is to be used as a decorator:
        it will fill the parameter of a method by parsing the
        content of the body of the request.
        In particular, it will assign to the method argument named <field>
        the value of the associated <json_field> field in the request content,
        deserialized from json to a dictionary.

        If <json_field> is not specified, the value of <field> will be used.

        Additionally, a validator can be passed to automatically check the data.
        If the validation failed, a bad request is returned.

        Deserializer will be infered from type annotation.
        Field with a default value are considered optional.

        eg:
        request content =
        {
            field1: value1
            field2: value2
        }

        @field_from_json_body(field="fieldA", json_field="field1")
        @field_from_json_body(field="fieldB", json_field="field2")
        def method(fieldA, fieldB):
            assert fieldA == "value1"
            assert fieldB == "value2"

        field = the name of the function argument to be filled. If field is
                a path, the last segment of the path will be the name of the
                function argument to be filled.
                eg: data/parent/child -> child
        json_field = the name of the field in the json body,
                    if not provided, the value of field will be used
        validator = a function that take the input as a value and returns a
                    tuple (bool,reason) to indicate if the input is valid or not
        deserializer = a function used to deserialize the input to an object
        """
        self.json_field = json_field or field
        super(field_from_json_body, self).__init__(framework_adapter, field, validator, deserializer)

    def set_field(self, field):
        if field is None:
            return

        self.json_field = self.json_field or field
        self.field = field.split("/")[-1]

    async def get_value(self):
        return await _get_field_from_json_body(self.framework_adapter, self.json_field)


class from_header(base_binder):
    __name__ = "from_header"
    def __init__(self, framework_adapter,field=None, header_field=None, validator=None, deserializer=None):
        """
        This function is to be used as a decorator:
        it will fill the parameter of a method by parsing the
        content of the headers of the request.
        In particular, it will assign to the method argument named <field>
        the value of the associated <header_field> field in the request headers.

        If <header_field> is not specified, the value of <field> will be used.

        Additionally, a validator can be passed to automatically check the data.
        If the validation failed, a bad request is returned.

        Deserializer will be infered from type annotation.
        Field with a default value are considered optional.

        eg:
        request query string field1=value1&field2=value2

        @from_header(field="fieldA", header_field="field1")
        @from_header(field="fieldB", header_field="field2")
        def method(fieldA, fieldB):
            assert fieldA == "value1"
            assert fieldB == "value2"

        field = the name of the function argument to be filled
        header_field = the name of the field in the header dict,
                    if not provided, the value of field will be used
        validator = a function that take the input as a value and returns a
                    tuple (bool,reason) to indicate if the input is valid or not
        deserializer = a function used to deserialize the input to an object
        """
        self.header_field = header_field
        super(from_header, self).__init__(framework_adapter, field, validator, deserializer)


    def set_field(self, field):
        if field is None:
            return

        self.header_field = self.header_field or field
        self.field = field

    async def get_value(self):
        return _get_field_from_headers(
            self.framework_adapter,
            self.header_field)

class from_query_string(base_binder):
    __name__ = "from_query_string"
    def __init__(self, framework_adapter,field=None, query_field=None, validator=None, deserializer=None, as_list=False):
        """
        This function is to be used as a decorator:
        it will fill the parameter of a method by parsing the
        content of the query string of the request.
        In particular, it will assign to the method argument named <field>
        the value of the associated <query_field> field in the request query string,
        deserialized to a dictionary.

        If <query_field> is not specified, the value of <field> will be used.

        Additionally, a validator can be passed to automatically check the data.
        If the validation failed, a bad request is returned.

        Deserializer will be infered from type annotation.
        Field with a default value are considered optional.

        eg:
        request query string field1=value1&field2=value2

        @from_query_string(field="fieldA", query_field="field1")
        @from_query_string(field="fieldB", query_field="field2")
        def method(fieldA, fieldB):
            assert fieldA == "value1"
            assert fieldB == "value2"

        field = the name of the function argument to be filled
        query_field = the name of the field in the query string,
                    if not provided, the value of field will be used
        validator = a function that take the input as a value and returns a
                    tuple (bool,reason) to indicate if the input is valid or not
        deserializer = a function used to deserialize the input to an object
        as_list = indicate that the input should be treated as a list at all time.
                If set to False(default), the input will be treated as a list only if the list
                contains more than one element.
        """
        self.query_field = query_field
        self.as_list = as_list

        super(from_query_string, self).__init__(framework_adapter, field, validator, deserializer)

    def set_field(self, field):
        if field is None:
            return

        self.query_field = self.query_field or field
        self.field = field

    async def get_value(self):
        return _get_field_from_query_string(
            self.framework_adapter,
            self.query_field,
            self.as_list)

_key_clean_regex=re.compile('[^a-zA-Z0-9]+')
class from_Oauth(base_binder):
    __name__ = "from_Oauth"
    def __init__(self, framework_adapter, allowed_domains=None, validate_options=None, client_id=None, field=None, valid_tokens=None, deserializer=None):
        """
        This function is to be used as a decorator:
        it will fill the parameter of a method by parsing the
        content of the Authorization header of the request, and getting the associated
        informations from the oauth auth server if the token is valid.

        Deserializer will be infered from type annotation.
        Field with a default value are considered optional.

        allowed_domains = the domain trusted to issue tokens
        validate_options = defaults = {
                'verify_signature': True,
                'verify_aud': True,
                'verify_iat': True,
                'verify_exp': True,
                'verify_nbf': True,
                'verify_iss': True,
                'verify_sub': True,
                'verify_jti': True,
                'verify_at_hash': True,
                'leeway': 0,
            }
        client_id = the client id of the application : the token audience will be verified againt it.
        field = the method argument to be filled with auth infos
        valid_tokens = a dict of tokens that are valid and bypass auth, values associated with a valid token will be passed to the field.
        deserializer = a function used to deserialize the auth result into an object.
        """
        super(from_Oauth, self).__init__(framework_adapter, (field or "user_auth"), lambda x,y:(True,"always valid"), deserializer or (lambda x:x))
        self._public_keys = {}
        self.allowed_domains = allowed_domains
        self.client_id = client_id
        self.validate_options = validate_options
        self.valid_tokens = valid_tokens or {}


    async def get_value(self):
        token = _get_field_from_headers(
            self.framework_adapter,
            "Authorization")
        token = token.replace("Bearer ", "")

        if token in self.valid_tokens:
            return self.valid_tokens[token]

        unauthorized_exception = UnauthorizedException("""You are not authorized to access the requested resource or operation.
            Make sure the supplied token is valid and that the user associated with it has access rights""")
        id_token = token
        decoded_token = jws.get_unverified_header(id_token)
        cleaned_key_id = None
        if 'kid' not in decoded_token:
            raise UnauthorizedException("The token does not contain a key id. Is it a proper JWT token ?")

        dirty_key_id = decoded_token['kid']

        cleaned_key_id = re.sub(_key_clean_regex, '', dirty_key_id)

        if cleaned_key_id not in self._public_keys:
            unverified_claims = jwt.get_unverified_claims(id_token)
            dirty_url = urlparse(unverified_claims['iss'])

            if self.allowed_domains is not None and dirty_url.netloc not in self.allowed_domains:
                raise UnauthorizedException("The issuer of the token does not belong to the list of approved domains : " + str(self.allowed_domains))

            cleaned_issuer = dirty_url.geturl()
            oidc_discovery_url = "{}/.well-known/openid-configuration".format(cleaned_issuer)
            openid_configuration = requests.get(oidc_discovery_url).json()
            jwks_uri = openid_configuration['jwks_uri']
            jwks = requests.get(jwks_uri).json()
            self._public_keys = {re.sub(_key_clean_regex, '',key['kid']):key for key in jwks['keys']}

            if cleaned_key_id not in self._public_keys:
                raise UnauthorizedException("The public key used to sign the token is not valid.")

        try:
            decoded = jwt.decode(
                id_token,
                key=self._public_keys[cleaned_key_id],
                audience=self.client_id,
                options=self.validate_options)
        except Exception as ex:
            raise ForbiddenException("""You are not authorized to access the requested resource or operation.
            Make sure the supplied token is valid and that the user associated with it has access rights.

            Exception:
            {}
            """.format(ex))

        return decoded

#region private

async def _on_request_binding(decorator, *args, **kwargs):
    # if we are not within a request context (testing for instance)
    # there is no work to be done.
    if decorator.framework_adapter.is_in_test():
        return await decorator.func(*args, **kwargs) if inspect.iscoroutinefunction(decorator.func) else decorator.func(*args, **kwargs)

    if decorator.deserializer is None and decorator.type is not None:
        decorator.deserializer = type_deserializers.get_default_deserializer(decorator.type)

    if decorator.validator is None and decorator.type is not None:
        decorator.validator = validators.get_type_validators(decorator.type)

    try:
        value = await decorator.get_value()
        is_valid,reason = decorator.validator(value, False) if decorator.validator is not None else (True,"")
        if not is_valid:
            raise InvalidDataException("The value of the field {field} is not valid: {reason}".format(field=decorator.field, reason=reason))

        if callable(decorator.deserializer):
            value = decorator.deserializer(value)

        # post deserialization validation
        is_valid,reason = decorator.validator(value, True) if decorator.validator is not None else (True,"")
        if not is_valid:
            raise InvalidDataException(reason)
    except MissingFieldException as ex:
        if decorator.has_default:
            value = decorator.default
        else:
            raise

    kwargs.pop(decorator.field,None)
    kwargs[decorator.field] = value

    result = await decorator.func(*args, **kwargs) if inspect.iscoroutinefunction(decorator.func) else decorator.func(*args, **kwargs)
    return result

async def _get_dict_from_json_body(framework_adapter):
    try:
        body = await framework_adapter.get_current_request_body()
        context = framework_adapter.get_rest_helper_request_context()

        if context is not None and context.versionner is not None:
            body = context.versionner.body(body)
        if body == "":
            raise MissingFieldException("The body of the request is not valid: a json object is expected.")
        else:
            data = json.loads(body)

        data = context.versionner.body_dict(data) if context is not None and context.versionner is not None else data
        return data
    except (SyntaxError,ValueError) as ex:
        raise InvalidDataException("request data is not valid JSON: {message}".format(message=ex))

async def _get_field_from_json_body(framework_adapter, json_field):
    data = await _get_dict_from_json_body(framework_adapter)

    json_field_segments = json_field.split("/")
    for json_field_segment in json_field_segments:
        if data is None or not isinstance(data, dict) or json_field_segment not in data:
            raise MissingFieldException("The field {json_field} is not present in the content of the request.".format(json_field=json_field))
        else:
            data = data[json_field_segment]

    return data

def _get_field_from_query_string(framework_adapter, query_field, as_list):
    query_string_args = framework_adapter.get_current_request_query_string_args()

    context = framework_adapter.get_rest_helper_request_context()
    if context is not None and context.versionner is not None:
        query_string_args = context.versionner.query_string_args(query_string_args)

    if query_field not in query_string_args:
        raise MissingFieldException("The field {query_field} is not present in the query string.".format(query_field=query_field))
    else:
        associated_list = query_string_args[query_field]
        field_value = associated_list[0] if len(associated_list) == 1 and not as_list else associated_list

    return field_value

def _get_field_from_headers(framework_adapter, header_field):
    headers = framework_adapter.get_current_request_headers_dict()
    context = framework_adapter.get_rest_helper_request_context()
    if context is not None and context.versionner is not None:
        headers = context.versionner.headers(headers)

    if header_field not in headers:
        raise MissingFieldException("The field {header_field} is not present in the requests headers.".format(header_field=header_field))
    else:
        field_value = headers[header_field]

    return field_value

#endregion