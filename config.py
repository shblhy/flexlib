from werkzeug.local import LocalProxy


class Config:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


DEFAULT_CONFIG = Config(
    base_ignore_fields=['update_time'],
    db_engine='mongoengine'
)


class ExlibInterface:
    """
        保存了exlib将要使用到的多个类 自行继承重写
        保存exlib可能使用到的参数 config
    """

    def __init__(self):
        from .flask_restplus.formats import BaseTable, BaseResponse, BaseListResponse
        from .libs.casbin_mongoengine_adapter import CasbinRule
        from app import api_plus
        self.table_cls = BaseTable
        self.current_api = api_plus
        self.response_cls = BaseResponse
        self.casbin_rule_cls = CasbinRule
        self.list_response_cls = BaseListResponse
        self.config = DEFAULT_CONFIG

    def init_app(self, app, config=None, api=None, table=None, list_cls=None, response=None, casbin_model=None):
        """
            可传入自己使用的子类，从而改写默认行为
        :param app:
        :param api:
        :param table:
        :param response:
        :param casbin_model:
        :return:
        """
        self.config = config or self.config
        self.current_api = api or self.current_api
        self.table_cls = table or self.table_cls
        self.response_cls = response or self.response_cls
        self.casbin_rule_cls = casbin_model or self.casbin_rule_cls
        self.list_response_cls = list_cls or self.list_cls
        app.rest_plus_config = self
        self.current_app = app


def _get_current_rest_plus_config_cls():
    try:
        from utils.exlib_interface import REST_PLUS_CONFIG
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        REST_PLUS_CONFIG = ExlibInterface()
    return REST_PLUS_CONFIG


CURRENT_REST_PLUS_CONFIG = LocalProxy(lambda: _get_current_rest_plus_config_cls())
