class BaseExceptionHandle(Exception):
    def __init__(self, *args):
        super(BaseExceptionHandle, self).__init__(*args)

class NotFoundException(BaseExceptionHandle):
    """
    This exceptions indicates a client error : the object
    requested or subject to the requested operation does
    not exist.
    """
    pass

class InvalidDataException(BaseExceptionHandle):
    """
    This exception indicates a client error : the
    data sent by the client are not valid.
    """
    pass

class UnauthorizedException(BaseExceptionHandle):
    """
    This exception indicates that the client could not
    be authenticated.
    """
    pass

class ForbiddenException(BaseExceptionHandle):
    """
    This exception indicates that the client is not
    authorized to access the requested resource or
    perform the requested operation.
    """
    pass
