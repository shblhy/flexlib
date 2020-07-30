import copy
from flask_restplus import fields as frp_fields
from werkzeug.local import LocalProxy
from exlib.interface import CURRENT_REST_PLUS_CONFIG


class BaseTable(object):
    TABLE_FORMAT = {
        'total': frp_fields.Integer,
        'page': frp_fields.Integer(attribute='page'),
        'page_size': frp_fields.Integer(),
    }

    def __init__(self, _serializer_, format={}, **kwargs):
        """
            表格分页 支持：
                pargs
                page, page_size
                两种形式的输入
            表格信息 默认支持 code, message, total 参数
            表格额外信息 支持任意参数，但必须写好format，以便api文档展示

        :param _serializer_:
        :param format: 返回数据格式
        :param cal: 返回数据自定义计算式
        :param kwargs:
        """

        self._serializer_ = _serializer_
        now_format = copy.copy(self.__class__.TABLE_FORMAT)
        now_format.update(format)
        self.format = now_format
        if 'message' in kwargs:
            self.message = kwargs.pop('message')
        else:
            self.model = _serializer_.Meta.model
            self.message = "%s列表" % (self.model._model_desc_ or self.model.__class__.__name__)
        self.total = kwargs.pop('total', None) or len(self._items)
        self.add_action = kwargs.pop('add_action', False)
        pargs = kwargs.pop('pargs', None)
        if pargs:
            self.page = self.current_page = pargs.page
            self.page_size = pargs.page_size
        else:
            self.page = kwargs.pop('pargs', 0)
            self.page_size = kwargs.pop('pargs', DEFAULT_PAGE_SIZE)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def fields(self):
        return self.get_fields(self._serializer_.__class__, add_action=self.add_action, format=self.format)

    def fields_model(self, name=None, add_action=False):
        if name is None:
            name = 'Table%s' % (self.__class__,)
        return self.get_fields(self._serializer_.__class__, name=name, add_action=add_action, format=self.format)

    @property
    def _items(self):
        return self._serializer_._instance_ or []

    # @property
    # def data(self):
    #     return marshal(self, self.fields())

    @classmethod
    def get_fields(cls, serializer_cls, name=None, add_action=True, skip_none=True, format={}):
        if name is None:
            name = 'Table%s' % (serializer_cls,)
        model_fields = copy.deepcopy(serializer_cls(_many_=True).fields)
        if add_action:
            model_fields['actions'] = frp_fields.List(frp_fields.String)
        model = Model('ListItem%s' % (serializer_cls.__name__,), model_fields)
        res = copy.copy(cls.TABLE_FORMAT)
        res.update(format)
        res['data'] = frp_fields.List(frp_fields.Nested(model, skip_none=skip_none), attribute='_items')
        return Model(name, res)


DEFAULT_PAGE_SIZE = 20


class BaseResponse(object):
    FORMAT = {
        'message': frp_fields.String
    }

    def __init__(self, _serializer_, format={}, **kwargs):
        self._serializer_ = _serializer_
        # self.model = _serializer_.Meta.model
        # if 'message' in kwargs:
        #     self.message = kwargs.pop('message')
        # else:
        #     self.model = _serializer_.Meta.model
        self.message = kwargs.pop('message', '')
        now_format = copy.copy(self.__class__.FORMAT)
        now_format.update(format)
        self.format = now_format

        for k, v in kwargs.items():
            setattr(self, k, v)

    def fields(self):
        return self.get_fields(self._serializer_.__class__, format=self.format)

    def fields_model(self, name=None, add_action=False):
        if name is None:
            name = 'Table%s' % (self.__class__,)
        return self.get_fields(self._serializer_.__class__, name=name, format=self.format)

    @property
    def _item(self):
        return self._serializer_._instance_ or {}

    @classmethod
    def get_fields(cls, serializer_cls, name=None, format={}, **kwargs):
        if name is None:
            name = 'Response%s' % (serializer_cls,)
        res = copy.copy(cls.FORMAT)
        res.update(format)
        res['data'] = frp_fields.Nested(serializer_cls(**kwargs).fields_model(), attribute='_item')
        return Model(name, res)


class ListResponseMixin:
    @classmethod
    def get_fields(cls, serializer_cls, name=None, format={}):
        if name is None:
            name = 'Response%s' % (serializer_cls,)
        res = copy.copy(cls.FORMAT)
        model_fields = copy.deepcopy(serializer_cls().fields)
        model = Model('ListItem%s' % (serializer_cls.__name__,), model_fields)
        res.update(format)
        res['data'] = frp_fields.List(frp_fields.Nested(model), attribute='_item')
        return Model(name, res)


class BaseListResponse(BaseResponse, ListResponseMixin):
    pass


def _get_base_error_field():
    api = CURRENT_REST_PLUS_CONFIG.current_api
    return api.model('error_400', {
        'code': frp_fields.Integer,
        'message': frp_fields.String
    })


def _get_skv_error_field():
    api = CURRENT_REST_PLUS_CONFIG.current_api
    return api.model('error_400', {
        'status': frp_fields.Integer,
        'message': frp_fields.String
    })


def _get_model():
    api = CURRENT_REST_PLUS_CONFIG.current_api
    return api.model


def get_suc_response():
    return CURRENT_REST_PLUS_CONFIG.response_cls


SucResponse = LocalProxy(lambda: get_suc_response())


def get_table_cls():
    return CURRENT_REST_PLUS_CONFIG.table_cls


Table = LocalProxy(lambda: get_table_cls())


def get_list_response():
    return CURRENT_REST_PLUS_CONFIG.list_response_cls


ListResponse = LocalProxy(lambda: get_list_response())
BASE_ERROR_FIELD = LocalProxy(lambda: _get_base_error_field())
SKV_ERROR_FIELD = LocalProxy(lambda: _get_skv_error_field())
Model = LocalProxy(lambda: _get_model())
error_fields = LocalProxy(lambda: _get_skv_error_field())
