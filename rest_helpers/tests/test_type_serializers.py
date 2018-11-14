import decimal
from rest_helpers import type_serializers
from rest_helpers.jsonapi_objects import Resource, Response, Link, Relationship, JsonApiObject

class TestTypeSerializers(object):
    def test_to_jsonable(self):
        class TestInnerObj(object):
            def __init__(self, message):
                self.message = message
                self._private = "private"

        class TestObj(object):
            def __init__(self):
                self.name = "test_name"
                self.id = "test_id"
                self._private = "private"
                self.__super_private = "super_private"
                self.dic = {"this": "is", "a": "dictionary", "of":"strings", "and ints":2}
                self.inner_obj = TestInnerObj("This is a message")
                self.inner_obj_list = [TestInnerObj("ex 1"), TestInnerObj("ex 2"), TestInnerObj("ex 3")]
                self.none_field = None
                self.empty_field = ""
                self.decimal = decimal.Decimal(3)
                self.decimal_float = decimal.Decimal('3.4')

        test_object = TestObj()
        assert type_serializers.to_jsonable(test_object, no_empty_field=False) == {
            "name":"test_name",
            "id":"test_id",
            "dic": {"this": "is", "a": "dictionary", "of":"strings", "and ints":2},
            "inner_obj": {"message": "This is a message"},
            "inner_obj_list" : [{"message": "ex 1"}, {"message": "ex 2"}, {"message": "ex 3"}],
            'empty_field': '',
            'none_field': None,
            'decimal': 3,
            'decimal_float': '3.4'
        }

        assert type_serializers.to_jsonable(test_object, no_empty_field=True) == {
            "name":"test_name",
            "id":"test_id",
            "dic": {"this": "is", "a": "dictionary", "of":"strings", "and ints":2},
            "inner_obj": {"message": "This is a message"},
            "inner_obj_list" : [{"message": "ex 1"}, {"message": "ex 2"}, {"message": "ex 3"}],
            'decimal': 3,
            'decimal_float': '3.4'
        }

    def test_response_to_jsonable(self):
        test_resource_1 = Resource(resource_type="/test_type", resource_name="test_name_1")
        test_response_1 = Response(data = test_resource_1, error = None, meta = {"count": 1})

        assert type_serializers.response_to_jsonable(test_response_1) == {
                'data': {
                        'attributes': {
                            'name': 'test_name_1'
                        },
                        'id': '/test_type/test_name_1',
                        'type': '/test_type',
                        'links': {'self': '/test_type/test_name_1'}
                    },
                'meta': {'count': 1}
            }

        test_resource_2 = Resource(resource_type="/test_type", resource_name="test_name_2")
        test_response_2 = Response(data = [test_resource_1, test_resource_2], error = None, meta = {"count": 2})

        assert type_serializers.response_to_jsonable(test_response_2) == {
                'data': [
                            {
                                'attributes': {'name': 'test_name_1'},
                                'id': '/test_type/test_name_1',
                                'type': '/test_type',
                                'links': {'self': '/test_type/test_name_1'}
                            },
                            {
                                'attributes': {'name': 'test_name_2'},
                                'id': '/test_type/test_name_2',
                                'type': '/test_type',
                                'links': {'self': '/test_type/test_name_2'}
                            },
                    ],
                'meta': {'count': 2}
            }

        test_response_3 = Response(data = [], error = None, meta = {"count": 0})
        assert type_serializers.response_to_jsonable(test_response_3) == {
                'data': [],
                'meta': {'count': 0}
            }

    def test_resource_to_jsonable(self):
        test_related_resource = Resource(resource_type="/american_famous_writers", resource_name="19thcentury")
        test_parent_resource = Resource(
            resource_type = "/authors",
            resource_name = "marktwain",
            relationships={
                "part of": Relationship(data=test_related_resource, links = None),
                "bio": Relationship(links={"related":Link("http://host:80/bios/mtwain")}, data=None)
            },
            links={"self":Link("http://host:80/authors/marktwain"), "related": Link("http://host:80/american_famous_writers/19thcentury")},
            meta={"count":1},
            parent=None)

        test_child_resource = Resource(
            resource_type = "/authors/books",
            resource_name = "tomsawyer",
            relationships=None,
            links={ "self": Link("http://host:80/authors/marktwain/books/tomsayer")},
            meta={"count":1},
            parent=test_parent_resource)

        assert type_serializers.resource_to_jsonable(test_child_resource) == {
            'attributes': {'name': 'tomsawyer'},
            'id': '/authors/marktwain/books/tomsawyer',
            'links': {'self': 'http://host:80/authors/marktwain/books/tomsayer'},
            'meta': {'count': 1},
            'relationships': {
                'parent': {
                    'data': {'id': '/authors/marktwain', 'type': '/authors'},
                    'links': {
                        'parent': '/authors/marktwain',
                        'self': '/authors/marktwain/books/tomsawyer?json_path=/relationships/parent'
                        }
                    }
                },
            'type': '/authors/books'
            }

        assert type_serializers.resource_to_jsonable(test_parent_resource) == {
            'attributes': {'name': 'marktwain'},
            'id': '/authors/marktwain',
            'links': {
                'related': 'http://host:80/american_famous_writers/19thcentury',
                'self': 'http://host:80/authors/marktwain'
                },
            'meta': {'count': 1},
            'relationships': {
                'bio': {
                    'links': {'related': 'http://host:80/bios/mtwain', 'self': '/authors/marktwain?json_path=/relationships/bio'}
                    },
                'part of': {
                    'data': {
                        'id': '/american_famous_writers/19thcentury',
                        'type': '/american_famous_writers'
                        },
                    'links': {'self': '/authors/marktwain?json_path=/relationships/part of'}
                    }
                },
            'type': '/authors'}

    def test_links_to_jsonable(self):
        result = type_serializers.links_to_jsonable(None)
        assert result is None

        link = Link("/a/b/c", meta={"a":1,"b":2,"c":"3"})
        result = type_serializers.links_to_jsonable({"link_type": link})

        assert result == {"link_type":
            {
                "href":"/a/b/c",
                "meta":{"a":1,"b":2,"c":"3"}
            }
        }

    def test_jsonapi_object_serializer(self):
        jsonapi_object = JsonApiObject(meta=None)
        assert type_serializers.jsonapiobject_to_jsonable(jsonapi_object) == {
            "version" : "1.0"
        }

        jsonapi_object = JsonApiObject(meta={ "a" : 1, "b": "2"})
        assert type_serializers.jsonapiobject_to_jsonable(jsonapi_object) == {
            "version" : "1.0",
            "meta" : { "a" : 1, "b": "2"}
        }

    def test_relationships_to_jsonable(self):
        link = Link("/a/b/c")
        relationship = Relationship({"related":link}, data=Resource("test_name", "/test_type"))
        assert type_serializers.relationships_to_jsonable({"rel":relationship}) == {
            "rel":{
                "data":{ "type": "/test_type", "id":"/test_type/test_name"},
                "links":{
                    "related":"/a/b/c"
                }
            }
        }

        relationship = Relationship({"related":link}, data=Resource("test_name", "/test_type"))
        assert type_serializers.relationships_to_jsonable({"rel":relationship}, "/prefix", True) == {
            "rel":{
                "data":{ "type": "/test_type", "id":"/test_type/test_name"},
                "links":{
                    "related":"/a/b/c",
                    "self":"/prefix/rel"
                }
            }
        }

