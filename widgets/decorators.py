import time
import json
import datetime
from functools import wraps
from flask import request
from flask_login import current_user

from .http_utils import get_real_ip


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
    """
        类似于 classmethod 不过是属性不是方法
    """
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


def request_logging(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        from flask import current_app
        if request.method == "GET":
            payload = request.args
        else:
            try:
                payload = request.get_json()
                if request.args:
                    payload.update(request.args)
            except:
                payload = request.args
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
        current_app.access_log.info(logging_dict)
        return func(*args, **kwargs)

    return decorated_view
