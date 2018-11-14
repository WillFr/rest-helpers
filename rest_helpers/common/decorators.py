def get_decorated_id(f):
    return "{0}:{1}:{2}".format(f.__module__, f.__class__, f.__name__)