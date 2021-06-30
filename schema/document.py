import json
from collections import OrderedDict, defaultdict
from mongoengine import StringField, ListField, ReferenceField, fields
from exlib.mongoengine.document import get_field, copy_field, copy_cls, get_field_cls
from exlib.widgets.decorators import class_property
from exlib.schema import SchemaException, get_schema_by_model


class SchemaMixin:
    @class_property
    def Schema(cls):
        schema_cls = get_schema_by_model(cls)
        if schema_cls:
            return schema_cls
        raise SchemaException('Document % 未设定过Schema:' % cls.__name__)

    @class_property
    def _schema(cls):
        schema_cls = get_schema_by_model(cls)
        if schema_cls:
            return schema_cls(cls)
        return None

    @class_property
    def schemas_conf(cls):
        return cls._schema.schemas_conf

    @class_property
    def schemas_extra(cls):
        return cls._schema.schemas_extra

    @class_property
    def schemas_show_fields(cls):
        return cls._schema.schemas_show_fields

    @class_property
    def schemas_conf(self):
        return self._schema.schemas_conf

    @classmethod
    def gen_schema(cls, skip_none=True, mask=[]):
        TYPES = {
            'string': ['mongoengine.fields.StringField', 'mongoengine.base.fields.ObjectIdField'],
            'array': ['mongoengine.fields.ListField'],
            'object': ['mongoengine.fields.EmbeddedDocumentField'],
            'integer': ['mongoengine.fields.IntField'],
            'float': ['mongoengine.fields.FloatField'],
            'datetime': ['mongoengine.fields.DatetimeField', 'mongoengine.fields.DateField'],
        }

        def _get_changes_field(field, type_field, *args):
            try:
                # if field.name in ('appointment_skv', 'appointment_time_new', 'carrier'):
                    # print(1)
                if args:
                    ori_dict = type_field(*args).__dict__
                else:
                    ori_dict = type_field().__dict__
                changed_field = {}
                for k, v in field.__dict__.items():
                    if k in ['creation_counter', '_owner_document']:
                        continue
                    else:
                        try:
                            if v != ori_dict.get(k):
                                json.dumps(v)
                                changed_field[k] = v
                        except:
                            pass
                return changed_field
            except Exception as e:
                print(e)

        def _get_full_name(field_type):
            return field_type.__module__ + '.' + field_type.__name__

        def _get_type(field_type):
            for k, v in TYPES.items():
                if field_type in v:
                    return k

        def _gen_rule(field):
            type_field = type(field)
            rules = []
            if type_field is fields.ReferenceField:
                changed_field = _get_changes_field(field, type_field, field.document_type)
            else:
                changed_field = _get_changes_field(field, type_field)
            if type_field is fields.StringField or issubclass(type_field, fields.StringField):
                for key in changed_field:
                    if key in ['required', 'max_length', 'min_length', 'regex']:
                        rules.append({
                            "key": key, "value": changed_field.get(key),
                            "message": field.front.get(key, 'field check error: %s' % key) if hasattr(field,
                                                                                                      'front') else ''
                        })
            elif type_field in [fields.IntField, fields.LongField, fields.FloatField, fields.DecimalField]:
                for key in changed_field:
                    if key in ['min_value', 'max_value']:
                        field_front = field.front if hasattr(field, 'front') else {}
                        rules.append({
                            "key": key, "value": changed_field.get(key),
                            "message": field_front.get(key, 'field check error: %s' % key)
                        })
            elif type_field in [fields.ReferenceField]:
                for key in changed_field:
                    if key in ['required']:
                        rules.append({
                            "key": key, "value": changed_field.get(key),
                            "message": field.front.get(key, 'field check error: %s' % key) if hasattr(field,
                                                                                                      'front') else ''
                        })
            else:
                for key in changed_field:
                    if key in ['required']:
                        rules.append({
                            "key": key, "value": changed_field.get(key),
                            "message": field.front.get(key, 'field check error: %s' % key) if hasattr(field,
                                                                                                      'front') else ''
                        })
            return rules

        def _parse_field(field, data, sorted_fields=None):
            type_field = type(field)
            field_type = _get_full_name(type_field)
            res = {'field_type': field_type}
            if type_field is fields.ReferenceField:
                doc_type = field.document_type
                changed_field = _get_changes_field(field, type_field, doc_type)
                res['document_type'] = _get_full_name(doc_type)
                res['type'] = 'reference'
                res['rules'] = _gen_rule(field)
            elif type_field is fields.EmbeddedDocumentField:
                doc_type = field.document_type
                res['document_type'] = _get_full_name(doc_type)
                res['type'] = 'object'
                changed_field = {"fields": _parse_cls(doc_type, data, sorted_fields)}
            elif type_field is fields.ListField:
                changed_field = _get_changes_field(field, type_field)
                sub_changed_field = _parse_field(field.field, data, sorted_fields)
                res['type'] = 'list'
                changed_field['items'] = sub_changed_field
                changed_field['rules'] = _gen_rule(field)
            else:
                changed_field = _get_changes_field(field, type_field)
                res['type'] = _get_type(field_type)
                res['rules'] = _gen_rule(field)
            res.update(changed_field)
            result = {}
            for k, v in res.items():
                if k not in mask:
                    result[k] = res[k]
            return result

        def _parse_cls(cls, data, sorted_fields=None):
            result = {}
            now_sorted_fields = []
            left_sorted_fields = {}
            if sorted_fields is None:
                now_sorted_fields = cls._fields_ordered
            else:
                for i in sorted_fields:
                    if '.' in i:
                        k1, k2 = i.split('.', 1)
                        now_sorted_fields.append(k1)
                        if k1 not in left_sorted_fields:
                            left_sorted_fields[k1] = []
                        left_sorted_fields[k1].append(k2)
                    else:
                        now_sorted_fields.append(i)
            now_sorted_fields = list(set(now_sorted_fields))
            for f in now_sorted_fields:
                v = cls._fields[f]
                item = _parse_field(v, data, list(set(left_sorted_fields[f])) if f in left_sorted_fields else None)
                if skip_none and item is not None:
                    result[f] = item
                else:
                    result[f] = item
            return result

        sorted_fields = getattr(cls, 'schemas_show_fields', None)
        data = {}
        res = _parse_cls(cls, data=data, sorted_fields=sorted_fields)
        result = {
            'fields': res,
            'sorted_fields': sorted_fields,
            'ref': data.get('ref', {})
        }
        if hasattr(cls, '_extra_'):
            result['_extra_'] = getattr(cls, '_extra_')
        return result

    @classmethod
    def _gen_condition_class(cls, index):
        params = cls.schemas_conf[index].get('check_fields', [])

        def copy_document(cur_cls, params):
            current_keys = []
            now_keys = {}
            for f in params:
                if isinstance(f, (list, tuple)):
                    key = f[0]
                    v = f[1]
                else:
                    key = f
                    has_custom = False
                    v = None
                current_keys.append(key)
                if '.' in key:
                    k1, k2 = key.split('.', 1)
                    if k1 not in now_keys:
                        now_keys[k1] = []
                    now_keys[k1].append((k2, v) if has_custom else k2)
                else:
                    if get_field_cls(cur_cls, key):
                        now_keys[key] = []
                    else:
                        now_keys[key] = None
            res = defaultdict(dict)
            for k in now_keys:
                key = k
                cus_params = {}
                if isinstance(k, (list, tuple)):
                    key = k[0]
                    cus_params = dict(k[1])
                field = get_field(cur_cls, key)
                if now_keys[k] is None:
                    now_parms = {'required': True}
                    if type(field) is StringField:
                        now_parms.update({'min_length': 1})
                    now_parms.update(cus_params)
                    res[key] = copy_field(field, **now_parms)
                elif isinstance(field, ListField):
                    if now_keys[k]:
                        inner_field_param = {"document_type_obj": copy_document(get_field_cls(cur_cls, k), now_keys[k])}
                        inner_field = copy_field(field.field, **inner_field_param)
                        cus_params['field'] = inner_field
                        res[key] = copy_field(field, **cus_params)
                    else:
                        now_parms = {'required': True}
                        res[key] = copy_field(field, **now_parms)
                elif isinstance(field, ReferenceField):
                    now_parms = {'required': True}
                    now_parms.update(cus_params)
                    res[key] = copy_field(field, **now_parms)
                else:
                    now_params = {'required': True} if k in current_keys else {}
                    cus_params['document_type'] = cus_params['document_type_obj'] = copy_document(get_field_cls(cur_cls, k), now_keys[k])
                    now_params.update(cus_params)
                    res[key] = copy_field(field, **now_parms)
            return copy_cls(cur_cls, **res)
        new_cls = copy_document(cls, params)
        if index in cls.schemas_extra:
            new_cls._extra_ = cls.schemas_extra[index]
        return new_cls

    @classmethod
    def gen_condition_class(cls, index):
        if not hasattr(cls, '_schemas_cls'):
            cls._schemas_cls = {}
        if index in cls._schemas_cls:
            return cls._schemas_cls[index]
        cls._schemas_cls[index] = cls._gen_condition_class(index)
        return cls._schemas_cls[index]

    @classmethod
    def gen_schemas(cls, keys=None):
        if keys is None:
            keys = ['origin'] + list(cls.schemas_conf.keys() if hasattr(cls, 'schemas_conf') else [])
        backend_fields = ['choices', 'db_field', 'field_type', 'document_type']
        res = OrderedDict()
        for key in keys:
            if key == 'origin':
                res[key] = cls.gen_schema(mask=backend_fields)
            else:
                cls_copy = cls.gen_condition_class(key)
                res[key] = cls_copy.gen_schema(mask=backend_fields)
        return res
