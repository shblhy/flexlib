from flask import request
from werkzeug.exceptions import abort

def get_real_ip():
    ip = request.headers.get("x-forwarded-for")
    if ip is None or len(ip) == 0 or "unknown" == ip:
        ip = request.headers.get("Proxy-Client-IP")
    if ip is None or len(ip) == 0 or "unknown" == ip:
        ip = request.headers.get("WL-Proxy-Client-IP")
    if ip is None or len(ip) == 0 or "unknown" == ip:
        ip = request.remote_addr
    return ip


MODEL_HANDLERS = []


try:
    from mongoengine import Document as MongoDocument
    MODEL_HANDLERS.append((MongoDocument, lambda x, y: x.objects.get(**y)))
except Exception as e:
    pass
try:
    from elasticsearch_dsl import Document as EsDocument
    MODEL_HANDLERS.append((EsDocument, lambda x, y: x.get(**y)))
except Exception as e:
    pass


def get_object_or_404(model, **kwargs):
    """
        目前支持mongoengine.Document,elasticsearch_dsl.Document
        todo 支持peewee
    :param model:
    :param kwargs:
    :return:
    """
    try:
        for cls, handler in MODEL_HANDLERS:
            if issubclass(model, cls):
                return handler(model, kwargs)
    except Exception as e:
        clist = ['%s=%s' % (item[0], item[1]) for item in kwargs.items()]
        errmsg = 'can not find %s - %s' % (model.__name__, ';'.join(clist))
        abort(404, errmsg)
