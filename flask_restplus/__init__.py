"""
serializer
    增加大功能Serializer，实质是将marshal扩展为类，理由是：类方便于继承重写，比字典容易管理。可参考django_rest_framework的Serializer
resource
    增加ListResource/SingleResource/ActionResource，理由是：提供默认响应消息；提供查询、分页、排序的封装。
formats/decorators
    提供formats来描述响应格式，提供marshal_table/marshal_item方法按对应格式返回内容。理由是实际开发中，一个项目内甚至一个公司内往往只有一套前后端交互方法。无需重复编写。
fields
    CusTime支持自定义时间格式

结合model层，组合提供更强大功能：
    flask_restplus事实上是一个功能更为深入的web开发框架（较之flask），对于网站框架来说，model层数据处理必不可少。
    Flexlib尽量增加一些常用功能，但不想改变flask_restplus的"轻量级"特性。
    故在方法层级引用peewee mongoengine 等常用数据库层框架，避免造成依赖
"""
