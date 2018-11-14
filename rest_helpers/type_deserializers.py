import functools
from decimal import Decimal
import datetime
from dateutil import parser

from schematics.models import Model
from schematics import types

def bool_deserializer(x):
    """
    This is to be used to deserialize boolean : we consider that if
    the value is "", then we should return true in order to be
    able to parse boolean from query strings.
    eg: http://myhost.com/index?loggedin&admin&page=5
    is equivalent to
        http://myhost.com/index?loggedin=True&admin=True&page=5
    """
    return x is not None and (x == "" or x.lower() == "true" )

def int_deserializer(x):
    """
    This is to be used to deserialize integers.
    """
    return int(x)

def float_deserializer(x): # pragma: no cover (nothing to test here)
    """
    This is to be used to deserialize floats.
    """
    return float(x)

def decimal_deserializer(x):
    """
    This is to be used to deserialize decimals.
    """
    return Decimal(x)

def datetime_deserializer(x): # pragma: no cover (nothing to test here)
    """
    This is to be used to deserialize datetimes.
    """
    return parser.parse(x)

def string_deserializer(x): # pragma: no cover (nothing to test here)
    """
    This is to be used to deserialize strings.
    """
    return str(x)

# the order is important here because we will use isinstance, so we use a list
type_to_deserializer_tuple_list = list({
    bool: bool_deserializer, # bool must be first because a bool is an int
    int: int_deserializer,
    float: float_deserializer,
    Decimal: decimal_deserializer,
    str: string_deserializer,
    datetime.datetime: datetime_deserializer,
    Model: (lambda type_hint: type_hint,),
    types.BaseType: (lambda type_hint: type_hint.to_native,)
}.items())

def get_default_deserializer(type_hint):
    potential_deserializer_tuple = next((x for x in type_to_deserializer_tuple_list
                                            if isinstance(type_hint, type) and issubclass(type_hint, x[0]) or isinstance(type_hint, x[0])), None)
    if potential_deserializer_tuple is not None:
        return potential_deserializer_tuple[1][0](type_hint) if isinstance(potential_deserializer_tuple[1], tuple) else potential_deserializer_tuple[1]
    else:
        return None