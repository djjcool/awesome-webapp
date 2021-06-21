import logging
from ssl import Options;logging.basicConfig(level=logging.INFO)
import asyncio,os,json,time,orm
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from coroweb import add_routes, add_static


def init_jinja2(app,**kwargs):
    logging.info(" 初始化 jinja2...")
    Options=dict(
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

async def index(request):
    return web.Response(body=b"<h1>Awesome</h1>'",content_type='text/html')

def init():
    app=web.Application()
    app.router.add_get("/",index)
    web.run_app(app,host='127.0.0.1',port=9000)

    


if __name__=='__main__':
    init()


