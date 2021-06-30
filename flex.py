"""
    Flex对象用于保存项目启动必要信息。
    它确保在程序需要时，必定可以获得需要的类对象。
"""

from werkzeug.local import LocalProxy, LocalStack
from .webbase import Item
current_apis = LocalProxy(lambda: _get_apis())
current_api = LocalProxy(lambda: _get_api())
current_dbs = LocalProxy(lambda: _get_dbs())
current_logs = LocalProxy(lambda: _get_logs())
current_caches = LocalProxy(lambda: _get_caches())
get_mdb = LocalProxy(lambda x: _get_mdb(x))
get_log = LocalProxy(lambda x: _get_log(x))
get_redis = LocalProxy(lambda x: _get_redis(x))

# —————————--------LocalStack 实现_flex———————————
# _flex = LocalStack()
#
#
# def init_flex(**kwargs):
#     if not _flex.top:
#         _flex.push(Item(**kwargs))
#     else:
#         _flex.top.update(kwargs)
#     if 'app' in kwargs and not hasattr(kwargs['app'], 'flex'):
#         kwargs['app'].flex = _flex
#
#
# def _get_flex():
#     if not _flex.top:
#         init_flex()
#     return _flex.top
# current_flex = LocalProxy(lambda: _get_flex())
# ------------------------------------------------


# —————————--------单例模式 实现_flex———————————————
class Flex(Item):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = Item.__new__(cls)
        return cls._instance

    def init_app(self, app=None, **kwargs):
        self.app = app
        app.flex = self
        self.update(kwargs)


_flex = Flex()
current_flex = _flex
# ------------------------------------------------


def _get_dbs():
    return current_flex.dbs


def _get_mdb(key):
    return _get_dbs()['mongo'][key]


def _get_logs():
    return current_flex['logs']


def _get_log(key):
    return _get_logs()[key]


def _get_caches():
    return current_flex['caches']


def _get_redis(key):
    if key in _get_caches()['redis']:
        return _get_caches()['redis'][key]
    else:
        return _get_caches()['redis']['default']


def _get_apis():
    return current_flex['apis']


def _get_api():
    return _get_apis()['api']


def get_document(key):
    """
        使用get_document时注意：documents在create_app最后写入，此后可以使用本方法获取类，但早于此情境的不能。
        通常如 User CasbinRule 表，在create_appp过程中即需要，那个时间还无法执行此方法。
    """
    from mongoengine.base import get_document as get_document_
    return get_document_(current_flex.documents[key])
