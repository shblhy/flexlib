from flask_restplus.marshalling import marshal_with
from flask_restplus.utils import merge
from .formats import SucResponse, Table, error_fields


def marshal_item(serializer_class, code=200, description=None, **kwargs):
    fields = SucResponse.get_fields(serializer_class, _many_=False, skip_none=kwargs.get('skip_none', True))

    def wrapper(func):
        doc = {
            'responses': {
                code: (description, fields),
                400: ('http request error', error_fields)
            },
            '__mask__': kwargs.get('mask', True),  # Mask values can't be determined outside app context
        }
        func.__apidoc__ = merge(getattr(func, '__apidoc__', {}), doc)
        return marshal_with(fields, ordered=True, **kwargs)(func)

    return wrapper


def marshal_table(serializer_class, as_list=False, code=200, description=None, **kwargs):
    fields = Table.get_fields(serializer_class,
                              add_action=bool(kwargs.pop('add_action', False)),
                              skip_none=bool(kwargs.get('skip_none', True)))

    def wrapper(func):
        doc = {
            'responses': {
                code: (description, fields),
                400: ('http request error', error_fields)
            },
            '__mask__': kwargs.get('mask', True),  # Mask values can't be determined outside app context
        }
        func.__apidoc__ = merge(getattr(func, '__apidoc__', {}), doc)
        return marshal_with(fields, ordered=True, **kwargs)(func)

    return wrapper
