import jieba
import logging
from mongoengine import StringField, ListField, EmbeddedDocumentField
logger = logging.getLogger(__name__)


class SearchMixin:
    search_tags = StringField(verbose_name='全文搜索字段')
    search_fields = None

    def get_search_tags(self, fields=None):
        """
            将目标字符串都用结巴分词处理一遍，以便搜索
            如果目标是对象，则将目标下层的所有字符串及list(str)类型这样处理
        :param fields:
            Ex:['name', 'get_from', 'contact_info.phone', 'contact_info.phone_history', 'experience']

            # __all_str__  表示将所有字符串（含深度两级内的复杂对象,默认级中的字符串）都放进search_tags中,
        :return:
        """
        tags = []

        def _jieba_add_tags(val, field):
            if not val:
                return
            if type(field) is StringField:
                tags.extend(list(jieba.cut_for_search(val)))
                if val not in tags:
                    tags.append(val)
            if type(field) is ListField and field.field == StringField:
                for i in val:
                    if i:
                        tags.extend(list(jieba.cut_for_search(i)))
                        if val not in tags:
                            tags.append(val)

        def is_str_list_field(field):
            return type(field) is StringField or type(field) is ListField and field.field == StringField

        def _handle_attr(obj, attr_str):
            try:
                if not obj:
                    return
                if '.' not in attr_str:
                    field = obj._fields[attr_str]
                    value = getattr(obj, attr_str)
                    if not value:
                        return
                    if is_str_list_field(field):
                        _jieba_add_tags(value, field)
                    elif type(field) is ListField:
                        if type(field.field) is EmbeddedDocumentField:
                            new_fields = [key for key, field in field.field.document_type._fields.items() if
                                          is_str_list_field(field)]
                            for new_value in value:
                                for new_field in new_fields:
                                    _handle_attr(new_value, new_field)
                    else:
                        for key, new_field in value._fields.items():
                            new_value = getattr(value, key)
                            if new_value and is_str_list_field(new_field):
                                _jieba_add_tags(new_value, new_field)
                else:
                    attrs = attr_str.split('.', 1)
                    attr = attrs[0]
                    field = obj._fields[attr]
                    if is_str_list_field(field):
                        raise Exception('search field %s - %s 设置有误' % (obj, attr_str))
                    new_obj = getattr(obj, attr)
                    if not new_obj:
                        return
                    attr_left = attrs[1] if len(attrs) == 2 else None
                    if not attr_left:
                        new_fields = [key for key, field in new_obj._fields.items() if is_str_list_field(field)]
                    else:
                        new_fields = [attr_left]
                    for new_attr in new_fields:
                        _handle_attr(new_obj, new_attr)
            except Exception as e:
                if type(self).__name__ == 'Candidate':
                    pass
                    # todo@hy Candidate暂时不抛异常，不写日志，不影响程序执行 修理数据后再改进
                else:
                    logger.error('reset_search_tags error: %s - %s' % (str(obj), attr_str))

        if fields is None:
            fields = [key for key, field in self._fields.items() if is_str_list_field(field) and key != 'search_tags']
        for attr_str in fields:
            _handle_attr(self, attr_str)
        return tags

    def reset_search_tags(self):
        tags = self.get_search_tags(self.search_fields)
        self.search_tags = ' '.join(tags)
