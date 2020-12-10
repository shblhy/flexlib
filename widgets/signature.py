import hmac
import hashlib
from functools import wraps
from flask import request
from werkzeug.exceptions import Unauthorized


class Signature(object):
    """
        参考腾讯云接口鉴权 https://cloud.tencent.com/document/product/214/1526
        t = time.time()
        secret_id, action = 'wechat_personal', 'send_user_feedback'
        signature = Signature.gen_signature(action, secret_id, t)
        Signature.check_right(action, secret_id, t, signature)
    """

    @staticmethod
    def get_key(key):
        from ..config import CURRENT_REST_PLUS_CONFIG
        return dict(CURRENT_REST_PLUS_CONFIG.config.signature_group)[key]

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
