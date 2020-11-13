from flask_restplus.reqparse import RequestParser as OriRequestParser, Argument as OriArgument, abort, HTTPStatus
import copy
from werkzeug import exceptions
from flask import current_app, request
import six
import re
from functools import reduce

_friendly_location = {
    'json': 'the JSON body',
    'form': 'the post body',
    'args': 'the query string',
    'values': 'the post body or the query string',
    'headers': 'the HTTP headers',
    'cookies': 'the request\'s cookies',
    'files': 'an uploaded file',
}

#: Maps Flask-RESTPlus RequestParser locations to Swagger ones
LOCATIONS = {
    'args': 'query',
    'form': 'formData',
    'headers': 'header',
    'json': 'body',
    'values': 'query',
    'files': 'formData',
}

SPLIT_CHAR = ','
DEFAULT_ENGINE = 'mongo'
DEFAULT_OPER = {
    "peewee": '__eq__',
    "sqlarchemy": "",
    "mongo": '',
}
OPER_LIST_D = {
    "peewee": ['__eq__', '__ge__', '__gt__', '__le__', '__lt__', '__ne__', '__neg__',
               '__new__', 'between', 'cast', 'contains', 'like', 'endswith', 'in_', 'not_in', 'startswith'],
    "mongo": ['', 'contains', 'gt', 'lt', 'gte', 'lte', 'between', 'like', 'in', 'startswith', 'endswith']
}


class Empty(object):
    pass


class Argument(OriArgument):
    engine = DEFAULT_ENGINE

    def __init__(self, *args, **kwargs):
        self.regex = kwargs.pop('regex', None)
        self.oper = kwargs.pop('oper', DEFAULT_OPER[DEFAULT_ENGINE])
        if kwargs.get('action') == 'split':
            self.oper = 'in_'
        assert self.oper in OPER_LIST_D[DEFAULT_ENGINE], \
            '只能使用限定的操作符'

        super(Argument, self).__init__(*args, **kwargs)

    def get_dest(self):
        return self.dest or self.name

    def convert(self, value, op):
        if value in ['null'] and self.nullable:
            return None
        if value in ['false', 'False'] and self.type is bool:
            return False
        if value in ['true', 'True'] and self.type is bool:
            return True
        return super(Argument, self).convert(value, op)

    def parse(self, request, bundle_errors=False):
        bundle_errors = current_app.config.get('BUNDLE_ERRORS', False) or bundle_errors
        source = self.source(request)

        results = []

        # Sentinels
        _not_found = False
        _found = True

        for operator in self.operators:
            name = self.name + operator.replace('=', '', 1)
            if name in source:
                # Account for MultiDict and regular dict
                if hasattr(source, 'getlist'):
                    values = source.getlist(name)
                else:
                    values = [source.get(name)]

                for value in values:
                    if hasattr(value, 'strip') and self.trim:
                        value = value.strip()
                    if hasattr(value, 'lower') and not self.case_sensitive:
                        value = value.lower()

                        if hasattr(self.choices, '__iter__'):
                            self.choices = [choice.lower() for choice in self.choices]

                    try:
                        if self.action == 'split':
                            value = [self.convert(v, operator) for v in value.split(SPLIT_CHAR)]
                        else:
                            value = self.convert(value, operator)
                    except Exception as error:
                        if self.ignore:
                            continue
                        return self.handle_validation_error(error, bundle_errors)

                    if self.choices and value not in self.choices:
                        msg = 'The value \'{0}\' is not a valid choice for \'{1}\'.'.format(value, name)
                        return self.handle_validation_error(msg, bundle_errors)

                    if name in request.unparsed_arguments:
                        request.unparsed_arguments.pop(name)
                    results.append(value)

        if not results and self.required:
            if isinstance(self.location, six.string_types):
                location = _friendly_location.get(self.location, self.location)
            else:
                locations = [_friendly_location.get(loc, loc) for loc in self.location]
                location = ' or '.join(locations)
            error_msg = 'Missing required parameter in {0}'.format(location)
            return self.handle_validation_error(error_msg, bundle_errors)

        if not results:
            if callable(self.default):
                return self.default(), _not_found
            else:
                return self.default, _not_found

        if self.action == 'append':
            if self.regex:
                for result in results:
                    if not re.match(self.regex, result):
                        self.handle_validation_error('格式校验失败', bundle_errors)
            return results, _found

        if self.action == 'store' or len(results) == 1:
            if self.regex:
                if not re.match(self.regex, results[0]):
                    self.handle_validation_error('格式校验失败', bundle_errors)
            return results[0], _found
        return results, _found

    def handle_validation_error(self, error, bundle_errors):
        '''
        Called when an error is raised while parsing. Aborts the request
        with a 400 status and an error message

        :param error: the error that was raised
        :param bool bundle_errors: do not abort when first error occurs, return a
            dict with the name of the argument and the error message to be
            bundled
        '''
        error_str = six.text_type(error)
        error_msg = ' '.join([six.text_type(self.help), error_str]) if self.help else error_str
        errors = {self.name: error_msg}

        kname = self.help if self.help else self.name
        if bundle_errors:
            return ValueError(error), errors
        abort(HTTPStatus.BAD_REQUEST, '[%s]校验失败' % kname, errors=errors)


class RequestParser(OriRequestParser):
    def __init__(self, *args, **kwargs):
        kwargs['argument_class'] = Argument
        self.args_dict = {}
        self.or_args = {}
        super(RequestParser, self).__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], self.argument_class):
            self.args.append(args[0])
            self.args_dict[args[0].get_dest()] = args[0]
        else:
            arg = self.argument_class(*args, **kwargs)
            self.args.append(arg)
            self.args_dict[arg.get_dest()] = arg
        if self.trim and self.argument_class is Argument:
            self.args[-1].trim = kwargs.get('trim', self.trim)
        return self

    def set_or_argument(self, index, attrs):
        index = '__or__'.join(attrs)
        self.or_args[index] = attrs
        arg = copy.deepcopy(self.args_dict[attrs[0]])
        arg.name = index
        arg.help = '|'.join([self.args_dict[a].help for a in attrs if self.args_dict[a].help])
        self.args.append(arg)
        self.args_dict[index] = arg
        # filter.add_argument(index, type=str, oper='contains', store_missing=False, help='输入中文名或者英文名均可')

    def get_pw_conditions(self, model_class, args=None):
        """
            获取参数并转化为peewee的查询条件
            todo@hy conditions当有顺序，以符合索引提升查询效率。
        :param args:
        :return:
        """
        if args is None:
            args = self.parse_args()
        conditions = []
        for k, v in args.items():
            oper = self.args_dict.get(k, Argument(k)).oper
            if k in self.or_args:
                clsattrs = [getattr(model_class, attr) for attr in self.or_args[k]]
                or_items = [getattr(clsattr, oper)(v) for clsattr in clsattrs]
                condition = reduce(lambda x, y: x | y, or_items)
                conditions.append(condition)
            else:
                clsattr = getattr(model_class, k)
                f = getattr(clsattr, oper)
                conditions.append(f(v))
        return conditions
        # return [getattr(getattr(model_class, k), self.args_dict.get(k, Argument(k)).oper)(v) for k, v in args.items()]

    def get_sa_conditions(self, model_class, args=None):
        """
            获取参数并转化为sqlarchemy的查询条件
            todo@hy conditions当有顺序，以符合索引提升查询效率。
        :param args:
        :return:
        """
        model_class_c = getattr(model_class, 'c')
        if args is None:
            args = self.parse_args()
        conditions = []
        for k, v in args.items():
            oper = self.args_dict.get(k, Argument(k)).oper
            if k in self.or_args:
                clsattrs = [getattr(model_class_c, attr) for attr in self.or_args[k]]
                or_items = [getattr(clsattr, oper)(v) for clsattr in clsattrs]
                condition = reduce(lambda x, y: x | y, or_items)
                conditions.append(condition)
            else:
                if oper == 'like':
                    v = '%' + str(v) + '%'
                clsattr = getattr(model_class_c, k)
                f = getattr(clsattr, oper)
                conditions.append(f(v))
        return conditions

    def get_mge_conditions(self, model_class, args=None):
        if args is None:
            args = self.parse_args()
        conditions = {}  # []
        for k, v in args.items():
            oper = self.args_dict.get(k, Argument(k)).oper
            if k in self.or_args:
                clsattrs = [getattr(model_class, attr) for attr in self.or_args[k]]
                or_items = [getattr(clsattr, oper)(v) for clsattr in clsattrs]
                condition = reduce(lambda x, y: x | y, or_items)
                conditions.append(condition)
            else:
                clsattr = getattr(model_class, k)
                if oper:
                    conditions['%s__%s' % (k, oper)] = v
                else:
                    conditions[k] = v
        return conditions

    def set_model_class(self, model_class):
        self.model_class = model_class
        for k, v in self.args_dict.items():
            if not v.help:
                field = getattr(model_class, k)
                v.help = getattr(field, 'verbose_name', None) or getattr(field, 'help_text', None)

    def parse_args(self, req=None, strict=False):
        '''
        Parse all arguments from the provided request and return the results as a ParseResult

        :param bool strict: if req includes args not in parser, throw 400 BadRequest exception
        :return: the parsed results as :class:`ParseResult` (or any class defined as :attr:`result_class`)
        :rtype: ParseResult
        '''
        if req is None:
            req = request

        result = self.result_class()

        # A record of arguments not yet parsed; as each is found
        # among self.args, it will be popped out
        req.unparsed_arguments = dict(self.argument_class('').source(req)) if strict else {}
        errors = {}
        for arg in self.args:
            value, found = arg.parse(req, self.bundle_errors)
            if isinstance(value, ValueError):
                errors.update(found)
                found = None
            if found or arg.store_missing:
                result[arg.dest or arg.name] = value
        if errors:
            err_msgs = []
            for k, v in errors.items():
                _arg = self.args_dict.get(k)
                kname = _arg.help if _arg.help else k
                err_msgs.append("输入框[%s]校验失败" % (kname,))
            message = ','.join(err_msgs)
            abort(HTTPStatus.BAD_REQUEST, message, errors=errors)

        if strict and req.unparsed_arguments:
            arguments = ', '.join(req.unparsed_arguments.keys())
            msg = 'Unknown arguments: {0}'.format(arguments)
            raise exceptions.BadRequest(msg)

        return result


class DocumentRequestParser(RequestParser):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        model_class = kwargs.pop('model_class', None)
        location = kwargs.pop('location', None)
        store_missing = kwargs.pop('store_missing', None)
        super(DocumentRequestParser, self).__init__(*args, **kwargs)
        if fields is None:
            fields = [k for k in model_class._fields]
        for field in fields:
            v = model_class._fields[field]
            t = DocumentRequestParser.get_front_type(type(v))
            params = {
                'name': field,
                'type': t,
                'store_missing': False
            }
            if location is not None:
                params['location'] = location
            elif t in (list, dict):
                params['location'] = 'json'
            if store_missing is not None:
                params['store_missing'] = store_missing
            # if hasattr(v, 'choices'):
            #     if v.choices and isinstance(v.choices[0], (list, tuple)):
            #         params['choices'] = [c[0] for c in v.choices]
            #     else:
            #         params['choices'] = v.choices
            self.add_argument(**params)

    @staticmethod
    def get_front_type(field_type):
        import mongoengine as mge
        FieldsMapping = dict([(mge.StringField, str),
                              (mge.URLField, str),
                              (mge.EmailField, str),
                              (mge.IntField, int),
                              (mge.LongField, float),
                              (mge.FloatField, float),
                              (mge.DecimalField, float),
                              (mge.BooleanField, bool),
                              (mge.ReferenceField, str),
                              (mge.DateField, str),
                              (mge.DateTimeField, str),
                              (mge.ComplexDateTimeField, str),
                              (mge.ObjectIdField, str),
                              (mge.ListField, list),
                              (mge.DictField, dict),
                              (mge.EmbeddedDocumentField, dict)]
                             )
        return FieldsMapping.get(field_type, str)
