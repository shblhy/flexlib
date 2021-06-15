import hmac
import hashlib
from functools import wraps
from flask import request
from werkzeug.exceptions import Unauthorized


class Signature:
    """
        参考腾讯云接口鉴权 https://cloud.tencent.com/document/product/214/1526
        t = time.time()
        secret_id, action = 'wechat_personal', 'send_user_feedback'
        signature = Signature.gen_signature(action, secret_id, t)
        Signature.check_right(action, secret_id, t, signature)
    """
    identify_keys = ['secret_id', 'timestamp', 'action']

    @classmethod
    def get_key(cls, key):
        return dict(cls.items)[key]

    @classmethod
    def gen_signature(cls, action, secret_id, timestamp):
        identify = [
            (cls.identify_keys[2], action),
            (cls.identify_keys[0], secret_id),
            (cls.identify_keys[1], timestamp),
        ]
        identify_str = "&".join(["%s=%s" % (k, v) for k, v in identify])
        secret_key = cls.get_key(secret_id)
        return hmac.new(secret_key, identify_str.encode('utf-8'), hashlib.sha1).hexdigest()

    @classmethod
    def check_right(cls, action, secret_id, timestamp, signature):
        cal_signature = cls.gen_signature(action, secret_id, timestamp)
        return cal_signature == signature

    @classmethod
    def get_program_authentication_required(signature_cls):
        def program_authentication_required(func):
            """基于以上鉴权的装饰器方法"""

            @wraps(func)
            def decorated_view(*args, **kwargs):
                identify = request.environ.get('HTTP_IDENTIFY', '')
                try:
                    dic = dict([i.split('=') for i in identify.split('&')])
                    if not signature_cls.check_right(**dic):
                        raise Unauthorized(description='signature failed:' + str(dic))
                except Exception as e:
                    raise Unauthorized(description='signature failed:' + str(e))
                return func(*args, **kwargs)

            return decorated_view
        return program_authentication_required

    @classmethod
    def get_signature_required(signature_cls):
        def signature_required(*params):
            def wrapper(func):
                project, action = params

                @wraps(func)
                def decorated_view(*args, **kwargs):
                    identify = request.environ.get('HTTP_IDENTIFY', '')
                    try:
                        dic = dict([i.split('=') for i in identify.split('&')])
                        if project != dic.get('secret_id'):
                            raise Unauthorized(description='project error:' + str(dic))
                        if action != dic.get('action'):
                            raise Unauthorized(description='action error:' + str(dic))
                        if not signature_cls.check_right(**dic):
                            raise Unauthorized(description='signature failed:' + str(dic))
                    except Exception as e:
                        raise Unauthorized(description='signature failed:' + str(e))
                    return func(*args, **kwargs)

                return decorated_view

            return wrapper

        return signature_required


program_authentication_required = Signature.get_program_authentication_required()
signature_required = Signature.get_signature_required()
