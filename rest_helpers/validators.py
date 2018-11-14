import functools

from schematics.models import Model
from schematics import types
from schematics.exceptions import ValidationError


def _schematic_model_validator(model, post=False):
    if not post:
        #schematics models are validated post deserialization
        return True,""
    else:
        try:
            model.validate()
            return True,""
        except ValidationError as ex:
            return False, str(ex.messages)

def _schematic_type_validator(schematic_type, value, post=False):
    if not post:
        #schematics types are validated post deserialization
        return True,""
    else:
        try:
            schematic_type.validate(value)
            return True,""
        except ValidationError as ex:
            return False, str(ex.messages)

# the order is important here because we will use isinstance, so we use a list
type_to_validator_tuple_list = list({
    Model: (_schematic_model_validator,),
    types.BaseType: (lambda type_hint: functools.partial(_schematic_type_validator, type_hint),)
}.items())

def get_type_validators(type_hint):
    potential_type_to_validator_tuple = next((x for x in type_to_validator_tuple_list
                                            if isinstance(type_hint, type) and issubclass(type_hint, x[0]) or isinstance(type_hint, x[0])), None)
    if potential_type_to_validator_tuple:
        return potential_type_to_validator_tuple[1][0](type_hint) if isinstance(potential_type_to_validator_tuple[1], tuple) else potential_type_to_validator_tuple[1]
    else:
        return None