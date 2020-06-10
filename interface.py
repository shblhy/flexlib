from werkzeug.local import LocalProxy


class ExlibInitialError(Exception):
    def __init__(self, error_info):
        self.error_info = error_info

    def __str__(self):
        return self.error_info


class ExlibInterface:
    """
        保存了exlib将要使用到的多个类
    """

    def __init__(self):
        from exlib.rest.formats import BaseTable, BaseResponse, BaseListResponse
        from exlib.casbin_mongoengine_adapter import CasbinRule
        self.table_cls = BaseTable
        self.response_cls = BaseResponse
        self.casbin_rule_cls = CasbinRule
        self.list_response_cls = BaseListResponse

    def init_app(self, app):
        app.rest_plus_config = self


def _get_current_rest_plus_config_cls():
    try:
        from utils.exlib_interface import REST_PLUS_CONFIG
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        REST_PLUS_CONFIG = ExlibInterface()
    return REST_PLUS_CONFIG


CURRENT_REST_PLUS_CONFIG = LocalProxy(lambda: _get_current_rest_plus_config_cls())
