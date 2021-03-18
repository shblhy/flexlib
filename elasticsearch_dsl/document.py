import json
import datetime
import importlib
from copy import deepcopy
from elasticsearch_dsl import Document as Document_, Date, Boolean, Keyword
from elasticsearch_dsl.search import Search
from exlib.flask_restplus.serializers import ModelSerializer


class Document(Document_):
    meta_config = None

    # eg. meta_config = {'index': get_es_index("deal"), 'client': es, 'mongo_cls': Deal}
    # es的index 应该配置一个字符串，但往往使用方法来提供而非写死，原因是es数据库量少（贵），多个环境会使用相同的index
    def save(self, validate=False, **kwargs):
        return super(Document, self).save(validate=validate, **kwargs, using=self.meta_config["client"])

    @classmethod
    def init(cls, **kwargs):
        return super(Document, cls).init(using=cls.meta_config["client"], index=cls.meta_config["index"])

    @classmethod
    def transfer(cls, obj, serializer_cls=None):
        if not isinstance(obj, cls.meta_config['mongo_cls']):
            raise Exception('can not parse %s' % (obj,))
        if serializer_cls is None:
            class Serializer(ModelSerializer):
                class Meta:
                    model = obj.__class__
                    fields = "__all__"

            serializer_cls = Serializer
        fields = cls.get_fields()
        meta_data = {item: None for item in obj.__class__._fields.keys()}
        meta_data.update(serializer_cls(obj, _many_=False).data)
        data = {"_id": str(meta_data.get("id"))}
        data.update({key: meta_data.get(key) for key in meta_data if key in fields})
        return cls(**data)

    @classmethod
    def search(cls, extra={}):
        return Search(
            using=cls.meta_config["client"],
            index=cls.meta_config["index"],
            doc_type=[cls],
            extra=extra
        )

    @classmethod
    def get_sorted_mongo_objs(cls, ids):
        """按id顺序获取mongo对象"""
        mongo_cls = cls.meta_config['mongo_cls']
        objs = mongo_cls.objects(id__in=ids)
        res = {str(o.id): o for o in objs}
        return [res[str(i)] for i in ids if str(i) in res]

    @classmethod
    def get(cls, id, **kwargs):
        return Document_.get(id, using=cls.meta_config["client"], index=cls.meta_config["index"])

    @classmethod
    def mget(cls, docs, **kwargs):
        return Document_.mget(docs, using=cls.meta_config["client"], index=cls.meta_config["index"])

    def delete(self, **kwargs):
        return Document_.delete(self, using=self.meta_config["client"], index=self.meta_config["index"])

    def update(self, **kwargs):
        return Document_.update(self, using=self.meta_config["client"], index=self.meta_config["index"])

    @classmethod
    def get_fields(cls):
        return {i[0]: i for i in cls._ObjectBase__list_fields()}

    @classmethod
    def get_copy_to_fields(cls):
        return [k for (k, f, b) in cls.get_fields().values() if hasattr(f, 'copy_to') and f.copy_to == 'full_search_by']


class ESMixin:
    es_model = ''   # 'app.deal2.models.deal_es.DealES'
    es_serializer = ''  # 'app.deal2.serializers.deal.DealEsParseSerializer'

    @classmethod
    def get_es_model(cls):
        path = cls.es_model
        if not path:
            raise Exception("usset es_model")
        path_list = path.split('.')
        cls_path = '.'.join(path_list[:-1])
        cls_name = path_list[-1:][0]
        mod = importlib.import_module(cls_path)
        return getattr(mod, cls_name)

    @classmethod
    def get_es_serializer(cls):
        path = cls.es_serializer
        if not path:
            return None
        path_list = path.split('.')
        cls_path = '.'.join(path_list[:-1])
        cls_name = path_list[-1:][0]
        mod = importlib.import_module(cls_path)
        return getattr(mod, cls_name)

    @classmethod
    def gen_highlight_data(cls, objs, highlight_dict, serializer=None):
        def _replace_sign_data(data_json_, signs):
            data_json = deepcopy(data_json_)
            def _replace(item, sign):
                if isinstance(item, dict):
                    for k, v in item.items():
                        if type(v) is list:
                            item[k] = _replace(v, sign)
                        elif type(v) is list:
                            for _index, i in v:
                                v[_index] = _replace(i, sign)
                        elif type(item) is str:
                            item[k] = v.replace(sign, '<em>' + sign + '</em>')
                    return item
                elif type(item) is list:
                    for _index, i in enumerate(item):
                        item[_index] = _replace(i, sign)
                    return item
                elif type(item) is str:
                    return item.replace(sign, '<em>' + sign + '</em>')
                else:
                    return item
            for sign in signs:
                data_json = _replace(data_json, sign)
            if data_json_ == data_json:
                return None
            return data_json

        for obj in objs:
            if serializer is None:
                obj_data = obj.to_mongo().to_dict()
            else:
                obj_data = serializer(obj).data
            search_all_key = '_all_' in highlight_dict
            highlight_keys = list(set(obj_data.keys())) if search_all_key else \
                list(set(obj_data.keys()) & set(highlight_dict.keys()))
            highlight_item = {}
            for key in highlight_keys:
                data = obj_data[key]
                if search_all_key:
                    v = _replace_sign_data(data, highlight_dict.get(key, []) + highlight_dict.get('_all_', []))
                else:
                    v = _replace_sign_data(data, highlight_dict[key])
                if v:
                    highlight_item[key] = v
            obj.highlight = highlight_item
        return objs

    def sync_es_save(self, **kwargs):
        es_model = self.get_es_model()
        es_serializer = self.get_es_serializer()
        es = es_model.transfer(self, es_serializer)
        es.save()
