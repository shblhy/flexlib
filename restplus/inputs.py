from datetime import datetime
import aniso8601


def datetime_from_cndate(value):
    '''
    Turns an ISO8601 formatted date into a datetime object.

    Example::

        inputs.datetime_from_iso8601("2012-01-01T23:30:00+02:00")

    :param str value: The ISO8601-complying string to transform
    :return: A datetime
    :rtype: datetime
    :raises ValueError: if value is an invalid date literal

    '''
    try:
        try:
            return aniso8601.parse_datetime(value, ' ')
        except ValueError:
            date = aniso8601.parse_date(value)
            return datetime(date.year, date.month, date.day)
    except Exception:
        raise ValueError('Invalid date literal "{0}"'.format(value))


datetime_from_cndate.__schema__ = {'type': 'string', 'format': 'cn-date-time'}
