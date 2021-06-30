import copy
import six
import logging
from collections import OrderedDict
from flask_restplus.fields import Raw
from flask_restplus.model import ModelBase
from flask_restplus.marshalling import marshal
from ...widgets.decorators import class_property
from ...flex import current_flex
logger = logging.getLogger(__name__)
ALL_FIELDS = '__all__'
_serializer_registry = {}

"""
    marshal中以字典定义数据结构，以格式化对象得到所需数据。
    字典无法继承重写，无法自定义方法，故自行编写了Serializer完成该功能，简化代码。
    ModelSerializer完成了从peewee model到目标结构的序列化，完成了进一步简化工作。
    参考 flask_restplus 的 marshal 和 django_rest_framework 的Serializer，可以视为两者的结合
"""


class SerializerMetaclass(type):
    """
    This metaclass sets a dictionary named `_declared_fields` on the class.

    Any instances of `Field` included as attributes on either the class
    or on any of its superclasses will be include in the
    `_declared_fields` dictionary.
    """

    @classmethod
    def _get_declared_fields(cls, bases, attrs):
        fields = [(field_name, attrs.get(field_name))
                  for field_name, obj in list(attrs.items())
                  if (isinstance(obj, type) and issubclass(obj, Raw)) or issubclass(obj.__class__, Raw)]
        for base in reversed(bases):
            if hasattr(base, '_declared_fields'):
                fields = [
                             (field_name, obj) for field_name, obj
                             in base._declared_fields.items()
                             if field_name not in attrs
                         ] + fields
        return OrderedDict(fields)

    def __new__(cls, name, bases, attrs):
        attrs['_declared_fields'] = cls._get_declared_fields(bases, attrs)
        return super(SerializerMetaclass, cls).__new__(cls, name, bases, attrs)


@six.add_metaclass(SerializerMetaclass)
class Serializer(ModelBase):
    _format_base = current_flex.formats['Response']
    _format_list = current_flex.formats['ListResponse']
    _format_table = current_flex.formats['Table']
    _error_fields = current_flex.formats['error_fields']

    def __init__(self, instance=None, **kwargs):
        """
        :param instance: 待转化对象,支持字典
        :param kwargs:
        """
        self._instance_ = instance
        self.name = self.__class__.__module__ + '.' + self.__class__.__name__
        if '_many_' in kwargs:
            self.many = kwargs.pop('_many_')
        else:
            self.many = isinstance(instance, list)
        self.skip_none = kwargs.pop('_skip_none_', False)
        _serializer_registry[self.__class__.__module__ + '.' + self.__class__.__name__] = self.__class__


    @classmethod
    def get_fields(cls):
        return copy.deepcopy(cls._declared_fields)

    @class_property
    def fields(cls):
        """
        A dictionary of {field_name: field_instance}.OrderedDict
        """
        if not hasattr(cls, '_fields'):
            cls._fields = OrderedDict([])
            for key, value in cls.get_fields().items():
                cls._fields[key] = value
                if hasattr(cls, 'get_%s' % key):
                    value.attribute = '__func__%s' % key
        return cls._fields

    def parse_data_item(self, obj):
        for field in self.fields:
            if hasattr(self, 'get_%s' % field):
                func = getattr(self, 'get_%s' % field)
                setattr(obj, '__func__%s' % field, func(obj, field))

    def prepare_data(self):
        """parse_data_item进行数据准备，以免在marshal data时重复查询数据库"""
        pass

    def handle_data(self):
        if not self.many:
            self.parse_data_item(self._instance_)
        else:
            for i in self._instance_:
                self.parse_data_item(i)

    @property
    def data(self):
        if not self._instance_:
            return [] if self.many else {}
        self.prepare_data()
        self.handle_data()
        if not self.many:
            return marshal(self._instance_, self.fields, ordered=True, skip_none=self.skip_none)
        else:
            return [marshal(item, self.fields, ordered=True, skip_none=self.skip_none) for item in self._instance_]

    def fields_model(self):
        return self

    def table(self, **kwargs):
        self.prepare_data()
        self.handle_data()
        return self._format_table(
            _serializer_=self,
            **kwargs
        )

    def item(self, **kwargs):
        return self._format_base(
            _serializer_=self,
            **kwargs
        )

    def lists(self, **kwargs):
        return self._format_list(
            _serializer_=self,
            **kwargs
        )

    def __unicode__(self):
        return '{{cls_name}}({name},{{{fields}}})'.format(cls_name=self.__class__.__name__, name=self.name, fields=','.join(self.fields.keys()))

    @classmethod
    def items(cls):
        return cls.fields.items()

    def values(self):
        return list(self.fields.values())

    def __iter__(self, *args, **kwargs):
        pass

    def __len__(self, *args, **kwargs):
        return len(self.fields)

    def __getitem__(self, y):
        return self.fields[y]


def regist_serializer(api):
    for key, cls in _serializer_registry.items():
        api.model(key, cls.fields)
