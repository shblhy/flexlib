import difflib


class CompareTwoDict:
    """
        比较两个字典差异
        认为数据符合mongeengine Document的定义，即不发生类型变更（变None除外)
        只比较基础差异，业务如果存在id对象的差异等情况，应当另行开发解决。
    """
    RESULTS = []

    def __init__(self, dict1, dict2, path='', mask=[], root_result_keys=[]):
        self.dict1 = dict1
        self.dict2 = dict2
        if dict1 and dict2 and type(dict1) != type(dict2):
            raise Exception("比较的对象类型必须相同：%s, %s" % (type(dict1), type(dict2)))
        self.key_list = CompareTwoDict.keys(dict1, dict2)
        if path == '' and mask:
            self.key_list = [key for key in self.key_list if not mask_contain(key, mask)]
        self.path = path
        self.root_result_keys = root_result_keys

    def compare(self, key):
        """比较一个key"""
        v1 = self.dict1.get(key)
        v2 = self.dict2.get(key)
        # 如果都是字典继续深入比较
        if isinstance(v1, dict) and isinstance(v2, dict):
            CompareTwoDict(v1, v2, self.path + '.' + key if self.path else key, root_result_keys=self.root_result_keys).main()
        # 如果是数组则遍历后比较
        elif isinstance(v1, list) or isinstance(v2, list):
            if v2 is None:
                list_length = len(v1)
            elif v1 is None:
                list_length = len(v2)
            else:
                list_length = max(len(v1), len(v2))
            for i in range(0, list_length):
                _v1 = v1[i] if v1 and len(v1) > i else None
                _v2 = v2[i] if v2 and len(v2) > i else None
                if type(_v1) == dict or type(_v2) == dict:
                    CompareTwoDict(_v1, _v2,
                                   self.path + '.' + key + '.' + str(i) if self.path else key + '.' + str(i),
                                   root_result_keys=self.root_result_keys).main()
                else:
                    self.diff(_v1, _v2, key + "." + str(i))
        # elif not v1 or not v2:
        #     self.diff(v1, v2, key)
        else:
            self.diff(v1, v2, key)
        # except Exception as e:
        #     print("d1:", self.dict1, "d2:", self.dict2, e)

    # @staticmethod
    def diff(self, v1, v2, attr):
        if v1 != v2:
            if type(v1) is dict or type(v2) is dict:
                keys = CompareTwoDict.keys(v1, v2)
                for key in keys:
                    self.add_root_result_key(self.path + '.' + attr + '.' + key if self.path else attr + '.' + key)
            else:
                self.add_root_result_key(self.path + '.' + attr if self.path else attr)

    def add_root_result_key(self, index_path):
        self.root_result_keys.append(index_path)

    @staticmethod
    def keys(dict1, dict2):
        """获取所有key"""
        # try:
        if dict1 and dict2:
            return list(set(list(dict1.keys()) + list(dict2.keys())))
        elif dict1:
            return list(dict1.keys())
        elif dict2:
            return list(dict2.keys())
        else:
            return {}
        # except Exception as e:
        #     print(dict1, dict2)

    def main(self):
        # for k in self.key_list:
        #     self.compare(k)
        if type(self.dict1) is dict and self.dict1 and not self.dict2:
            for key in self.key_list:
                if type(self.dict1.get(key)) is dict:
                    for _key in self.dict1.get(key):
                        self.add_root_result_key(self.path + '.' + key + '.' + _key if self.path else key + '.' + _key)
                else:
                    self.add_root_result_key(self.path + '.' + key if self.path else key)
        elif type(self.dict2) is dict and self.dict2 and not self.dict1:
            for key in self.key_list:
                if type(self.dict2.get(key)) is dict:
                    for _key in self.dict2.get(key):
                        self.add_root_result_key(self.path + '.' + key + '.' + _key if self.path else key + '.' + _key)
                elif type(self.dict2.get(key)) is list:
                    for _index, _item in enumerate(self.dict2.get(key)):
                        for _key in _item:
                            self.add_root_result_key(
                                self.path + '.' + key + '.' + str(_index) + '.' + str(_key)
                                if self.path else key + '.' + str(_index) + '.' + str(_key))
                else:
                    self.add_root_result_key(self.path + '.' + key if self.path else key)
        elif not self.dict1 or not self.dict2:
            for key in self.key_list:
                self.add_root_result_key(self.path + '.' + key if self.path else key)
        else:
            for k in self.key_list:
                self.compare(k)


def can_parse(p, ptype):
    try:
        ptype(p)
        return True
    except:
        return False


def easy_str(v):
    if type(v) is float:
        if int(v) == v:
            return str(int(v))
    return str(v)

def get_attr(dic, path):
    path_list = path.split('.')
    v = dic
    for p in path_list:
        if not v:
            # return v
            return ''
        if isinstance(v, dict):
            v = v.get(p)
        elif type(v) is list and can_parse(p, int):
            v = v[int(p)] if len(v) >= int(p)+1 else None
        else:
            # pass
            raise Exception('parse error %s, %s' % (path, p))
    # if type(v) is dict:
    #     return v
    return easy_str(v) if v else ''


def diff_str(s1, s2):
    res = difflib.ndiff(s1, s2)
    results = []
    last_sign = None
    for r in res:
        if r.startswith('+ '):
            now_sign = 'strong'
            item = r.replace('+ ', '', 1)
            if last_sign == now_sign:
                results.append(item)
            elif last_sign == 'em':
                s = '</%s>' % last_sign
                if now_sign == 'strong':
                    s += '<strong>'
                s += item
                results.append(s)
            else:
                results.append('<strong>' + item)
            last_sign = now_sign
        elif r.startswith('- '):
            now_sign = 'em'
            item = r.replace('- ', '', 1)
            if last_sign == now_sign:
                results.append(item)
            elif last_sign == 'strong':
                s = '</%s>' % last_sign
                if now_sign == 'em':
                    s += '<em>'
                s += item
                results.append(s)
            else:
                results.append('<em>' + item)
            last_sign = now_sign
        elif r.startswith(' '):
            item = r.replace('  ', '', 1)
            if last_sign == "strong":
                results.append("</strong>")
            elif last_sign == "em":
                results.append("</em>")
            results.append(item)
            last_sign = None
        else:
            raise Exception('difflib error')
    if last_sign:
        results.append('</%s>' % last_sign)
    return ''.join(results)


def mask_contain(index, mask):
    for key in mask:
        if key == index or index.startswith(key + '.'):
            return True
    return False


def get_diff(dic1, dic2, mask=[]):
    """该方法使用到difflib.ndiff 测试在极差情况下，响应时间可能较长，该方法不应该再在for循环中使用，以控制时间"""
    root_results = []
    cmp = CompareTwoDict(dic1, dic2, mask=mask, root_result_keys=root_results)
    cmp.main()
    res = {}
    for i in root_results:
        if not mask_contain(i, mask):
            res[i] = diff_str(get_attr(dic1, i), get_attr(dic2, i))
    return res
