import uuid
from copy import deepcopy, copy
from bson import ObjectId
from mongoengine import fields, EmbeddedDocumentField, EmbeddedDocumentListField, ReferenceField, DateTimeField, DateField, ListField, Document, StringField
from mongoengine.base.metaclasses import DocumentMetaclass, TopLevelDocumentMetaclass
from mongoengine.queryset import QuerySet
try:
    from dateutil import parser
except:
    from dateparser import parser
from ..widgets.decorators import classproperty


def get_field_cls(cls, key, silent=True):
    def _get_cls(v):
        if hasattr(v, 'document_type'):
            return v.document_type
        elif hasattr(v, 'field') and hasattr(v.field, 'document_type'):
            return v.field.document_type
        else:
            if silent:
                return None
            raise Exception('not a document_type')
    return _get_cls(get_field(cls, key))


def get_field(cls, key):
    if '.' not in key:
        field = cls._fields[key]
        return field
    attr_key, new_key = key.split('.', 1)
    v = cls._fields.get(attr_key)
    if hasattr(v, 'document_type'):
        return get_field(v.document_type, new_key)
    else:
        return get_field(v.field.document_type, new_key)


def copy_field(_field, **kwargs):
    new_field = copy(_field)
    new_field.__dict__.update(kwargs)
    return new_field


def copy_cls(cls, base_cls=None, **kwargs):
    if not base_cls:
        base_cls = cls.__bases__[0]
    attrs = dict(cls.__dict__)
    attrs.update(kwargs)
    return DocumentMetaclass.__new__(mcs=DocumentMetaclass,
                                     name='%s%s' % (cls.__name__, uuid.uuid1()),
                                     bases=(base_cls,), attrs=attrs)


class DocumentMixin:
    _restruct_ = False
    base_ignore_fields = []

    @classmethod
    def copy_base_class(cls, base_cls=None, **kwargs):
        return copy_cls(cls, base_cls, **kwargs)

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
    def parse_db_key(cls, data):
        res = {}
        
        def _parse_data(dest, dic, cur_cls):
            reverse_dic = cur_cls._reverse_db_field_map
            for db_key, v in dic.items():
                if db_key in reverse_dic:
                    cls_key = reverse_dic[db_key]
                    dest[cls_key] = v
                    field = getattr(cur_cls, cls_key)
                    if isinstance(field, ListField):
                        if isinstance(field.field, EmbeddedDocumentField):
                            next_cls = field.field.document_type
                            for ind,ite in enumerate(v):
                                dest[cls_key][ind] = {}
                                _parse_data(dest[cls_key][ind], deepcopy(ite), next_cls)
                        elif isinstance(field.field, StringField):
                            dest[cls_key] = [str(i) for i in v]
                        else:
                            for ind, ite in enumerate(v):
                                dest[cls_key][ind] = field.field(**ite)
                    elif isinstance(field, EmbeddedDocumentField):
                        next_cls = field.document_type
                        dest[cls_key] = {}
                        _parse_data(dest[cls_key], deepcopy(dic[db_key]), next_cls)
        _parse_data(res, data, cls)
        return res

    @classmethod
    def create_with(cls, data_dict, ignore_fields=None):
        ignore_fields = ignore_fields or cls.base_ignore_fields
        s = cls()
        data_dict = {i: data_dict[i] for i in data_dict if i not in ignore_fields}
        DocumentMixin.update_document(s, data_dict)
        return s

    def update_with(self, data_dict, ignore_fields=None):
        """
            利用字典内容更新对象。屏蔽掉若干字段。
        :param data_dict:
        :param ignore_fields:
        :return:
        """
        ignore_fields = ignore_fields or self.base_ignore_fields
        data_dict = {i: data_dict[i] for i in data_dict if i not in ignore_fields}
        DocumentMixin.update_document(self, data_dict)

    @staticmethod
    def update_document(document, data_dict):
        def field_value(field, value):
            if field.__class__ in (fields.ListField, fields.SortedListField):
                if value is None:
                    return None
                else:
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
                    if field.__class__ is DateField:
                        return parser.parse(value).date()
                    else:
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
                if isinstance(field, (EmbeddedDocumentField, ReferenceField, ListField, EmbeddedDocumentListField)) and value is None:
                    setattr(document, key, None)
                else:
                    setattr(
                        document, key,
                        field_value(field, value)
                    )
            except Exception as e:
                raise Exception('err field %s - value %s | %s' % (key, str(value), str(e)))

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

    def has_cached_property(self, k):
        return k in self.__dict__

    # ----------------------- reference fields 相关处理 -----------------------
    # LazyReferenceField 必须先fetch后使用,不符合需要的处理方式
    # fill_refer 在不改变ReferenceField的处理方式的前提下，减少了查询量
    # fill_refer 由对象调用,将refer_cls作为参数
    # fill_qs_refer 由refer_cls调用，将query_set转变的list作为参数
    def fill_refer(self, refer_cls, source=None, fields_dic=None):
        if fields_dic is None:
            ref_fields = self.__class__.get_reference_fields(refer_cls)
            fields_dic = {f: self.__class__._fields[f] for f in ref_fields if '.' not in f}
        else:
            ref_fields = list(fields_dic.keys())
        if source is None:
            source = self.get_all_ref_obj_dict(refer_cls, ref_fields)
        for field_key, field in fields_dic.items():
            try:
                if '.' not in field_key:
                    if isinstance(field, ListField) and isinstance(field.field, ReferenceField):
                        self._data[field_key] = [source[dbref.id] for dbref in self._data[field_key]]
                    elif self._data.get(field_key):
                        self._data[field_key] = source[self._data[field_key].id]
            except Exception as e:
                raise e
        suffix_dic = {}
        for field_key in ref_fields:
            if '.' in field_key:
                attr, suffix = field_key.split('.', 1)
                if attr not in suffix_dic:
                    suffix_dic[attr] = [suffix]
                else:
                    suffix_dic[attr].append(suffix)
        for attr, suffix in suffix_dic.items():
            if attr in self._data:
                if isinstance(self._data[attr], list):
                    for x in self._data[attr]:
                        x.fill_refer(refer_cls, source)
                else:
                    self._data[attr].fill_refer(refer_cls, source)

    @classmethod
    def fill_qs_refer(cls, qs_list, refer_cls,  source=None) -> list:
        """
        :param source:
        :return:
        """
        if not isinstance(qs_list, list):
            raise Exception('只接受数组型参数，QuerySet请自行转化为数组')
        ref_fields = cls.get_reference_fields(refer_cls)
        fields_dic = cls.get_reference_fields_dic(refer_cls)
        if source is None:
            ids = set()
            for d in qs_list:
                for i in d.get_all_ref_ids(ref_fields):
                    ids.add(i)
            source = {i.id: i for i in refer_cls.objects(id__in=ids)}
        for d in qs_list:
            d.fill_refer(refer_cls, source, fields_dic)

    @classmethod
    def get_reference_fields(cls, target_cls=None):
        """
            target_cls = None -> {'key':cls}
            target_cls -> ['key']
        :param target_cls:
        :return:
        """
        key = '__reference_fields_%s' % target_cls.__name__
        if hasattr(cls, key):
            return getattr(cls, key)
        res = []
        for f, v in cls._fields.items():
            if (isinstance(v, ReferenceField) and v.document_type is target_cls) or \
                    (isinstance(v, ListField) and isinstance(v.field,ReferenceField) and v.field.document_type is target_cls):
                res.append(f)
            elif isinstance(v, EmbeddedDocumentField):
                if hasattr(v.document_type, 'get_reference_fields'):
                    ref = v.document_type.get_reference_fields(target_cls)
                    if ref:
                        for _i in ref:
                            res.append('%s.%s' % (f, _i))
            elif isinstance(v, ListField) and isinstance(v.field,EmbeddedDocumentField):
                if hasattr(v.field.document_type, 'get_reference_fields'):
                    ref = v.field.document_type.get_reference_fields(target_cls)
                    if ref:
                        for _i in ref:
                            res.append('%s.%s' % (f, _i))
        setattr(cls, key, res)
        return res

    @classmethod
    def get_reference_fields_dic(cls, target_cls=None):
        """
            target_cls = None -> {'key':cls}
            target_cls -> ['key']
        :param target_cls:
        :return:
        """
        fields = cls.get_reference_fields(target_cls)
        return {f: get_field(cls, f) for f in fields}

    def get_all_ref_ids(self, fields):
        ids = []
        suffix_dic = {}
        for field_key in fields:
            if '.' not in field_key:
                dbref = self._data[field_key] if field_key in self._data else None
                if dbref:
                    if isinstance(dbref, list):
                        ids.extend([i.id for i in dbref])
                    else:
                        ids.append(dbref.id)
            else:
                attr, suffix = field_key.split('.', 1)
                if attr not in suffix_dic:
                    suffix_dic[attr] = [suffix]
                else:
                    suffix_dic[attr].append(suffix)
        for attr, suffix in suffix_dic.items():
            if attr in self._data:
                if isinstance(self._data[attr], list):
                    for x in self._data[attr]:
                        ids.extend(x.get_all_ref_ids(suffix))
                else:
                    ids.extend(self._data[attr].get_all_ref_ids(suffix))
        return ids

    def get_all_ref_obj_dict(self, refer_cls, ref_fields):
        ids = self.get_all_ref_ids(ref_fields)
        res = refer_cls.objects(id__in=ids)
        return {i.id: i for i in res}

    def fill_qs_refer_all(self):
        return
