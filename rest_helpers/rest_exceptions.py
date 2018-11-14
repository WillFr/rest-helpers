class NotFoundException(Exception):
    """
    This exceptions indicates a client error : the object
    requested or subject to the requested operation does
    not exist.
    """
    pass

class InvalidDataException(Exception):
    """
    This exception indicates a client error : the
    data sent by the client are not valid.
    """
    pass

class UnauthorizedException(Exception):
    """
    This exception indicates that the client could not
    be authenticated.
    """
    pass

class ForbiddenException(Exception):
    """
    This exception indicates that the client is not
    authorized to access the requested resource or
    perform the requested operation.
    """
    pass
