import asyncio
import orm
from models import User

async def test(loop):
    await orm.create_pool(user='root', password='password', db='moe')
    a=User(name="Adminstrator",email="admin@example.com",passwd="1234567890",image="about:blank")
    x=User(name="djj",email="djj@example.com",passwd="1234567890",image="about:blank")
    t=User(name="Test",email="test@example.com",passwd="1234567890",image="about:blank")
    await a.save()
    await x.save()
    await t.save()
    
loop=asyncio.get_event_loop()
loop.run_until_complete(test(loop))