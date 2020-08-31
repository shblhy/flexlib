from flask_restplus import Resource as OriResource
from utils.decorators import cached_property
from flask import render_template, flash, redirect, session, url_for, request, g
from flask_login import login_required, login_user, logout_user, current_user
from utils import pagination, get_object_or_404
from exlib.restviewset.response import JsonResponse, SuccessResponse, FailedResponse, TableResponse, ProjectError, \
    PermError
from exlib.restviewset.reqparse import RequestParser
from werkzeug.exceptions import abort, BadRequest
from utils.decorators import request_logging

DEFAULT_ENGINE = 'mongo'


class Resource(OriResource):
    model_class = None
    method_decorators = [request_logging]

    @property
    def engine(self):
        return DEFAULT_ENGINE


class SingleResource(OriResource):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]

    # def __init__(self, api=None, *args, **kwargs):
    #     self.api = api
    #     if hasattr(self.__class__, 'poster') and  self.model_class:
    #         self.__class__.poster.set_model_class(self.model_class)
    #     if hasattr(self.__class__, 'filter') and  self.model_class:
    #         self.__class__.filter.set_model_class(self.model_class)

    @cached_property
    def msg_del_success(self):
        # return '删除%s成功' % self.model_class._model_desc_
        return 'delete %s success' % self.model_class._model_desc_

    @cached_property
    def msg_edit_success(self):
        # return '编辑%s成功' % self.model_class._model_desc_
        return 'edit %s success' % self.model_class._model_desc_

    @cached_property
    def description_edit_success(self):
        # return '修改' % self.model_class._model_desc_
        return 'edit %s description success' % self.model_class._model_desc_

    def get(self, obj_id):
        """
            查询对象
        :param obj_id:
        :return:
        """
        obj = get_object_or_404(self.model_class, self.model_class.id == obj_id)
        return JsonResponse(self.model_serializer(obj).data)

    def get_operation_msg(self, obj):
        ACTIONS = {
            "GET": "查看%s",
            "PUT": "修改%s",
            "DELETE": "删除%s",
        }
        return ACTIONS[request.method] % str(obj)

    def save_operation(self, obj: object = None, message: str = None, obj_id: str = None, obj_type=None) -> str:
        from app.basic.operation_log.models import OperationLog
        if not any([obj is None, message is None]):
            assert Exception('obj和message必须有一项有值')
        msg = self.get_operation_msg(obj) if message is None else message
        o = OperationLog(
            message=msg,
            obj_id=str(obj.pk) if obj else obj_id,
            obj_type=getattr(type(obj) if obj else obj_type, '__name__', None),
            status='成功'
        ).save()
        return o.message


class ListResource(OriResource):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]

    # def __init__(self, api=None, *args, **kwargs):
    #     self.api = api
    #     if hasattr(self.__class__, 'poster') and  self.model_class:
    #         self.__class__.poster.set_model_class(self.model_class)
    #     if hasattr(self.__class__, 'filter') and  self.model_class:
    #         self.__class__.filter.set_model_class(self.model_class)

    @cached_property
    def msg_add_success(self):
        # return '新增%s成功' % self.model_class._model_desc_
        return 'add %s success' % self.model_class._model_desc_

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

    def save_operation(self, objs: object = None, message: str = None, obj_type=None) -> str:
        from app.basic.operation_log.models import OperationLog
        if not any([objs is None, message is None]):
            assert Exception('obj和message必须有一项有值')
        msg = self.get_operation_msg(objs) if message is None else message
        o = OperationLog(
            message=msg,
            obj_type=getattr(type(objs[0]) if objs else obj_type, '__name__', None),
            status='成功'
        ).save()
        return o.message

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
                # abort(400, "{} 排序字段错误".format(key_name))
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


class ActionResource(OriResource):
    model_class = None
    method_decorators = Resource.method_decorators


class ActionResourceLogin(OriResource):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]


class LoginActionResource(OriResource):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]
