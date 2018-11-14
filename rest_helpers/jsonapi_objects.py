
class Resource(object):
    resource_type = None
    def __init__(self, resource_name, resource_type=None, relationships=None, links=None, meta=None, parent=None):
        """
        This is the base type for a REST resource compatible with jsonapi.

        A resource is identified uniquely by the field id constructed as follow:
        id=/grand_parent_type_plural/grand_parent_resource_name/parent_type_plural/parent_name/type_plural/name
        type=/grand_parent_type_plural/parent_type_plural/type_plural

        A resource can be nested under a parent resource where it makes sense.
        Eg:
        id = /authors/mtwain/books/tomsawyer
        type = /authors/books
        call: Resource("books","tomsawyer",parent=MTwainResourceObject)

        resource_type: the type of the resource NOT including the parent type. It should be plural
                        eg: books
        resource_name: the name of the resource.
                        eg: tomsawyer
        relationships: a dictionary of related relationships objects, keyed by relation kind.
        links: a dictionary of links, keyed by kind. 'self' is a special kind: links associated to 'self' should
               point to the current resource or node.
        meta: a list of metadata objects

        """
        resource_type = resource_type if resource_type is not None else self.__class__.resource_type
        assert resource_name is not None and resource_name != ""
        assert resource_type is not None and resource_type != ""
        assert parent is None or (isinstance(parent, Resource))
        assert parent is None or resource_type.startswith(parent.type)

        assert relationships is None \
            or isinstance(relationships, dict) \
               and all(isinstance(x,Relationship) for x in relationships.values())

        assert links is None \
            or isinstance(links, dict) \
               and all(isinstance(x,Link) for x in links.values())

        self.id = "{0}/{1}/{2}".format(parent.id if parent is not None else "", resource_type.split("/")[-1], resource_name)
        self.type = resource_type
        self.name = resource_name
        self.relationships = relationships
        self.links = links
        self.meta = meta
        self._parent = parent

        # automatically create the parent relationship
        if self._parent is not None and (self.relationships is None or "parent" not in self.relationships):
            if self.relationships is None:
                self.relationships = {}
            self.relationships["parent"] = Relationship(links={ "self": Link(self.id + "/relationships/parent"), "parent": Link(parent.id)}, data = self._parent)

        if self.links == None:
            self.links = dict()

        # automatically create the self link
        if "self" not in self.links:
            self.links["self"] = Link(self.id)

class Response(object):
    def __init__(self, data, error, meta, jsonapi=None, links=None, included=None):
        """
        data: the document's primary data
        errors: an array of error objects
        meta: a meta object that contains non-standard meta-information.
        jsonapi: an object describing the server's implementation
        links: a links object related to the primary data.
        included: an array of resource objects that are related to the primary data and/or each other

        The members data and errors MUST NOT coexist in the same document.

        A document MAY contain any of these top-level members:

        jsonapi: an object describing the server's implementation
        links: a links object related to the primary data.
        included: an array of resource objects that are related to the primary
                  data and/or each other (included resources).

        If a document does not contain a top-level data key, the included member
        MUST NOT be present either.
        """
        # A response can contain either data or error but not both
        assert (data is not None) != (error is not None) or data is None
        assert data is not None or included is None
        assert data is None \
                or isinstance(data, Resource) \
                or (isinstance(data, list) and all(isinstance(x, Resource) for x in data))

        assert jsonapi is None or isinstance(jsonapi, JsonApiObject)

        assert included is None \
            or isinstance(included, list) \
               and all(isinstance(x,Resource) for x in included)

        assert links is None \
            or isinstance(links, dict) \
               and all(isinstance(x,Link) for x in links.values())

        self.data = data
        self.error = error
        self.meta = meta
        self.jsonapi = jsonapi
        self.links = links
        self.included = included

class SuccessResponse(Response):
    """
    See Response documentation.
    This response is specific to successful outcome.

    Swagger extra_definition:
        response:
            type: "object"
            properties:
                data:
                    type: "object"
    """
    def __init__(self, data, meta=None, jsonapi=None, links=None, included=None):
        super(SuccessResponse,self).__init__(data=data, error=None, meta=meta, jsonapi=jsonapi, links=links, included=included)

class ErrorResponse(Response):
    """
    See Response documentation.
    This response is specific to erroneous outcome.

    Swagger extra_definition:
    error_response:
        type: "object"
        properties:
            error:
                type: "object"
                $ref: '#/definitions/error'

    error:
        type: "object"
        properties:
            id:
                type: "string"
            status:
                type: "integer"
            title:
                type: "string"
            detail:
                type: "string"
    """
    def __init__(self, error, meta=None, jsonapi=None, links=None, included=None):
        assert error is not None
        super(ErrorResponse,self).__init__(data=None, error=error, meta=meta, jsonapi=jsonapi, links=links, included=included)


class Error(object):
    def __init__(self, error_id, status, title, detail, links=None, about=None, code=None, source=None, pointer=None, parameter=None, meta=None):
        """
        error_id: a unique identifier for this particular occurrence of the problem.
        status: the HTTP status code applicable to this problem, expressed as a string value.
        title: a short, human-readable summary of the problem that SHOULD NOT change from
               occurrence to occurrence of the problem, except for purposes of localization.
        detail: a human-readable explanation specific to this occurrence of the problem.
                Like title, this field's value can be localized.

        links: a links object containing the following members:
        about: a link that leads to further details about this particular occurrence of the problem.
        code: an application-specific error code, expressed as a string value.
        source: an object containing references to the source of the error, optionally including any of the following members:
        pointer: a JSON Pointer [RFC6901] to the associated entity in the request document [e.g. "/data" for a primary data object, or "/data/attributes/title" for a specific attribute].
        parameter: a string indicating which URI query parameter caused the error.
        meta: a meta object containing non-standard meta-information about the error.
        """
        assert status >= 400

        self.id = error_id
        self.status = status
        self.title = title
        self.detail = detail

        self.links = links
        self.about = about
        self.code = code
        self.source = source
        self.pointer = pointer
        self.parameter = parameter
        self.meta = meta

class Link(object):
    """
    Where specified, a links member can be used to represent links.
    """
    def __init__(self, url, meta = None):
        assert url is not None
        self.url = url
        self.meta = meta


class JsonApiObject(object):
    """
     JSON API document MAY include information about its implementation
     under a top level jsonapi member. If present, the value of the
     jsonapi member MUST be an object (a "jsonapi object"). The jsonapi
     object MAY contain a version member whose value is a string
     indicating the highest JSON API version supported. This object MAY
     also contain a meta member, whose value is a meta object that
     contains non-standard meta-information.
    """

    def __init__(self, meta=None):
        self.version = "1.0"
        self.meta = meta

class Relationship(object):
    """
    Members of the relationships object ("relationships") represent
    references from the resource object in which it's defined to other
    resource objects.

    Relationships may be to-one or to-many.
    """
    def __init__(self, links, data, meta=None):
        assert data is not None or links is not None
        assert links is None or isinstance(links,dict) and all(isinstance(x,Link) for x in links.values())
        assert data is None or isinstance(data,Resource)

        self.links = links
        self.data = data