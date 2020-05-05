import pprint
from bson import ObjectId
from app.user.models import Account, Role
from app.deal2.models.deal import Deal
from app.deal2.models.deal_memo import DealMemo
from app.deal2.models.memo import StandardMemo, DealEasyItem
from app.deal2.serializers.memo import StandardMemoSerializer
from unittest import TestCase
from utils.time import WeekTime
from utils.mongoengine import Document
from app.user.models import Department
from app import app
from mongoengine import StringField, IntField, \
    BooleanField

from app.database import BP_ARCHIVE, STRICT_CHECK
from utils.decorators import cached_property
from utils.mongoengine import Document


class Department2(Document):
    _model_desc_ = '部门'
    name = StringField()
    desc = StringField(required=False)
    order = IntField(verbose_name='部门序号', help_text='排序使用')
    insights_sort_right = IntField(help_text="insight展示的时候不同部门排序的顺序")
    has_right_for_insight = BooleanField()

    meta = {'strict': True, 'db_alias': 'local_archive', 'collection': 'department'}


class TestReferenceField(TestCase):
    def test_save_department2(self):
        for d in Department.objects():
            a = d.to_dict()
            print(a)
            # d.switch_db('local_archive')
            d2 = Department2.create_with(a)
            d2.save()
        # Department2(
        #     name='test',
        #     desc = '',
        #     order = '1'
        # ).save()
