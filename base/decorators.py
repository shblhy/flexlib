import time
import json
import datetime
from functools import wraps
from flask import request
from flask_login import current_user
from werkzeug.exceptions import Unauthorized
from exlib.base.signature import Signature
from exlib.base.http_utils import get_real_ip


class cached_property(object):
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(get_absolute_url, name='url') )
    """

    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


class ClassPropertyDescriptor(object):

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)
    return ClassPropertyDescriptor(func)


class ClassPropertyMetaClass(type):
    def __setattr__(self, key, value):
        if key in self.__dict__:
            obj = self.__dict__.get(key)
        if obj and type(obj) is ClassPropertyDescriptor:
            return obj.__set__(self, value)

        return super(ClassPropertyMetaClass, self).__setattr__(key, value)


def func_timer(function):
    '''
    用装饰器实现函数计时
    :param function: 需要计时的函数
    :return: None
    '''

    @wraps(function)
    def function_timer(*args, **kwargs):
        print('[Function: {name} start...]'.format(name=function.__name__))
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print('[Function: {name} finished, spent time: {time:.2f}s]'.format(name=function.__name__, time=t1 - t0))
        return result

    return function_timer


def marshal_item(serializer_class, code=200, description=None, **kwargs):
    from flask_restplus.marshalling import marshal, marshal_with
    from exlib.rest.formats import SucResponse, error_fields
    from flask_restplus.utils import merge
    fields = SucResponse.get_fields(serializer_class, _many_=False)

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
    '''
    A decorator specifying the fields to use for serialization.

    :param bool as_list: Indicate that the return type is a list (for the documentation)
    :param int code: Optionally give the expected HTTP response code if its different from 200

    '''
    from flask_restplus.marshalling import marshal, marshal_with
    from flask_restplus.utils import merge
    from exlib.rest.formats import Table, error_fields
    fields = Table.get_fields(serializer_class, add_action=bool(kwargs.get('add_action')))

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


def program_authentication_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        identify = request.environ.get('HTTP_IDENTIFY', '')
        try:
            dic = dict([i.split('=') for i in identify.split('&')])
            if not Signature.check_right(**dic):
                raise Unauthorized(description='signature failed:' + str(dic))
        except Exception as e:
            raise Unauthorized(description='signature failed:' + str(e))
        return func(*args, **kwargs)

    return decorated_view


def request_logging(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        from flask import current_app
        if request.method == "GET":
            payload = request.args
        else:
            payload = request.get_json()
        ip = get_real_ip()
        logging_dict = dict(
            request=request.method, path=request.path, ip=ip,
            time=datetime.datetime.now(),
            agent_platform=request.user_agent.platform,
            agent_browser=request.user_agent.browser,
            agent_browser_version=request.user_agent.version,
            agent=request.user_agent.string,
            user_db_id=str(current_user.id) if (current_user and not current_user.is_anonymous) else "",
            user_name=current_user.name.encode("utf-8") if (current_user and not current_user.is_anonymous) else "",
            payload=json.dumps(payload, ensure_ascii=False)
        )
        current_app.connect_logger.info(logging_dict)
        return func(*args, **kwargs)

    return decorated_view
