import time
import datetime
import json
from bson import ObjectId
from mongoengine import StringField, DynamicField
from mongoengine.base.common import get_document
from utils.json_encoder import JsonExtendEncoder
from .compare_diff import get_diff, get_attr

"""
    历史记录的解决方案：
    1、增加一个History表，保存记录的历史。
    2、每次修改，一条记录作两份存档，分别进入原表和history表
    3、但以上操作无法处理类定义修改的情况，一旦类定义发生修改，会导致难以解析历史数据
    4、增加一个ClsHistory表，保存类的历史定义
"""


class HistoryMixin:
    """
        保存历史 使用注意：必须用默认id 主键
    """

    @classmethod
    def get_history_document(cls):
        cls_name = cls.__module__ + '.' + cls.__name__ + 'History'
        return get_document(cls_name)

    def save_with_history(self, desc=None, version=None, **kwargs):
        """
            每次更改存两份，一份在当前位置，一份在历史表。
            鉴于历史表不存在老数据，上个版本也存一份（不重复存）。
        :param desc: 当前版本描述
        :param kwargs:
        :return:
        """
        pk = self.pk
        history_cls = self.get_history_document()
        content = type(self).objects.get(pk=pk)
        if self.db_dict == content.db_dict:
            return self
        res = self.save(**kwargs)
        snapshot = history_cls(
            content=self.db_dict,
            desc=desc
        )
        if version:
            snapshot.version = version
        snapshot.save()
        return res

    def _save_(self, desc=None, version=None, force=False, **kwargs):
        """
                    每次更改存两份，一份在当前位置，一份在历史表。
                :param desc: 当前版本描述
                :param kwargs:
                :return:
                """
        cls = type(self)
        pk = self.pk
        history_cls = self.get_history_document()
        content = cls.objects(pk=pk).first() if pk else None
        if content and not force and self.db_dict == content.db_dict:
            return self
        self.update_time = datetime.datetime.utcnow()
        res = super(cls, self).save(**kwargs)
        snapshot = history_cls(
            content=self.db_dict,
            desc=desc
        )
        if version:
            snapshot.version = version
        snapshot.save()
        return res

    def snapshot(self):
        history_cls = self.get_history_document()
        db_last_version = history_cls.objects(__raw__={"content._id": self.id}).order_by('-create_time').first()
        if not db_last_version or db_last_version.content != self.db_dict:
            db_last_version = history_cls(
                content=self.db_dict
            ).save()
        return db_last_version.id

    @property
    def _version_(self):
        """
            用于标记一份数据的版本，以方便快照处理。
            寻找历史最新版本数据，与当前版本比较，如果内容相同，则返还该版本号
        """
        cls = type(self)
        history_cls = self.get_history_document()
        db_last_version = history_cls.objects(__raw__={"content._id": self.id}).order_by('-create_time').first()
        if db_last_version and db_last_version.content == cls.objects.get(pk=self.pk).db_dict:
            return db_last_version.version

    def diff(self, record):
        return get_diff(record.content, self.to_mongo().to_dict())


class History:
    _model_desc_ = 'auto history'
    document_type = None
    desc = StringField(version_name="描述")
    content = DynamicField(db_field='content', verbose_name="历史数据快照")
    version = StringField(version_name="版本号", default=lambda: str(int(time.time() * 10 ** 6)))

    @classmethod
    def snapshot(cls, content, desc=None):
        return cls(content=content, desc=desc).save()

    @property
    def content_obj(self):
        return self.document_type(**self.content)

    @property
    def _content_(self):
        content = self.content
        if '_id' in content:
            content['id'] = content['_id']
            del content['_id']
        return content

    @property
    def version_time(self):
        return self.create_time

    @classmethod
    def get_by(cls, content_id, version):
        if type(content_id) is str:
            content_id = ObjectId(content_id)
        return cls.objects(__raw__={"content._id": content_id, "version": version}).order_by('-create_time').first()

    @property
    def content_json(self):
        if self.content:
            content_str = json.dumps(self.content, cls=JsonExtendEncoder)
            return json.loads(content_str)

    def diff(self, record):
        return get_diff(record.content, self.content)

