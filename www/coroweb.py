import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web
from apis import APIError

def get(path):
    """Define decorator @get('/path')
    Args:
        path ([str]): [资源链接]
    """
    def decorator(func):
        #确保返回的是被装饰函数而非装饰器的引用
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper.__method__ ='GET'
        wrapper.__route__=path
        return wrapper
    return decorator

def post(path):
    """Define decorator @post('/path')
    Args:
        path ([str]): [资源链接]
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper.__method__='POST'
        wrapper.__route__=path
        return wrapper
    return decorator

def get_require_kwargs(fn):
    """获取函数命名关键字参数,且非默认参数
    Args:
        fn (function): 函数
    """
    args=[]
    # signature可以返回参数列表,是个ordered mapping
    # https://docs.python.org/zh-cn/3.8/library/inspect.html?highlight=inspect#module-inspect
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==param.KEYWORD_ONLY and param.default is param.empty:
            args.append(name)
    return tuple(args)

def get_named_kwargs(fn):
    """获取函数命名关键字参数
    Args:
        fn (function): 函数
    """
    args=[]
    # signature可以返回参数列表
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind ==param.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kwarg(fn):
    """
    判断是否有命名关键字参数

    :param fn: 函数
    :return:
    """
    # 获取函数 fn 的参数，ordered mapping
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # * 或者 *args 后面的参数
        if param.kind == param.KEYWORD_ONLY:
            return True


def has_var_kwarg(fn):
    """判断是否存在关键字参数

    Args:
        fn (function): 函数
    """
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind==param.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    """判断是否有请求参数
    Args:
        fn (function): 函数
    """
    # 这里仅获取fn签名的object用于后面抛异常
    sig=inspect.signature(fn)
    params=sig.parameters
    found=False
    for name ,param in params.items():
        if name=='request':
            found=True
            continue
        if found and (param.kind is not param.VAR_POSITIONAL and 
                    param.kind is not param.KEYWORD_ONLY and
                    param.kind is not param.VAR_KEYWORD):
            raise ValueError(
                "Request 参数必须作为函数的最后一个命名参数: %s %s"%(fn.__name__,str(sig)))
    return found

#
class RequestHandler(object):
    """目的是从url中分析其要接收的参数,从request中获取必要参数
    调用URL函数,把结果转换为web.Response对象,使其符合aiohttp的要求
    """
    def __init__(self,app,fn) -> None:
        """目的是从url中分析其要接收的参数,从request中获取必要参数
        调用URL函数,把结果转换为web.Response对象,使其符合aiohttp的要求

        Args:
            app ([obejct]): 当前app
            fn (function): 待处理函数,用于构建参数
        """
        self.__app=app
        self.__func=fn
        self.__has_request_arg=has_request_arg(fn)
        self.__has_var_kwarg=has_var_kwarg(fn)
        self.__has_named_kwarg=has_named_kwarg(fn)
        self.__name_kwargs=get_named_kwargs(fn)
        self.__required_kwargs=get_require_kwargs(fn)

    #使得类可以被调用
    async def __call__(self,request):
        kwargs=None
        if self.__has_named_kwarg or self.__has_var_kwarg or self.__required_kwargs:
            if request.method=="POST":
                if not request.content_type:
                    return web.HTTPBadRequest(text="Missing Content-Type")
                ct =request.content_type.lower()
                #解析json
                if ct.startswith('application/json'):
                    params=await request.json()
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest(text="JSON body must be dict object")
                    kwargs=params
                #form 表单编码为 字典形式发送到服务器
                elif ct.startswith("appliction/x-www-form-urlencoded") or ct.startswith("multipart/form-data"):
                    params=await request.post()
                    kwargs=dict(**params)
                else:
                    return web.HTTPBadRequest(text="Unsupported Content-Type: %s"%request.content_type)
            if request.method == 'GET':
                qs=request.query_string
                if qs:
                    kwargs=dict()
                     # {'id': ['10']}
                    for k,v in parse.parse_qs(qs,True).items():
                        kwargs[k]=v[0]
        if kwargs is None:
            kwargs=dict(**request.match_info)
        else:
            if not self.__has_var_kwarg and self.__name_kwargs:
                # 移除全部 unnamed kwargs
                copy=dict()
                for name in self.__name_kwargs:
                    if name in kwargs:
                        copy[name]=kwargs[name]
                kwargs=copy
            # 检查命名关键字参数
            for k,v in request.match_info.items():
                if k in kwargs:
                     logging.warning('Duplicate arg name in named kwargs and kwargs: %s' % k)
                kwargs[k]=v
        if self.__has_request_arg:
            kwargs['request']=request
        #检查requierd kwargs
        if self.__required_kwargs:
            for name in self.__required_kwargs:
                if name not in kwargs:
                    return web.HTTPBadRequest(text="缺少参数 %s"%name)
        logging.info("call with kwargs : %s"%str(kwargs))
        try:
            r= await self.__func(**kwargs)
            return r
        except APIError  as e:
            return dict(error=e.error,data=e.data,message=e.message)

def add_static(app):
    """为返回的静态文件添加一个路由和一个handler
     /www/static
    Args:
        app ([obejct]): 当前app对象
    """
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    app.router.add_static('/static/',path)
    logging.info("add static %s =>%s"%('/static/',path))
    
def add_route(app,fn):
    """注册url处理函数,拿到 method 和 path 属性,然后封装好添加给 aiohttp 框架
    当 handler 是正则函数时，内部会转为协程 
    Args:
        app ([object]): 当前app对象
        fn (function): 当前要注册的url

    Raises:
        ValueError: 没有定义是GET还是POST方法
    """
    method=getattr(fn,'__method__',None) #反射
    path=getattr(fn,'__route__',None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s'%str(fn))
    #if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
    #    fn=asyncio.coroutine(fn)
    logging.info('add route %s %s=>%s(%s)'%(method,path,fn.__name__,",".join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method,path,RequestHandler(app,fn))
    
def add_routes(app,module_name):
    """把多次add_route调用换成自动扫描

    Args:
        app ([type]): [当前app对象]
        module_name ([str]): [自动化扫描包名导入路由定义]
    """
    n=module_name.rfind(".")
    # For package.module, n = 7
    # For module, n = -1
    if n==(-1):
        # 导入 module
        mod = __import__(module_name,globals(),locals())
    else:
        # package.module ,name =module 进行导入
        name=module_name[n+1:]
        # Import package.module,等价于 'from package import module', fromlist = [module]
        mod=getattr(__import__(module_name[:n],globals(),locals(),name))
    # module的属性字典
    for attr in dir(mod):
        if attr.startswith("_"):
            continue
        fn=getattr(mod,attr)
        if callable(fn):
            method=getattr(fn,"__method__",None)
            path=getattr(fn,"__route__",None)
            if method and path:
                add_route(app,fn)