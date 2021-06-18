

import asyncio
import orm
from models import User, Blog, Comment
# 这部分源码来自 https://aodabo.tech/blog/001546713871394a2814d2c180b4e6f8d30c62a3eaf218a000
async def test(loop):                      # *** 注意此处的密码填自己设的密码 ***
    await orm.create_pool(loop=loop, user='root', password='password', db='moe')
                                           # *** 注意此处的密码填自己设的密码 ***
    u = User(name='Test', email='test@qq.com', passwd='password', image='about:blank')
    await u.save()
    ## 网友指出添加到数据库后需要关闭连接池，否则会报错 RuntimeError: Event loop is closed
    orm.__pool.close()
    await orm.__pool.wait_closed()
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    loop.close()
    
'''
import pymysql

conn=pymysql.connect(host='localhost',port=3306,user='root',passwd='password',db='moe')
cursor=conn.cursor()
cursor.close()
'''