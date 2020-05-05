"""
    mongoengine bug集:
    1、db_field与field重名处理：不使用这种情景
    2、db_field与EmbeddedDocument同时使用无法使用__魔术机制处理：__raw__:{}

"""
