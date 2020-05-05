# copy from https://github.com/zhangbailong945/mongoengine_adapter/blob/master/casbin_mongoengine_adapter/adapter.py
import casbin
from casbin import persist
from mongoengine import Document
from mongoengine import connect
from mongoengine.fields import IntField, StringField
from app.database import BP_ARCHIVE


class CasbinRule(Document):
    '''
    CasbinRule model
    '''

    __tablename__ = "casbin_rule"

    ptype = StringField(required=True, max_length=255)
    v0 = StringField(max_length=255)
    v1 = StringField(max_length=255)
    v2 = StringField(max_length=255)
    v3 = StringField(max_length=255)
    v4 = StringField(max_length=255)
    v5 = StringField(max_length=255)
    v6 = StringField(max_length=255)

    meta = {'strict': True, 'db_alias': BP_ARCHIVE}

    def __str__(self):
        text = self.ptype
        if self.v0:
            text = text + ', ' + self.v0
        if self.v1:
            text = text + ', ' + self.v1
        if self.v2:
            text = text + ', ' + self.v2
        if self.v3:
            text = text + ', ' + self.v3
        if self.v4:
            text = text + ', ' + self.v4
        if self.v5:
            text = text + ', ' + self.v5
        if self.v6:
            text = text + ', ' + self.v6

        return text

    def __repr__(self):
        return '<CasbinRule :"{}">'.format(str(self))


class Adapter(persist.Adapter):
    """the interface for Casbin adapters."""

    def __init__(self, dbname, host):
        connect(db=dbname, host=host)

    def load_policy(self, model):
        '''
        implementing add Interface for casbin \n
        load all policy rules from mongodb \n
        '''
        lines = CasbinRule.objects()
        for line in lines:
            persist.load_policy_line(str(line), model)

    def _save_policy_line(self, ptype, rule):
        line = CasbinRule(ptype=ptype)
        if len(rule) > 0:
            line.v0 = rule[0]
        if len(rule) > 1:
            line.v1 = rule[1]
        if len(rule) > 2:
            line.v2 = rule[2]
        if len(rule) > 3:
            line.v3 = rule[3]
        if len(rule) > 4:
            line.v4 = rule[4]
        if len(rule) > 5:
            line.v5 = rule[5]
        line.save()

    def save_policy(self, model):
        '''
        implementing add Interface for casbin \n
        save the policy in mongodb \n
        '''
        for sec in ["p", "g"]:
            if sec not in model.model.keys():
                continue
            for ptype, ast in model.model[sec].items():
                for rule in ast.policy:
                    self._save_policy_line(ptype, rule)
        return True

    def add_policy(self, sec, ptype, rule):
        """add policy rules to mongodb"""
        self._save_policy_line(ptype, rule)

    def remove_policy(self, sec, ptype, rule):
        """delete policy rules from mongodb"""
        if sec in ["p", "g"]:
            condition = {'ptype': sec}
            data = dict(zip(['v0', 'v1', 'v2', 'v3', 'v4', 'v5'], rule))
            for k in data:
                condition[k] = data[k]
            check = CasbinRule.objects(**condition)
            if check.count() > 0:
                CasbinRule.objects.filter(**condition).delete()
                return True
            else:
                return False
        else:
            return False

    def remove_filtered_policy(self, sec, ptype, field_index, *field_values):
        """
        delete policy rules for matching filters from mongodb
        """
        if sec not in ["p", "g"]:
            return False
        condition = {'ptype': sec}
        conditions = dict(zip(['v%s' % str(i) for i in range(0, len(field_values))], field_values))
        condition.update(conditions)
        check = CasbinRule.objects(**condition)
        if check.count() > 0:
            CasbinRule.objects(**condition).delete()
            return True
        else:
            return False
