import hmac
import hashlib
from collections import OrderedDict


class Signature(object):
    """
        参考腾讯云接口鉴权 https://cloud.tencent.com/document/product/214/1526
        t = time.time()
        secret_id, action = 'wechat_personal', 'send_user_feedback'
        signature = Signature.gen_signature(action, secret_id, t)
        Signature.check_right(action, secret_id, t, signature)
    """
    USERS = [('wechat_personal', b'641a841e-0f7a-11ea-bcb4-88e9fe798ebc'),
             ('spider_angel', b'641a841e-0f7a-11ea-cda5-88e9fea634fg')]

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
