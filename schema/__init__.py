"""
    Schema模块用于格式校验相关功能支持。如：提供给前端后端的字段格式；按条件校验数据；检查历史数据正确性等。
    SchemaMixin 提供给mongo document继承，能动态生产各条件下的校验类。
    SchemaField 提供校验规则支撑，支持document的validate校验和自订逻辑校验。
"""


from .field import SchemaException, ErrDetailItem, SchemaField, SchemaMetaclass, get_schema, get_schema_by_model, \
    register_all_schemas
from .document import SchemaMixin