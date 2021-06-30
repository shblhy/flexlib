import os, importlib
from dataclasses import dataclass
from typing import List
from copy import deepcopy
from collections import OrderedDict, defaultdict
from ..widgets.decorators import cached_property


class SchemaException(Exception):
    pass


@dataclass
class ErrDetailItem:
    index: str = ''
    info: str = ''


@dataclass
class SchemaField:
    desc: str = None  # 中文描述
    condition: str = None # 条件 一个lambda方法，或conditions的某个方法名 None表示无条件进行校验
    func: str = None  # 校验的逻辑方法名
    indexes: List[str] = None # 校验的index
    condition_funcs: dict = None
    relation_funcs: dict = None
    batch: bool = False #成批处理，而非单条记录处理

    def get_func(self):
        """生产数据校验的方法字典"""
        res = {}
        if self.indexes:
            for key in self.indexes:
                if key == 'origin':
                    res['%s_%s_%s' % (self.name, self._model.__name__, key)] = self._model.validate
                else:
                    cls = self._model.gen_condition_class(key)
                    res['%s_%s_%s' % (self.name, self._model.__name__, key)] = lambda x: cls._from_son(x.db_dict).validate()
        if self.func:
            if type(self.func) is str:
                res['%s_%s'% (self.name, self.func)] = self.funcs[self.func]
            elif type(self.func) is list:
                for index, func in enumerate(self.func):
                    if type(func) is str:
                        res['%s_%s' % (self.name, func)] = self.funcs[func]
                    else:
                        res['%s_%s_%s' % (self.name, index, func.__name__)] = func
            else:
                res['%s_%s' % (self.name, self.func.__name__)] = self.func
        return res

    @cached_property
    def real_funcs(self):
        return self.get_func()

    def validate_func(self):
        def res_func(x):
            for _, v in self.real_funcs.items():
                try:
                    if v(x) is False:
                        return False
                    return True
                except:
                    return False
        return res_func

    def validate_func_detail(self):
        details = []

        def res_func(x):
            for f, v in self.real_funcs.items():
                try:
                    if v(x) is False:
                        details.append(ErrDetailItem(f, '%s check error' % v.__name__))
                except Exception as e:
                    details.append(ErrDetailItem(f, '%s raise exception %s' % (v.__name__, str(e))))
            return details
        return res_func

    def match(self, obj):
        if self.condition is None:
            return True
        if type(self.condition) is str:
            return self.funcs[self.condition](obj)
        return self.condition(obj)

    def validate(self, obj, detail=True):
        if not detail:
            return self.validate_func()(obj)
        else:
            err_detail = self.validate_func_detail()(obj)
            return err_detail

    def set_model(self, model, schema):
        self._model = model
        self._schema = schema

    def set_name(self, name):
        self.name = name

    @property
    def funcs(self):
        return self._schema.funcs


class SchemaMetaclass(type):
    """
        子类会继承父类增加fields
        conf 和 extra 会进行merge
    """

    extend_dict_attrs = ['schemas_conf', 'schemas_extra', 'schemas_funcs']
    _schema_names = defaultdict(list)
    _schema_classes = {}
    _schema_models = {}
    schemas_show_fields = []

    @classmethod
    def _get_schema_fields(cls, bases, attrs):
        fields = [(field_name, attrs.get(field_name)) for field_name, obj in list(attrs.items())
                  if (isinstance(obj, type) and issubclass(obj, SchemaField)) or issubclass(obj.__class__, SchemaField)]
        for base in reversed(bases):
            if hasattr(base, '_fields'):
                fields = [(field_name, obj) for field_name, obj in base._fields.items()
                          if field_name not in attrs] + fields
        return OrderedDict(fields)

    def __new__(cls, name, bases, attrs):
        attrs['_fields'] = deepcopy(cls._get_schema_fields(bases, attrs))
        if 'model' not in attrs:
            if '__qualname__' in attrs and '.' in attrs['__qualname__']:
                model_path = attrs['__module__'] + '.'+ attrs['__qualname__'].split('.')[0]
            else:
                raise SchemaException('Schema:%s未指定Model' % name)

        else:
            model_path = attrs['model'].__module__+ '.' + attrs['model'].__name__
        for attr in cls.extend_dict_attrs:
            attr_dic = attrs.get(attr, {})
            for base in reversed(bases):
                if hasattr(base, attr):
                    attr_dic.update(getattr(base, attr))
            attrs[attr] = attr_dic
        res = super(SchemaMetaclass, cls).__new__(cls, name, bases, attrs)
        SchemaMetaclass._schema_names[res.__name__].append(res.__module__ + '.' + res.__name__)
        SchemaMetaclass._schema_classes[res.__module__ + '.' + res.__name__] = SchemaMetaclass._schema_models[model_path] = res
        return res


def get_schema(name):
    if name in SchemaMetaclass._schema_names:
        if len(SchemaMetaclass._schema_names[name]) == 1:
            return SchemaMetaclass._schema_classes[SchemaMetaclass._schemas_names[name]]
        else:
            raise SchemaException('存在同名Schema:%s，必须指定Module' % name)
    raise SchemaException('不存在的Schema:%s' % name)


def get_schema_by_model(cls):
    return SchemaMetaclass._schema_models.get(cls.__module__ + '.' + cls.__name__)


def register_all_schemas(app_root='app'):
    """app创建完成前，应进行schmas注册"""
    def import_model_schemas(mod):
        schema_path = '/schemas/'.join(mod.__file__.rsplit('/models/', 1))
        if '/schemas/' in schema_path and os.path.exists(schema_path):
            schema_path = schema_path[:schema_path.rfind('/')]
            for root, dirs, files in os.walk(schema_path):
                for f in files:
                    if f.endswith('.py') and f != '__init__.py':
                        path = mod.__package__.replace('.models', '.schemas') + '.' + f.replace('.py', '')
                        importlib.import_module(path)

    def get_module(mod):
        for name in dir(mod):
            var = getattr(mod, name)
            if type(var).__name__ == 'module' and var.__package__.startswith('app.'):
                if var.__name__.endswith('.models'):
                    import_model_schemas(var)
                get_module(var)

    app_root = __import__(app_root)
    get_module(app_root)
