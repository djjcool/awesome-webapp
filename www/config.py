"""[配置文件解析]
"""
import config_default #加载开发配置文件

class Dict(dict):
    """可以用 x.y 这种写法操作dict
    """
    def __init__(self,name=(),values=(),**kw):
        super(Dict,self).__init__(**kw)
        # zip函数将参数数据分组返回
        # >>list(zip('abcdefg', range(3), range(4)))
        # <<[('a', 0, 0), ('b', 1, 1), ('c', 2, 2)]
        # 以参数中元素数量最少的集合长度为返回列表长度
        for k,v in zip(name,values):
            self[k]=v
            
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults,override):
    """合并数据库配置

    Args:
        defaults ([dict]): [原配置]
        override ([dict]): [覆盖配置]
    """
    r={}
    for k,v in defaults.items():
        if k in override:
            if isinstance(v,dict):
                r[k]=merge(v,override[k])
            else:
                r[k]=override[k]
        else:
            r[k]=v
    return r
def toDict(d):
    """转自制强化版Dict
    Args:
        d ([dict])
    """
    D=Dict()
    for k,v in d.items():
        D[k]=toDict(v) if isinstance(v,dict) else v
    return D
    
configs = config_default.configs

try:
    import config_override
    configs=merge(configs,config_override.configs)
except ImportError:
    pass

configs=toDict(configs)