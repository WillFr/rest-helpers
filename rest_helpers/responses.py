import json
import re
import traceback
import logging

from functools import reduce
from time import time
from rest_helpers.jsonapi_objects import Error, Resource, SuccessResponse, ErrorResponse, Response, Link
from rest_helpers.type_serializers import to_jsonable,response_to_jsonable
from rest_helpers import rest_exceptions, binding

LOGGER = logging.getLogger(__name__)
def base_exception_handler(framework_adapter, exception):
    if isinstance(exception, rest_exceptions.InvalidDataException):
        return bad_request(framework_adapter, exception)
    elif isinstance(exception, binding.MissingFieldException):
        return bad_request(framework_adapter, exception)
    elif isinstance(exception, rest_exceptions.UnauthorizedException):
        return error(framework_adapter, 401, "Unauthorized", "Your authentication was not successful.")
    elif isinstance(exception, rest_exceptions.ForbiddenException):
        return error(framework_adapter, 403, "Forbidden", "You are not authorized to access the requested resources or perform the requested operation.")
    else:
        LOGGER.error(str(exception) + traceback.format_exc())
        return internal_server_error(framework_adapter, exception, traceback.format_exc())

#region error responses
def bad_request(framework_adapter, exception):
    """Creates an HTTP Status code 400 response with the given message."""
    return error(framework_adapter, 400, "Bad request", "Client error: "+str(exception))

def not_found(framework_adapter, details=None):
    """Creates an HTTP Status code 404 response with the given message."""
    return error(framework_adapter, 404, "Not found", "Client error: The requested resource does not exist.{}".format(("\n"+details) if details else ""))

def internal_server_error(framework_adapter, exception, stack_trace=""):
    """Creates an HTTP Status code 500 response with the given message."""
    details = "Server error: {exception_type} {exception_str} \n {stack_trace}".format(
        exception_type=exception.__class__.__name__,
        exception_str=str(exception),
        stack_trace=stack_trace
    )
    return error(framework_adapter, 500, "Internal server error", details)

def error(framework_adapter, status_code, title, detail, retry_after=None):
    """Creates an error response with the given status code, error title and detail."""
    assert status_code >= 400
    error_obj = Error(
        error_id = framework_adapter.get_current_request_headers_dict().get("X-Unique-ID") or str(time()),
        status = status_code,
        title = title,
        detail = detail
    )

    return _response_from_error(framework_adapter, error_obj, headers={"Retry-After": retry_after} if retry_after else None)
#end region

#region success responses
def ok(framework_adapter, data, page_size=None, id_only=False):
    """Create an HTTP response with exit code 200:OK

    Arguments:
        data {dict} -- the data to be returned

    Keyword Arguments:
        page_size {int} -- if specified, pagination will be used,
                            and this will be the number of items on
                            a page(default: {None})

    Returns:
        [dict] -- A json serializable representation of a JSONAPI response.
    """
    return success(framework_adapter, data, 200, page_size = page_size, id_only=id_only)


def created(framework_adapter, data):
    """ Create an HTTP response with exit code 201:Created """
    return success(framework_adapter, data, 201)

def accepted(framework_adapter, data=None):
    """
    Create an HTTP response with exit code 202:Accepted. It adds a meta field output
    indicating the operation was successful.
    """
    return success(framework_adapter, data,202, {"output":"success"})

def success(framework_adapter, data, status_code, meta=None, links=None, page_size=None, id_only=False):
    """ Create a success response with the given object, status code, and meta. """
    assert status_code < 300 and status_code >= 200
    request_args=framework_adapter.get_current_request_query_string_args()

    if isinstance(data, list):
        actual_page_size = request_args.get("page_size") or page_size or framework_adapter.get_rest_helper_request_context().page_size

        if actual_page_size is not None:
            meta = meta if meta is not None else {}
            links = links if links is not None else {}
            data = _paginate(framework_adapter, data, actual_page_size, links, meta)

    if data is not None and not isinstance(data, Resource) and not isinstance(data, list):
        jsonable = to_jsonable(data)
    else:
        resp = SuccessResponse(data=data, meta=meta, links=links)
        jsonable = response_to_jsonable(resp, id_only=id_only)


    if "json_path" in request_args:
        try:
            jsonable["data"] = _filter_using_json_path(framework_adapter, jsonable, request_args.get("json_path")[0].strip(" /").split("/"))
        except Exception as ex:
            return bad_request(framework_adapter, ex)

    rh_context = framework_adapter.get_rest_helper_request_context()
    jsonable = rh_context.versionner.response_body_dict(jsonable) if rh_context.versionner is not None else jsonable
    response = framework_adapter.make_json_response(jsonable, status_code)

    return response
#endregion


#region private helpers

def _paginate(framework_adapter, data, page_size, links, meta):
    assert isinstance(links, dict)
    assert isinstance(meta, dict)

    page_size = page_size if page_size is not None else \
                framework_adapter.get_rest_helper_request_context.page_size

    if callable(page_size):
        page_size = page_size()

    if page_size is None:
        return

    page_size = int(page_size)
    if "total_pages" not in meta:
        meta["total_pages"] = (len(data)+page_size-1)//page_size

    assert page_size > 0
    prev_link = None
    next_link = None

    # This is a zero based page index
    query_string_args = framework_adapter.get_current_request_query_string_args()
    page = int(query_string_args.get("page",[1])[0])-1
    left = page * page_size
    right = min(len(data), left + page_size)

    if right != len(data):
        next_link = _get_paginated_self_link(framework_adapter, page+2)
    if left != 0:
        prev_link = _get_paginated_self_link(framework_adapter, page)

    data = data[left:right]

    if prev_link is not None:
            links["last"] = prev_link

    if next_link is not None:
        links["next"] = next_link

    return data

def _get_paginated_self_link(framework_adapter, page):
    # we proceed like this to avoid changing the order of the query string args
    query_string = "&".join(x if not x.startswith("page=") else "page={0}".format(page) for x in framework_adapter.get_current_request_query_string().decode().split("&"))
    if "page=" not in query_string:
        query_string = ("{0}{1}page={2}").format(query_string, "&" if query_string != "" else "", page)

    return Link("{0}?{1}".format( framework_adapter.get_current_request_path(), query_string))

def _filter_using_json_path(framework_adapter, jsonable_data, segments):
    for i,segment in enumerate(segments):
        if isinstance(jsonable_data, list):
            if segment[0] == "*":
                filter = _parse_filter(segment)
                sub_segments = segments[i+1:] if i < len(segments)-1 else []
                jsonable_data = [_filter_using_json_path(framework_adapter, x,sub_segments) for x in jsonable_data if filter(x) is True]
                return jsonable_data

            try:
                index = int(segment)
                if index >= len(jsonable_data):
                    raise Exception("The json path provided is not valid: the index '{0}' should be lower than '{1}'.".format(segment, len(jsonable_data)))
                jsonable_data = jsonable_data[index]
            except:
                raise Exception("The json path provided is not valid: expexting an integer for list index, found '{0}'.".format(segment))
        else:
            if segment not in jsonable_data:
                raise Exception("The json path provided is not valid: the key '{0}' is not present.".format(segment))
            jsonable_data = jsonable_data[segment]

    return jsonable_data

def _parse_filter(segment):
    """This parses strings to convert them into a lambda. For instance:
    *:/key1/key2~=[^x]+x

    [
        { key1: {key2: 123x},
        { key1: {key2: 123s}
    ]
    would be filtered to [{ key1: {key2: 123x}]

    
    Arguments:
        segment {str} -- the segment to filter
    
    Raises:
        Exception -- if the filter is not properly formatted, an exception will be raised.

    Returns:
        [callable] -- a callable that will take an object as a parameter and return true or false
    """

    if len(segment) == 1:
        return lambda x: True

    segment=segment[2:]
    operators = ["~=", "==", "!="]
    op_index = next((segment.index(op) for op in operators if op in segment), None)

    if op_index is None:
        raise Exception("The filter {} provided in json_path is not valid: it must contain an operator among {}".format(segment, str(operators)))

    path = segment[:op_index].strip(" >").split(">")
    operator = segment[op_index:op_index+2]
    compared_to = segment[op_index+2:]

    compare = (lambda x,y: re.match(y,x) is not None) if operator == "~=" \
                else (lambda x,y: x == y) if operator == "==" \
                else (lambda x,y: x != y)

    # Here we use reduce drill through the object following the path.
    return lambda x: compare(str(reduce(lambda acc,cur: acc[cur], path, x)), compared_to)


def _response_from_error(framework_adapter, error, headers=None):
    error_response = ErrorResponse(error)
    response = framework_adapter.make_json_response(response_to_jsonable(error_response), error.status, headers, title = error.title)
    return response

#endregion