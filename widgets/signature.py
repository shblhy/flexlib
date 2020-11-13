import hmac
import hashlib
from functools import wraps
from flask import request
from werkzeug.exceptions import Unauthorized
from .signature import Signature


class Signature(object):
    """
        参考腾讯云接口鉴权 https://cloud.tencent.com/document/product/214/1526
        t = time.time()
        secret_id, action = 'wechat_personal', 'send_user_feedback'
        signature = Signature.gen_signature(action, secret_id, t)
        Signature.check_right(action, secret_id, t, signature)
    """
    USERS = [('wechat_personal', b'641a841e-0f7a-11ea-bcb4-88e9fe798ebc'),
             ('spider_angel', b'641a841e-0f7a-11ea-cda5-88e9fea634fg'),
             ('account_sync', b'1f8a1a7a-94d7-11ea-97e6-f0189806dd47'),
             ('study_account_sync', b'25410564-94d7-11ea-86a5-f0189806dd47'),
             ('study_library_alert', b'25410564-94d7-11ea-86a5-f0189806dd47'),
             ('get_valuator', b'0029bddc-afaa-11ea-868f-f0189806dd47'),
             ]

    @staticmethod
    def get_key(key):
        return dict(Signature.USERS)[key]

    @staticmethod
    def gen_signature(action, secret_id, timestamp):
        identify = [
            ('action', action),
            ('secret_id', secret_id),
            ('timestamp', timestamp),
        ]
        identify_str = "&".join(["%s=%s" % (k, v) for k, v in identify])
        secret_key = Signature.get_key(secret_id)
        return hmac.new(secret_key, identify_str.encode('utf-8'), hashlib.sha1).hexdigest()

    @staticmethod
    def check_right(action, secret_id, timestamp, signature):
        cal_signature = Signature.gen_signature(action, secret_id, timestamp)
        return cal_signature == signature


def program_authentication_required(func):
    """基于以上鉴权的装饰器方法"""
    @wraps(func)
    def decorated_view(*args, **kwargs):
        identify = request.environ.get('HTTP_IDENTIFY', '')
        try:
            dic = dict([i.split('=') for i in identify.split('&')])
            if not Signature.check_right(**dic):
                raise Unauthorized(description='signature failed:' + str(dic))
        except Exception as e:
            raise Unauthorized(description='signature failed:' + str(e))
        return func(*args, **kwargs)

    return decorated_view
