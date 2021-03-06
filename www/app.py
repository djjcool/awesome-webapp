import logging
from re import template
from ssl import Options;logging.basicConfig(level=logging.INFO)
import asyncio,os,json,time,orm
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from coroweb import add_route, add_routes, add_static
from config import configs

logging.basicConfig(level=logging.INFO)

def init_jinja2(app,**kwargs):
    logging.info(" 初始化 jinja2...")
    options=dict(
        autoescape=kwargs.get('autoescape', True),
        block_start_string=kwargs.get('block_start_string', '{%'),
        block_end_string=kwargs.get('block_end_string', '%}'),
        variable_start_string=kwargs.get('variable_start_string', '{{'),
        variable_end_string=kwargs.get('variable_end_string', '}}'),
        auto_reload=kwargs.get('auto_reload', True)
    )
    path=kwargs.get('path',None)
    if path is None:
        path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
    logging.info('Set jinja2 template path: %s' % path)
    # 从文件系统的字典中加载一个模板
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kwargs.get('filters', None)
    if filters is not None:
        # Filters are Python functions
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env
    
async def logger_factory(app,handler):
    """记录URL日志的中间件
    """
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return await handler(request)
    return logger
# 把表单和JSON转化为 web.Response 对象的中间件
async def data_factory(app,handler):
    async def parse_data(request):
        #JSON数据
        if request.content_type.startswith('application/json'):
            # Read request body decoded as json
            request.__data__ = await request.json()
            logging.info('Request json: %s' % str(request.__data__))
        # form 表单数据被编码为 key/value 格式发送到服务器（表单默认的提交数据的格式）
        elif request.content_type.startswith('application/x-www-form-urlencoded'):
            # Read POST parameters from request body
            request.__data__ = await request.post()
            logging.info('Request form: %s' % str(request.__data__))
        return await handler(request)
    return parse_data

# 把response返回值转化为 web.Response 对象返回
async def response_factory(app,handler):
    async def response(request):
        logging.info("response handler")
        r=await handler(request)
        if isinstance(r,web.StreamResponse):
            return r
        if isinstance(r,bytes):
            resp=web.Response(body=r)
            #二进制数据处理
            resp.content_type='application/octet-stream'
            return resp
        if isinstance(r,str):
            if r.startswith('redirect'):
                return web.HTTPFound(r[9:])
            resp=web.Response(body=r.encode('utf-8'))
            resp.content_type='text/html;charset=UTF-8'
            return resp
        if isinstance(r,dict):
            template=r.get("__template__")
            if template is None:
                # 这里dumps是使用序列化r为JSON
                # default函数为把任意对象变成一个可序列为JSON的对象(也就是字典)
                # __dict__魔法方法可获取任意class内部的属性,并且以字典形式存在
                # https://docs.python.org/3/library/json.html#json.dumps
                resp=web.Response(body=json.dumps(r,ensure_ascii=False,default=lambda o:o.__dict__).encode("utf-8"))
                resp.content_type= 'application/json; charset=UTF-8'
                return resp
            else:
                #加载模板,渲染模板
                #app['__templating__'] 是Environment 对象
                resp=web.Response(body=app['__templating__'.get_template(template).render(**r).encode('utf-8')])
                resp.content_type='text/html;charset=UTF-8'
                return resp
        # 服务器状态码
        if isinstance(r,int) and 100<=r<600:
            return web.Response(status=r)
        # 状态码与原因短语 
        if isinstance(r,tuple) and len(r)==2:
            t,m=r
            if isinstance(t,int) and 100<=t <600:
                return web.Response(status=t,reason=str(m))
        # 默认
        resp = web.Response(body=str(r).encode("utf-8"))
        #纯文本格式
        resp.content_type='text/plain;charset=UTF-8'
        return resp
    return response

def datetime_filter(t):
    """时间过滤器
    Args:
        t ([datetime]): 时间戳秒
    Returns:
        [unicode字符串]: ["x分钟前"这样的时间表示字符串]
    """
    delta=int(time.time()-t)
    if delta<60:
        return u'1分钟前'
    if delta<3600:
         return u'%s分钟前' % (delta // 60)
    if delta < 86400:  # 24 h
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:  # 7 days
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

async def init_db(app):
    """获取database配置信息
    如果在Linux系统运行,避免使用root作为用户名
    """
    await orm.create_pool(
        
        host=configs.db.host,
        port=configs.db.port,
        user=configs.db.user,
        password=configs.db.password,
        db=configs.db.database
    )



    

    




if __name__=='__main__':
    # 加载自己的中间件
    app=web.Application(middlewares=[logger_factory,response_factory])
    # 加载自己的时间过滤器
    init_jinja2(app,filter=dict(datetime=datetime_filter))
    add_routes(app,'handlers')
    add_static(app)
    app.on_startup.append(init_db)
    '''
    app.router.add_get("/",index)
    async def index(request):
    return web.Response(body=b"<h1>Awesome</h1>'",content_type='text/html')
    '''
    
    web.run_app(app,host='localhost',port=9000)


