from collections import OrderedDict
from flask_restplus import fields as frp_fields
from flask_restplus.marshalling import marshal
from ...widgets.decorators import cached_property
from ...flask_restplus.fields import DateLocal
from ...widgets.decorators import class_property
from .serializers import Serializer, ALL_FIELDS, logger, _serializer_registry


class ModelSerializer(Serializer):
    """
        对象序列化，支持peewee,sqlalchemy等多种orm
    """
    model_class = None
    default_datetimefield = DateLocal

    def __init__(self, instance=None, **kwargs):
        """
        :param instance: 待转化对象
        :param kwargs:
        """
        # super(ModelSerializer, self).__init__(**kwargs)
        kwargs.pop('_many_', None)
        self._instance_ = instance
        self.name = self.__class__.__module__ + '.' + self.__class__.__name__
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.many = self.get_many()
        self.skip_none = kwargs.pop('_skip_none_', False)
        _serializer_registry[self.__class__.__module__ + '.' + self.__class__.__name__] = self.__class__

    def get_many(self):
        many = True
        if self.engine == 'peewee':
            import peewee as pw
            if isinstance(self._instance_, pw.ModelSelect):
                many = isinstance(self._instance_._from_list, (list, tuple))
            else:
                many = False
        elif self.engine == 'mongo':
            import mongoengine as mge
            if isinstance(self._instance_, mge.queryset.queryset.QuerySet) or isinstance(self._instance_,
                                                                                         (list, tuple)):
                many = True
            else:
                many = False
        elif self.engine == 'sqlalchemy':
            pass
        return many

    # @cached_property
    @class_property
    def engine(self):
        model = getattr(self.Meta, 'model')
        if 'peewee' in type(model).__module__:
            return 'peewee'
        elif 'mongo' in type(model).__module__:
            return 'mongo'

    @classmethod
    def get_mapping_field_func(cls):
        funcs = {
            'peewee': cls.get_base_fields_by_pw_field,
            'mongo': cls.get_base_fields_by_mge_field,
            'sqlalchemy': None
        }
        return funcs[cls.engine]

    @classmethod
    def get_all_fields_model(cls, target_cls):
        """
            仅支持mongoengine
        :param cls:
        :return:
        """
        name = 'EmbeddedDocument %s' % (target_cls.__module__ + '.' + target_cls.__name__,)
        return cls._api.model(name, {key: cls.get_base_fields_by_mge_field(target_cls._fields[key]) for key in target_cls._fields})

    @classmethod
    def get_all_fields_func(cls):
        funcs = {
            'peewee': lambda m: list(m._meta.fields.keys()),
            'mongo': lambda m: list(m._fields.keys()),
            'sqlalchemy': None
        }
        return funcs[cls.engine]

    @cached_property
    def meta_ready(self):
        assert hasattr(self, 'Meta'), (
            'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        assert hasattr(self.Meta, 'model'), (
            'Class {serializer_class} missing "Meta.model" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        fields = getattr(self.Meta, 'fields', None)
        exclude = getattr(self.Meta, 'exclude', None)

        if fields and fields != ALL_FIELDS and not isinstance(fields, (list, tuple)):
            raise TypeError(
                'The `fields` option must be a list or tuple or "__all__". '
                'Got %s.' % type(fields).__name__
            )

        if exclude and not isinstance(exclude, (list, tuple)):
            raise TypeError(
                'The `exclude` option must be a list or tuple. Got %s.' %
                type(exclude).__name__
            )

        assert not (fields and exclude), (
            "Cannot set both 'fields' and 'exclude' options on "
            "serializer {serializer_class}.".format(
                serializer_class=self.__class__.__name__
            )
        )

        assert not (fields is None and exclude is None), (
            "Creating a ModelSerializer without either the 'fields' attribute "
            "or the 'exclude' attribute has been deprecated since 3.3.0, "
            "and is now disallowed. Add an explicit fields = '__all__' to the "
            "{serializer_class} serializer.".format(
                serializer_class=self.__class__.__name__
            ),
        )
        return True

    @classmethod
    def get_field_names(self):
        """
        Returns the list of all field names that should be created when
        instantiating this serializer class. This is based on the default
        set of fields, but also takes into account the `Meta.fields` or
        `Meta.exclude` options if they have been specified.
        """
        self.meta_ready
        model = getattr(self.Meta, 'model')
        fields = getattr(self.Meta, 'fields', None)
        exclude = getattr(self.Meta, 'exclude', None)
        declared_fields = self._declared_fields
        if fields == ALL_FIELDS:
            fields = None

        if fields is not None:
            # Ensure that all declared fields have also been included in the
            # `Meta.fields` option.

            # Do not require any fields that are declared in a parent class,
            # in order to allow serializer subclasses to only include
            # a subset of fields.
            required_field_names = set(declared_fields)
            for cls in self.__bases__:
                required_field_names -= set(getattr(cls, '_declared_fields', []))

            for field_name in required_field_names:
                assert field_name in fields, (
                    "The field '{field_name}' was declared on serializer "
                    "{serializer_class}, but has not been included in the "
                    "'fields' option.".format(
                        field_name=field_name,
                        serializer_class=self.__name__
                    )
                )
            return fields

        # Use the default set of field names if `Meta.fields` is not specified.
        fields = self.get_all_fields_func()(model)

        if exclude is not None:
            # If `Meta.exclude` is included, then remove those fields.
            for field_name in exclude:
                assert field_name not in self._declared_fields, (
                    "Cannot both declare the field '{field_name}' and include "
                    "it in the {serializer_class} 'exclude' option. Remove the "
                    "field or, if inherited from a parent serializer, disable "
                    "with `{field_name} = None`."
                        .format(
                        field_name=field_name,
                        serializer_class=self.__class__.__name__
                    )
                )

                assert field_name in fields, (
                    "The field '{field_name}' was included on serializer "
                    "{serializer_class} in the 'exclude' option, but does "
                    "not match any model field.".format(
                        field_name=field_name,
                        serializer_class=self.__class__.__name__
                    )
                )
                fields.remove(field_name)

        return fields

    @classmethod
    def get_fields(self):
        """
        Return the dict of field names -> field instances that should be
        used for `self.fields` when instantiating the serializer.
        """
        self.meta_ready
        model = getattr(self.Meta, 'model')
        field_names = self.get_field_names()
        fields = OrderedDict()
        for field_name in field_names:
            if field_name in self._declared_fields:
                fields[field_name] = self._declared_fields[field_name]
            else:
                model_field = getattr(model, field_name)
                fields[field_name] = self.get_mapping_field_func()(model_field)
        return fields

    def check_error_fields(self):
        items = self.Meta.model.objects.all()
        fields = self.fields
        for key in fields:
            new_fields = {key: fields[key]}
            for item in items:
                try:
                    marshal(item, new_fields)
                except:
                    logger.error("error marshal key: %s id: %s" % (key, item.pk))

    @classmethod
    def get_base_fields_by_pw_field(cls, pw_field):
        import peewee as pw
        FieldsMapping = dict([(pw.AutoField, frp_fields.Integer),
                              (pw.BareField, frp_fields.String),
                              (pw.BigAutoField, frp_fields.Integer),
                              (pw.BigBitField, frp_fields.String),
                              (pw.BigIntegerField, frp_fields.Integer),
                              (pw.BinaryUUIDField, frp_fields.String),
                              (pw.BitField, frp_fields.String),
                              (pw.BlobField, frp_fields.String),
                              (pw.BooleanField, frp_fields.Boolean),
                              (pw.CharField, frp_fields.String),
                              (pw.DateField, frp_fields.Date),
                              (pw.DateTimeField, frp_fields.DateTime),
                              (pw.DecimalField, frp_fields.Decimal),
                              (pw.DoubleField, frp_fields.Decimal),
                              (pw.FixedCharField, frp_fields.String),
                              (pw.FloatField, frp_fields.Float),
                              # (pw.ForeignKeyField, frp_fields.)
                              (pw.IntegerField, frp_fields.Integer),
                              (pw.IPField, frp_fields.String),
                              # (pw.ManyToManyField, frp_fields)
                              (pw.SmallIntegerField, frp_fields.Integer),
                              (pw.TextField, frp_fields.String),
                              (pw.TimeField, frp_fields.DateTime),
                              (pw.TimestampField, frp_fields.Integer),
                              (pw.UUIDField, frp_fields.String)])
        return FieldsMapping.get(type(pw_field), frp_fields.String)

    @classmethod
    def get_base_fields_by_mge_field(cls, mongo_field):
        """
            mongo中出现了嵌套field，list可处理，dict及对象嵌套无法处理会报异常
        :param mongo_field:
        :return:
        """
        STRICT_CHECK = False
        import mongoengine as mge
        fields = []
        while isinstance(mongo_field, mge.ListField):
            fields.append(frp_fields.List)
            mongo_field = mongo_field.field or mge.StringField()
        if isinstance(mongo_field, mge.EmbeddedDocumentField):
            fields.append(frp_fields.Nested(cls.get_all_fields_model(mongo_field.document_type_obj)))
            res = fields[0]
            for f in fields[1:]:
                res = res(f)
            return res

        FieldsMapping = dict([(mge.StringField, frp_fields.String),
                              (mge.URLField, frp_fields.String),
                              (mge.EmailField, frp_fields.String),
                              (mge.IntField, frp_fields.Integer),
                              (mge.LongField, frp_fields.Integer),
                              (mge.FloatField, frp_fields.Float),
                              (mge.DecimalField, frp_fields.Float),
                              (mge.BooleanField, frp_fields.Boolean),
                              (mge.DateField, frp_fields.Date),
                              (mge.DateTimeField, cls.default_datetimefield),
                              (mge.ComplexDateTimeField, frp_fields.DateTime),
                              (mge.ObjectIdField, frp_fields.String)
                              # todo mongoengine 有一堆不容易获取的类型
                              ])
        if STRICT_CHECK and mongo_field not in FieldsMapping:
            raise Exception("复杂field对象必须自定义Field")
        fields.append(FieldsMapping.get(type(mongo_field), frp_fields.String))
        if len(fields) == 1:
            return fields[0]
        res = fields[0]
        for f in fields[1:]:
            res = res(f)
        return res
