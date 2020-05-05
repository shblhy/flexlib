from datetime import datetime, date

from flask_restplus import fields

from exlib.base.exceptions import ActionError


class CusTime(fields.MinMaxMixin, fields.Raw):
    __schema_type__ = 'string'
    __schema_format__ = 'cn-date-time'

    def __init__(self, dt_format="%Y-%m-%d %H:%M:%S", **kwargs):
        super(CusTime, self).__init__(**kwargs)
        self.dt_format = dt_format

    def format(self, value):
        value = self.parse(value)
        return datetime.strftime(value, self.dt_format)

    def parse(self, value):
        if value is None:
            return None
        elif isinstance(value, str):
            parser = lambda x: datetime.strptime(x, self.dt_format)
            try:
                return parser(value)
            except:
                raise ActionError('DateTime format must be %s' % self.dt_format)
        elif isinstance(value, datetime):
            return value
        elif isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        else:
            raise ActionError('Unsupported DateTime format')

    def _for_schema(self, name):
        value = self.parse(self._v(name))
        return self.format(value) if value else None

    def schema(self):
        schema = super(CusTime, self).schema()
        schema['default'] = self._for_schema('default')
        schema['minimum'] = self._for_schema('minimum')
        schema['maximum'] = self._for_schema('maximum')
        return schema
