import copy
from flask_restplus import fields as frp_fields

try:
    from app import api_plus as api

    Model = api.model
except:
    from flask_restplus.model import OrderedModel as Model
from flask_restplus.marshalling import marshal


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
    def get_fields(cls, serializer_cls, name=None, add_action=True, format={}):
        if name is None:
            name = 'Table%s' % (serializer_cls,)
        model_fields = copy.deepcopy(serializer_cls(_many_=True).fields)
        if add_action:
            model_fields['actions'] = frp_fields.List(frp_fields.String)
        model = Model('ListItem%s' % (serializer_cls.__name__,), model_fields)
        res = copy.copy(cls.TABLE_FORMAT)
        res.update(format)
        res['data'] = frp_fields.List(frp_fields.Nested(model, skip_none=True), attribute='_items')
        return Model(name, res)


DEFAULT_PAGE_SIZE = 20


class QttTable(BaseTable):
    TABLE_FORMAT = {
        'code': frp_fields.Integer(attribute='_code'),
        'message': frp_fields.String,
        'total': frp_fields.Integer,
        'current_page': frp_fields.Integer(attribute='page'),
        'total_page': frp_fields.Integer(attribute='_total_page'),
    }

    @property
    def _code(self):
        if hasattr(self, 'code'):
            return self.code
        return 0

    @property
    def _total_page(self):
        if hasattr(self, 'total_page'):
            return self.total_page
        return int((self.total - 1) / self.page_size) + 1 if self.page_size!= -1 else 1


class SkvTable(BaseTable):
    TABLE_FORMAT = {
        'status': frp_fields.Integer(attribute='_status'),
        'message': frp_fields.String,
        'total': frp_fields.Integer,
        # 'current_page': frp_fields.Integer(attribute='page'),
        'total_page': frp_fields.Integer(attribute='_total_page'),
    }

    @property
    def _status(self):
        if hasattr(self, 'status'):
            return self.status
        return 200

    @property
    def _total_page(self):
        if hasattr(self, 'total_page'):
            return self.total_page
        return int((self.total - 1) / self.page_size) + 1 if self.page_size!= -1 else 1


Table = SkvTable


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


class QttSucResponse(BaseResponse):
    FORMAT = {
        'code': frp_fields.Integer(attribute='_code'),
        'message': frp_fields.String
    }

    @property
    def _code(self):
        if hasattr(self, 'code'):
            return self.code
        return 0


class SkvSucResponse(BaseResponse):
    FORMAT = {
        'status': frp_fields.Integer(attribute='_status'),
        'message': frp_fields.String
    }

    @property
    def _status(self):
        if hasattr(self, 'status'):
            return self.status
        return 200


SucResponse = SkvSucResponse


class ListResponse(SucResponse):
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


BASE_ERROR_FIELD = api.model('error_400', {
    'code': frp_fields.Integer,
    'message': frp_fields.String
})

SKV_ERROR_FIELD = api.model('error_400', {
    'status': frp_fields.Integer,
    'message': frp_fields.String
})

error_fields = SKV_ERROR_FIELD
