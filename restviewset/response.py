import json
from flask.wrappers import Response
from utils.json_encoder import JsonExtendEncoder
from werkzeug.exceptions import BadRequest, HTTPException


def json_dumps(data):
    return json.dumps(data, cls=JsonExtendEncoder)


class JsonResponse(Response):
    default_mimetype = 'application/json'

    def __init__(self, data={}, status=200):
        super(JsonResponse, self).__init__(response=json_dumps(data), content_type='application/json', status=status)


# class SuccessResponse(JsonResponse):
#     def __init__(self, message, data={}):
#         res = {'code': 0, 'message': message}
#         if data is not None:
#             res['data'] = data
#         super(SuccessResponse, self).__init__(res)


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


# class ProjectError(BadRequest):
class ProjectError(HTTPException):
    def __init__(self, right_pro_id=None, err_pro_id=None, message='项目错误'):
        messages = [message]
        if right_pro_id:
            messages.append('当前项目是%s号' % right_pro_id)
        if err_pro_id:
            messages.append('却尝试在%s号项目上操作' % err_pro_id)
        res = {'code': 4031, 'message': ','.join(messages)}
        # super(BadRequest, self).__init__(res)
        super(ProjectError, self).__init__(
            response=Response(response=json_dumps(res), status=403, content_type='application/json'))


class ActionError(HTTPException):
    def __init__(self, message=''):
        super(ActionError, self).__init__(response=FailedResponse(message, status=400))

    def __str__(self):
        return


class PermError(HTTPException):
    def __init__(self, message=''):
        super(PermError, self).__init__(response=FailedResponse(message, status=403))

    def __str__(self):
        return


class TableResponse(JsonResponse):
    DEFAULT_PAGE_SIZE = 20

    def __init__(self, data=[], page=1, total=0, page_size=20, message=''):
        if page_size < -1:
            raise BadRequest('page_size(页长)不能小于-1')
        res = {'code': 0, 'data': data, 'message': message, 'current_page': page,
               'total': total, 'total_page': int((total - 1) / page_size) + 1 if page_size != '-1' else 1}
        super(JsonResponse, self).__init__(response=json_dumps(res))
