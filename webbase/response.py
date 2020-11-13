import json
from flask.wrappers import Response
from flask.json import JSONEncoder
from werkzeug.exceptions import BadRequest, HTTPException


def json_dumps(data):
    return json.dumps(data, cls=JSONEncoder)


class JsonResponse(Response):
    def __init__(self, data={}, status=200):
        super(JsonResponse, self).__init__(response=json_dumps(data), content_type='application/json', status=status)


class SuccessResponse(JsonResponse):
    def __init__(self, message, data={},status=200):
        res = {'status': status, 'message': message, "data": {}}
        if data is not None:
            res['data'] = data
        super(SuccessResponse, self).__init__(res)


class SuccessCreatedResponse(JsonResponse):
    def __init__(self, message, data={}):
        res = {'status': 200, 'message': message, "data": {}}
        if data:
            res['data'] = data
        super(SuccessCreatedResponse, self).__init__(res, status=201)


class SuccessAcceptedResponse(JsonResponse):
    def __init__(self, message, data={}):
        res = {'status': 200, 'message': message, "data": {}}
        if data:
            res['data'] = data
        super(SuccessAcceptedResponse, self).__init__(res, status=202)


class FailedResponse(JsonResponse):
    def __init__(self, message, data={}, status=400):
        res = {'status': status, 'message': message, "data": {}}
        if data is not None:
            res['data'] = data
        super(FailedResponse, self).__init__(res)


class TableResponse(JsonResponse):
    DEFAULT_PAGE_SIZE = 20

    def __init__(self, data=[], page=1, total=0, page_size=20, message=''):
        if page_size < -1:
            raise BadRequest('page_size(页长)不能小于-1')
        res = {'code': 0, 'data': data, 'message': message, 'current_page': page,
               'total': total, 'total_page': int((total - 1) / page_size) + 1 if page_size != '-1' else 1}
        super(JsonResponse, self).__init__(response=json_dumps(res))


class ActionError(HTTPException):
    def __init__(self, message=''):
        super(ActionError, self).__init__(response=FailedResponse(message, status=400))

    def __str__(self):
        code = self.code if self.code is not None else "???"
        return "%s %s: %s" % (code, self.name, self.description)


class PermError(HTTPException):
    def __init__(self, message=''):
        super(PermError, self).__init__(response=FailedResponse(message, status=403))

    def __str__(self):
        code = self.code if self.code is not None else "???"
        return "%s %s: %s" % (code, self.name, self.description)
