"""
This module contains functions that are geared toward serializing objects,
in particular JSON API objects.
"""

import decimal
from collections import Iterable
from rest_helpers.jsonapi_objects import Resource, Response, Link, JsonApiObject, Relationship

def to_jsonable(obj, no_empty_field=False):
    """
    This is a low level function to transform any object into a json
    serializable (jsonable) object based on its __dict__.

    Arguments:
        obj {any type} -- the object to be transformed.

    Keyword Arguments:
        no_empty_field {bool} -- if set to true, the empty field (empty
        string or None) will be removed from the resulting jsonable object
        (default: {False})

    Returns:
        dict -- A dictionary that can be used by json.dumps
    """
    if isinstance(obj, list):
        return [to_jsonable(r, no_empty_field) for r in obj]
    dic = obj if isinstance(obj, dict) else \
          obj.__dict__ if hasattr(obj, "__dict__") else \
          None

    if dic is None:
        if isinstance(obj, decimal.Decimal):
            str_rep = str(obj)
            return int(obj) if '.' not in str_rep else str_rep
        return obj

    return {
        k: to_jsonable(v, no_empty_field)
        for k, v in dic.items()
        if k[0] != '_' and (not no_empty_field or v is not None and v != "")
    }

def response_to_jsonable(response, generate_self_links=True, id_only=False):
    """
    Transform a response object into a json serializable (jsonable) object that
    matches the jsonapi requirements.

    Arguments:
        resource {Response} -- The response to be serialized

    Keyword Arguments:
        generate_self_links {bool} -- If set to true "self" links will be added appropriately
        where they do not exist. (default: {True})

    Returns:
        dict -- a dictionary that can be used by json.dumps to serialize the Response object.
    """
    assert isinstance(response, Response)

    # Data is a resource object (or a list of resource object,
    # hence it needs some special serialization logic)
    dic = response.__dict__.copy()
    dic.pop("data")
    return_value = to_jsonable(dic, no_empty_field=True)

    if response.data is not None:
        jsonable_data = resource_to_jsonable(response.data, generate_self_links)
        if id_only:
            jsonable_data = jsonable_data["id"] if not isinstance(jsonable_data, Iterable) else [x["id"] for x in jsonable_data]
        return_value["data"] = jsonable_data

    return return_value


def resource_to_jsonable(resource, generate_self_links=True):
    """
    Transform a resource object or a resource object list into
    a json serializable (jsonable) object that matches the jsonapi
    requirements.

    Arguments:
        resource {Resource|list<Resource>} -- The resource or list of resources
        to be serialized

    Keyword Arguments:
        generate_self_links {bool} -- If set to true "self" links will be added appropriately
        where they do not exist. (default: {True})

    Returns:
        dict -- a dictionary that can be used by json.dumps to serialize the Resource object.
    """

    if isinstance(resource, list):
        return [resource_to_jsonable(x) for x in resource]

    assert isinstance(resource, Resource)

    json_resource = resource.to_primitive() if (hasattr(resource, "to_primitive") and callable(resource,to_primitive)) else to_jsonable(resource)
    special = ["id", "type", "relationships", "links", "meta"]
    for key in special:
        json_resource.pop(key, None)

    relationships = relationships_to_jsonable(
        resource.relationships, "{0}?json_path=/{1}".format(resource.id, "relationships"),
        generate_self_links)

    resource_links = resource.links
    if generate_self_links and "self" not in resource_links:
        resource_links = resource.links.copy()
        resource_links["self"] = Link(resource.id)

    links = links_to_jsonable(resource_links)
    return_value = {
        "id" : resource.id,
        "type" : resource.type,
        "relationships" : relationships,
        "links" : links,
        "meta" : resource.meta,
        "attributes" :json_resource
    }

    _remove_empty_fields(return_value)
    return return_value

def link_to_jsonable(link):
    """
    Transforms a json api link object into a dictionary that can be used by json.dumps.

    Arguments:
        link {Link} -- the link to be serialized.

    Returns:
        dict -- a dictionary that can be used by json.dumps to serialize the Link object.
    """

    assert isinstance(link, Link)

    if link.meta is None:
        return  link.url
    else:
        return {
            "href": link.url,
            "meta": to_jsonable(link.meta)
        }

def links_to_jsonable(links):
    """
    Transform a json api Link object dictionary into a dictionaty that can be used
    by json dumps.

    Arguments:
        links {dict<Link>} -- the dictionary of Link objects to be serialized.

    Returns:
        dict --  a dictionary that can be used by json.dumps to serialize the dictionary of link
        objects.
    """

    if links is None:
        return None

    assert isinstance(links, dict)
    return {k: link_to_jsonable(v) for k, v in links.items()}

def jsonapiobject_to_jsonable(jsonapiobject):
    """
    Transforms a jsonapi json api objects into a dictionary that can be used by json dumps

    Arguments:
        jsonapiobject {JsonApiObject} -- The jsonapiobject to be serialized.

    Returns:
        dict -- a dictionary that can be used by json.dumps to serialize the JsonApiObject object.
    """

    assert isinstance(jsonapiobject, JsonApiObject)
    return  to_jsonable(jsonapiobject, no_empty_field=True)


def relationship_to_jsonable(relationship, self_link=None):
    """
    Tranform a json api relationship object into a json serializable object that matches
    the json api specification.

    Arguments:
        relationship {Relationship} -- a relationship object to be serialized.

    Keyword Arguments:
        self_link {string} -- link to the relationship to be serialized. If not None, a link
        json api object will be created based on this value and added to the links of the
        relationship object to be serialized (default: {None}).

    Returns:
        dict -- a dictionary that can be used by json.dumps to serialize the relationship object.
    """

    assert isinstance(relationship, Relationship)

    return_value = dict()

    links = relationship.links.copy() if relationship.links is not None else dict()
    if self_link is not None:
        links["self"] = Link(self_link)

    if any(links):
        return_value["links"] = links_to_jsonable(links)

    if relationship.data is not None:
        return_value["data"] = {"type": relationship.data.type, "id": relationship.data.id}

    return return_value

def relationships_to_jsonable(relationships, self_link_prefix=None, generate_self_link=False):
    """
    Tranform a dictionary of json api relationship object nto a json
    serializable object that matches the json api specification.

    Arguments:
        relationships {dict<Relationships>} -- a dict of
        relationship objects to be serialized.

    Keyword Arguments:
        self_link_prefix {string} -- prefix to be used as the link prefix when generate_self_link
        is set to true. (default: {None})
        generate_self_link {bool} -- when set to true, a self link will be autogenerated when
        serializing the relationship object (default: {False}).

    Returns:
        dict -- a dictionary that can be used by json.dumps to serialize the relationship
        dictionary.
    """

    if relationships is None:
        return None

    assert isinstance(relationships, dict)

    if generate_self_link:
        return {k: relationship_to_jsonable(v, "{0}/{1}".format(self_link_prefix, k))
                for k, v in relationships.items()}
    else:
        return {k: relationship_to_jsonable(v) for k, v in relationships.items()}

#region private

def _remove_empty_fields(dic):
    for key in [k for k, v in dic.items() if v is None or v == ""]:
        dic.pop(key)

#endregion
