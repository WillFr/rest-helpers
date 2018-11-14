from rest_helpers import type_deserializers


class TestTypeDeserializers(object):
    def test_bool_deserializer(self):
        assert type_deserializers.bool_deserializer("")
        assert type_deserializers.bool_deserializer("True")
        assert type_deserializers.bool_deserializer("true")

        assert not type_deserializers.bool_deserializer("false")
        assert not type_deserializers.bool_deserializer("False")
        assert not type_deserializers.bool_deserializer(None)

    def test_int_deserializer(self):
        assert type_deserializers.int_deserializer("3") == 3