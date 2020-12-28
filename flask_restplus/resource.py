from flask_restplus import Resource as Resource_
from flask import request
from flask_login import login_required
from utils import get_object_or_404
from exlib.webbase.response import JsonResponse
from werkzeug.exceptions import abort, BadRequest
from ..widgets.decorators import request_logging
from ..config import CURRENT_REST_PLUS_CONFIG

DEFAULT_ENGINE = CURRENT_REST_PLUS_CONFIG.db_engine


class Resource(Resource_):
    model_class = None
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


class ActionResource(Resource_):
    model_class = None
    method_decorators = Resource.method_decorators


class LoginActionResource(Resource_):
    model_class = None
    method_decorators = Resource.method_decorators + [login_required]
