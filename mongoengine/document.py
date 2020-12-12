from bson import ObjectId
from mongoengine import fields, EmbeddedDocumentField, ReferenceField, DateTimeField, DateField
try:
    from dateutil import parser
except:
    from dateparser import parser
from ..widgets.decorators import classproperty
from ..config import CURRENT_REST_PLUS_CONFIG


class DocumentMixin:
    _restruct_ = False

    @property
    def db_dict(self):
        return self.to_mongo().to_dict()

    def to_dict(self, need_id=False):
        """
            将一条记录转为字典, 按需去除id
        :param need_id:
        :return:
        """
        res = self.to_mongo(use_db_field=False).to_dict()
        if not need_id and '_id' in res and '_id' not in self._fields_ordered:
            del res['_id']
        return res

    @classmethod
    def create_with(cls, data_dict, ignore_fields=None):
        ignore_fields = ignore_fields or CURRENT_REST_PLUS_CONFIG.config.base_ignore_fields
        s = cls()
        data_dict = {i: data_dict[i] for i in data_dict if i not in ignore_fields}
        cls.update_document(s, data_dict)
        return s

    def update_with(self, data_dict, ignore_fields=None):
        """
            利用字典内容更新对象。屏蔽掉若干字段。
        :param data_dict:
        :param ignore_fields:
        :return:
        """
        ignore_fields = ignore_fields or CURRENT_REST_PLUS_CONFIG.config.base_ignore_fields
        data_dict = {i: data_dict[i] for i in data_dict if i not in ignore_fields}
        DocumentMixin.update_document(self, data_dict)

    @staticmethod
    def update_document(document, data_dict):
        def field_value(field, value):
            if field.__class__ in (fields.ListField, fields.SortedListField):
                return [
                    field_value(field.field, item)
                    for item in value
                ]
            if field.__class__ in (
                    fields.ReferenceField,
            ) and type(value) in (ObjectId, str):
                return field.document_type.objects.get(pk=value)
            elif field.__class__ in (DateTimeField, DateField):
                if type(value) is str:
                    return parser.parse(value)
                else:
                    return value
            elif field.__class__ in (
                    fields.EmbeddedDocumentField,
                    fields.ReferenceField,
                    fields.GenericEmbeddedDocumentField,
                    fields.GenericReferenceField
            ):
                if hasattr(field.document_type, 'create_with') and field.document_type._restruct_:
                    return field.document_type.create_with(value)
                else:
                    return field.document_type(**value)
            else:
                return value

        for key, value in data_dict.items():
            try:
                field = document._fields[key]
                if isinstance(field, (EmbeddedDocumentField, ReferenceField)) and value is None:
                    continue
                else:
                    setattr(
                        document, key,
                        field_value(field, value)
                    )
            except Exception as e:
                print('err field %s - value %s' % (key, str(value)))
                raise Exception('err field %s - value %s' % (key, str(value)))

    @classproperty
    def _class_name_(cls):
        return cls.__module__ + '.' + cls.__name__

    def set_cached_property(self, k, v):
        """
            在行数据上存缓存。然后利用如下方式获取缓存数据。
            @cached_property
            def k(self):
                return v
        :param k:
        :param v:
        :return:
        """
        self.__dict__[k] = v

    def clear_cached_property(self, k):
        """
            清除对应的缓存数据
        :param k:
        :param v:
        :return:
        """
        if k in self.__dict__:
            del self.__dict__[k]
