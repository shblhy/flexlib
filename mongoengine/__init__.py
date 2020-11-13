"""
##### DocumentMixin:提供了Document对象使用的一些常用方法

     create_with   以字典直接创建对象（支持嵌套）
     update_with   以字典直接更新对象（支持嵌套）
     db_dict    获取数据库字典
     to_dict    转为字典

推荐用法：
    自定义Document，在引用mongoengine前加一层封装，在这个层次加入自己需要的业务公共属性，并继承DocumentMixin


##### HistoryMixin:为Document提供保存历史记录功能

##### SearchMixin:为Document提供保存历史记录功能

##### ConditionValidatorMixin:为Document提供条件校验功能


附录：
    mongoengine 若干已知bug:
    1、db_field与field重名处理：不使用这种情景
    2、db_field与EmbeddedDocument同时使用无法使用__魔术机制处理：__raw__:{}

"""
