"""[配置文件解析]
"""
import config_default #加载开发配置文件

class Dict(dict):
    """可以用 x.y 这种写法操作dict
    """
    def __init__(self,name=(),values=(),**kw):
        super(Dict,self).__init__(**kw)
        # zip函数将参数数据分组返回[(arg1[0],arg2[0],arg3[0]...),(arg1[1],arg2[1],arg3[1]...),,,]
        # 以参数中元素数量最少的集合长度为返回列表长度
        for k,v in zip(name,values):
            self[k]=v
    
    
    
configs = config_default.configs