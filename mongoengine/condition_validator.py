from mongoengine import errors, BooleanField, EmbeddedDocumentField, EmbeddedDocumentListField, ListField, StringField
import json
from collections import defaultdict
from importlib import import_module, _bootstrap_external


def deepcopy(cls_copy):
    """
        用重载module的方式 对cls进行深拷贝
    :param cls_copy:
    :return:
    """
    test_module = import_module(cls_copy.__module__)
    module_path, _, suffix = test_module.__file__.rpartition('.')
    module_path, _, module_name = module_path.rpartition('/')
    ff = _bootstrap_external.FileFinder(module_path, (_bootstrap_external.SourceFileLoader, ['.py']))
    mod = ff.find_module(module_name).load_module()
    return getattr(mod, cls_copy.__name__)


class ValidationErrorEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, errors.ValidationError):
            return o.message
        else:
            return json.JSONEncoder.default(self, o)


class ConditionValidatorMixin:
    """
        条件校验及条件Schema:
        依据不同的规则（用户权限、用户与数据的关系），进行不同的校验，或提供不同的Schema
        权限和条件类可变逻辑难于记忆，故强制要求在代码里写明判定逻辑，并在schema接口返回描述到前端。
    """
    rules_desc = {

    }
    validate_conf = {}

    def validate_according_to(self, action):
        """
            条件校验器 按配置进行校验
            校验通过，返回TRUE
            不通过，返回err_msgs
            err_msgs包括字段名和描述
            ！！！！解决深拷贝问题之前，暂时只在脚本中使用此方法
        :param action:
        :return:
        """
        ori_cls = type(self)
        fields = ori_cls.validate_conf[action].get('check_fields', [])
        res = defaultdict(dict)
        for f in fields:
            key = f
            if isinstance(f, (list, tuple)):
                key = f[0]
                res[key] = dict(f[1])
            res[key].update({'required': True})
        fields = res

        def _get_field(cls_copy, key):
            if '.' not in key:
                field = cls_copy._fields[key]
                return field
            else:
                keys = key.split('.', 1)
                attr_key = keys[0]
                new_key = keys[1]
                v = cls_copy._fields.get(attr_key)
                if new_key == '_str_':
                    return v.field
                if type(v) in (EmbeddedDocumentField, EmbeddedDocumentListField):
                    res = _get_field(v.document_type, new_key)
                else:
                    # 目前支持的复杂field 仅存在 ListField 及以上两种。
                    res = _get_field(v.field.document_type, new_key)
                return res

        cls_copy = deepcopy(ori_cls)
        cls_fields_dict = {}
        # 确认校验替换参数 String型加入了默认参数
        for field_key in fields:
            field = _get_field(cls_copy, field_key)
            cls_fields_dict[field_key] = field
            if type(field) is StringField and not field.min_length and 'min_length' not in fields[field_key]:
                fields[field_key].update({'min_length': 1})
        # 最终获得fields 即各个字段及它校验时需要的参数 格式为 {field_key:{需更新的field_params}}
        fields_changed_params = defaultdict(dict)
        # 格式为 {field_key:{原始的field_params}}
        cls_fields_changed_params = set([])
        """
            已修改的对象id保存在cls_fields_changed_params中
            一开始使用默认deepcopy 未完成对象深拷贝，导致原始对象的field被修改，不得不进行还原操作
            现在保存fields_changed_params，是为了避免对同一个对象进行多次更改属性动作，出于谨慎，原还原动作也未移除
        """
        try:
            result = None
            for k in cls_fields_dict:
                i = cls_fields_dict[k]
                if id(i) in cls_fields_changed_params:
                    continue
                else:
                    cls_fields_changed_params.add(id(i))
                for attr in fields[k]:
                    fields_changed_params[k][attr] = getattr(i, attr)
                    setattr(i, attr, fields[k][attr])
            self_copy = cls_copy.create_with(self.to_dict())
            self_copy.validate()

        except errors.ValidationError as e:
            result = json.loads(json.dumps(e.errors, cls=ValidationErrorEncoder))
        finally:
            # 对类进行还原操作
            for field_key in fields_changed_params:
                field = cls_fields_dict[field_key]
                for attr in fields_changed_params[field_key]:
                    setattr(field, attr, fields_changed_params[field_key][attr])
        return result
