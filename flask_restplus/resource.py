# from abc import abstractmethod
import regex
from collections import OrderedDict
from werkzeug.exceptions import abort, BadRequest
from flask_restplus import Resource as Resource_
from flask import request
from flask.views import View, MethodViewType
from flask_login import login_required
from ..webbase.http_utils import get_object_or_404
from ..webbase.response import JsonResponse
from ..widgets.decorators import request_logging
from ..flex import current_flex
DEFAULT_ENGINE = current_flex.db_engine
_regist_decorators = {}
_regist_decorators_dynamic_params = {}


def regist_decorator(decorator_func, decorator_param_func=None):
    """
        注册自定义装饰器，以支持自订修饰。
        传入decorator_param_func以支持动态参数，提供方法形如 def fun1(fields, bases, method, attr, value):return 1
    :param decorator_func:
    :param decorator_param_func: eg: lambda fields, bases, method, attr, value: 1
    :return:
    """
    _regist_decorators[decorator_func.__name__] = decorator_func
    if decorator_param_func:
        _regist_decorators_dynamic_params[decorator_func.__name__] = decorator_param_func


def get_decorators_func(key):
    return _regist_decorators.get(key)


def has_decorators_dynamic_params(key):
    return key in _regist_decorators_dynamic_params


def get_decorators_dynamic_params(key):
    return _regist_decorators_dynamic_params[key]


def get_attr(d, bases, attr):
    if attr in d:
        val = d[attr]
    else:
        for b in bases:
            val = getattr(b, attr, None)
            if val is not None:
                break
        else:
            raise Exception('%s-%s 未定义' % (d['__qualname__'], attr))
    return val


def has_attr(d, bases, attr):
    if attr in d:
        return True
    else:
        for b in bases:
            val = getattr(b, attr, None)
            if val is not None:
                return True
        else:
            return False


decorator_pattern = regex.compile('decorator__(?P<method>(.*)?)__(?P<name>(.*)?)')


def get_decorator_attrs(d, bases):
    res = OrderedDict()
    for attr in d:
        item = decorator_pattern.match(attr)
        if item:
            res[attr] = (item.groupdict()['method'], item.groupdict()['name'], d[attr])
    for cls in bases:
        for attr in dir(cls):
            if attr in res:
                continue
            item = decorator_pattern.match(attr)
            if item:
                res[attr] = (item.groupdict()['method'], item.groupdict()['name'], getattr(cls, attr))
    return res


class ResourceBaseType(MethodViewType):
    """
        支持对methods的任意修饰
    """
    def __init__(cls, name, bases, d):
        super(ResourceBaseType, cls).__init__(name, bases, d)
        abstract = True if d.get('Meta') and d.get('Meta').abstract else False
        if not abstract and getattr(cls, 'methods', None):
            # 计算decorators_config
            cls._decorator_config = ResourceBaseType.get_decorator_config(cls, bases, d, cls.methods)
            # 为methods方法设置装饰器（支持带参）
            for method in cls.methods:
                _method = method.lower()
                for decorator_name, decorator_param in cls._decorator_config.get(_method, {}).items():
                    decorator_func = get_decorators_func(decorator_name)
                    if decorator_func:
                        if isinstance(decorator_param, dict):
                            setattr(cls, _method, decorator_func(**decorator_param)(getattr(cls, _method)))
                        elif isinstance(decorator_param, list):
                            setattr(cls, _method, decorator_func(*decorator_param)(getattr(cls, _method)))
                        else:
                            setattr(cls, _method, decorator_func(decorator_param)(getattr(cls, _method)))

    @staticmethod
    def get_decorator_config(cls, bases, d, methods):
        res = {}
        parameterized_decorators = get_attr(d, bases, 'parameterized_decorators')
        _methods = [m.lower() for m in methods]
        for method, val in parameterized_decorators.items():
            if method not in _methods:
                continue
            res[method] = OrderedDict([])
            for item in val:
                if type(item) is str:
                    decorator_name = item
                    decorator_params = None
                else:
                    decorator_name = item[0]
                    decorator_params = item[1]
                res[method][decorator_name] = decorator_params
        attrs = get_decorator_attrs(d, bases)
        for attr, item in attrs.items():
            method, decorator_name, val = item
            if method not in res:
                res[method] = OrderedDict([])
            res[method][decorator_name] = val
        for method in res:
            for decorator_name in res[method]:
                if has_decorators_dynamic_params(decorator_name):
                    res[method][decorator_name] = get_decorators_dynamic_params(decorator_name)(
                        d, bases, method, decorator_name, res[method][decorator_name]
                    )
        return res


# class AbResource(Resource, metaclass=ResourceBaseType):
class AbResource(Resource_):
    """
        这是一个抽象Resource类，将之具体化时应多重继承于元类为ResourceBaseType的类
    """
    model_class = None
    method_decorators = [request_logging]
    parameterized_decorators = {}

    class Meta:
        engine = 'mongo'
        abstract = True


class AbSingleResource(AbResource):
    model_class = None
    model_serializer = None
    method_decorators = AbResource.method_decorators + [login_required]
    # methods = ['get', 'put', 'delete']
    parameterized_decorators = {
        'get': ['marshal_item', 'expect'],
        'put': ['marshal_item', 'expect'],
        'delete': []
    }

    class Meta:
        engine = 'mongo'
        abstract = True

    @property
    def msg_del_success(self):
        return '删除%s成功' % self.model_class._model_desc_

    @property
    def msg_edit_success(self):
        return '编辑%s成功' % self.model_class._model_desc_

    def get(self, obj_id):
        obj = get_object_or_404(self.model_class, self.model_class.id == obj_id)
        return JsonResponse(self.model_serializer(obj).data)

    def get_operation_msg(self, obj):
        ACTIONS = {
            "GET": "查看%s",
            "PUT": "修改%s",
            "DELETE": "删除%s",
        }
        return ACTIONS[request.method] % str(obj)


class AbListResource(AbResource):
    model_class = None
    model_serializer = None
    method_decorators = AbResource.method_decorators + [login_required]
    # methods = ['get', 'post']
    parameterized_decorators = {
        'get': ['marshal_table', 'expect'],
        'post': ['marshal_item', 'expect']
    }
    class Meta:
        engine = 'mongo'
        abstract = True

    @property
    def msg_add_success(self):
        return '新增 %s 成功' % self.model_class._model_desc_

    def order_paginate(self, objs, pargs):
        return model_order_paginate(self.model_class, objs, pargs, self.Meta.engine)

    def get_operation_msg(self, objs):
        def _get_desc(objs):
            return objs[0]._model_desc_ + '列表'
        ACTIONS = {
            "GET": "查看%s",
            "POST": "新增%s"
        }
        return ACTIONS[request.method] % _get_desc(objs)


def model_order_paginate(model_class, objs, pargs, engine=DEFAULT_ENGINE):
    """
    :param objs:
    :param pargs: pargs.order_fields  # like "id,-create_time"
    :return:
    """  # todo@hy filter order_fields的正则校验
    if engine == 'peewee':
        order_string = pargs.order_fields
        order_fields = [field for field in order_string.split(',')]
        can_order_fields = []  # (status, True) # [key, desc]
        for order_field in order_fields:
            desc = order_field.startswith('-')
            key_name = order_field[1:] if desc else order_field
            if key_name in model_class._meta.fields:
                can_order_fields.append((key_name, desc))
            else:
                abort(400, "{} order fields error".format(key_name))
        fields = (
            getattr(model_class, key_name).desc()
            if desc else getattr(model_class, key_name).asc()
            for (key_name, desc) in can_order_fields)
        objs = objs.order_by(*fields)
        if pargs.page_size != -1:
            objs = objs.paginate(pargs.page, pargs.page_size)
        return list(objs)
    elif engine == 'mongo':
        if hasattr(pargs, 'order_fields') and pargs.order_fields is not None:
            objs = objs.order_by(pargs.order_fields)
        if pargs.page_size < -1:
            raise BadRequest('page_size(页长）不能小于-1')
        elif pargs.page_size == -1:
            return list(objs)
        return list(objs.skip((pargs.page - 1) * pargs.page_size).limit(pargs.page_size))


class AbActionResource(AbResource):
    method_decorators = AbResource.method_decorators

    class Meta:
        abstract = True


class AbLoginActionResource(AbResource):
    method_decorators = AbResource.method_decorators + [login_required]

    class Meta:
        abstract = True

# ------------------------------支持老用法 todo@hy 待删----------------------------------------------------


class Resource(Resource_):
    model_class = None
    model_serializer = None
    method_decorators = [request_logging]

    @property
    def engine(self):
        return DEFAULT_ENGINE


class SingleResource(Resource_):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]

    @property
    def msg_del_success(self):
        return '删除%s成功' % self.model_class._model_desc_

    @property
    def msg_edit_success(self):
        return '编辑%s成功' % self.model_class._model_desc_

    def get(self, obj_id):
        obj = get_object_or_404(self.model_class, self.model_class.id == obj_id)
        return JsonResponse(self.model_serializer(obj).data)

    def get_operation_msg(self, obj):
        ACTIONS = {
            "GET": "查看%s",
            "PUT": "修改%s",
            "DELETE": "删除%s",
        }
        return ACTIONS[request.method] % str(obj)


class ListResource(Resource_):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]

    @property
    def msg_add_success(self):
        return '新增 %s 成功' % self.model_class._model_desc_

    def order_paginate(self, objs, pargs, engine=DEFAULT_ENGINE):
        return model_order_paginate(self.model_class, objs, pargs, engine)

    def get_operation_msg(self, objs):
        def _get_desc(objs):
            return objs[0]._model_desc_ + '列表'
        ACTIONS = {
            "GET": "查看%s列表",
            "POST": "新增%s"
        }
        return ACTIONS[request.method] % _get_desc(objs)

class ActionResource(Resource_):
    model_class = None
    method_decorators = Resource.method_decorators


class LoginActionResource(Resource_):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]

