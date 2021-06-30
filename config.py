# from werkzeug.local import LocalProxy
# from flask_restplus import fields as frp_fields
#
#
# class Config:
#     def __init__(self, **kwargs):
#         for k, v in kwargs.items():
#             setattr(self, k, v)
#
#
# DEFAULT_CONFIG = Config(
#     base_ignore_fields=['update_time'],
#     db_engine='mongo',
#     timezone='BEIJING'# todo@hy 时区用这个标记表达并不合理
#     # signature_group
# )
#
#
# class ExlibInterface:
#     """
#         保存了exlib将要使用到的多个类 自行继承重写
#         保存exlib可能使用到的参数 config
#     """
#
#     def __init__(self):
#         from flask_restplus import Api
#         from .flask_restplus.formats import BaseTable, BaseResponse, BaseListResponse
#         from .libs.casbin_mongoengine_adapter import CasbinRule
#         self.table_cls = BaseTable
#         self.current_api = Api()
#         self.response_cls = BaseResponse
#         self.casbin_rule_cls = CasbinRule
#         self.list_response_cls = BaseListResponse
#         self.config = DEFAULT_CONFIG
#         self.error_fields = self.current_api.model('error_400', {
#             'code': frp_fields.Integer,
#             'message': frp_fields.String
#         })
#
#     def init_app(self, app, config=None, api=None, table=None, list_cls=None, response=None, casbin_model=None,
#                  error_fields=None):
#         """
#             可传入自己使用的子类，从而改写默认行为
#         :param app:
#         :param api:
#         :param table:
#         :param response:
#         :param casbin_model:
#         :return:
#         """
#         self.config = config or self.config
#         self.current_api = api or self.current_api
#         self.table_cls = table or self.table_cls
#         self.response_cls = response or self.response_cls
#         self.casbin_rule_cls = casbin_model or self.casbin_rule_cls
#         self.list_response_cls = list_cls or self.list_cls
#         self.error_fields = api.model('error_400', {
#             'code': frp_fields.Integer,
#             'message': frp_fields.String
#         })
#         app.rest_plus_config = self
#         self.current_app = app
#
#     @staticmethod
#     def init(app, config=None, api=None, table=None, list_cls=None, response=None, casbin_model=None, error_fields=None):
#         """
#             可传入自己使用的子类，从而改写默认行为  # todo@hy 重复写了次 和原意不符 是为了解决循环引用问题
#         :param app:
#         :param api:
#         :param table:
#         :param response:
#         :param casbin_model:
#         :return:
#         """
#         self = CURRENT_REST_PLUS_CONFIG
#         self.config = config or self.config
#         self.current_api = api or self.current_api
#         self.table_cls = table or self.table_cls
#         self.response_cls = response or self.response_cls
#         self.casbin_rule_cls = casbin_model or self.casbin_rule_cls
#         self.list_response_cls = list_cls or self.list_cls
#         self.error_fields = error_fields or api.model('error_400', {
#             'code': frp_fields.Integer,
#             'message': frp_fields.String
#         })
#         app.rest_plus_config = self
#         self.current_app = app
#
#
# CURRENT_REST_PLUS_CONFIG = ExlibInterface()
