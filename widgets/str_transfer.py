import re


def transfer_underline(name):
    """驼峰转下划线"""
    pattern = re.compile(r'([A-Z]{1})')
    res = re.sub(pattern, '_' + r'\1', name).lower()
    while res.startswith('_'):
        res = res[1:]
    while res.endswith('_'):
        res = res[-1:]
    return res
