from collections import defaultdict
import logging,aiomysql,asyncio
from typing import Any
from aiohttp.web import main
from attr import field
# from attr import field
# from pymysql import charset
#from app import *




async def create_pool(loop,**kw):
    """创建异步连接池
    这里使用字典解析为参数的方式
    """
    logging.info("创建数据库连接池...")
    global __pool
    __pool=await aiomysql.create_pool(
        # 字典的get方法其实就是如果key不存在,备选后面的
        host=kw.get('host','localhost'),
        port=kw.get('port','3306'),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset','utf8'),
        autocommit=kw.get('autocommit',True),
        maxsize=kw.get('maxsize',10),
        minsize=kw.get('minisize',1),
        loop=loop
    )


async def select(sql,args,size=None):
    """第三个参数用于限定获取数据大小"""
    logging.log(sql,args)
    global __pool
    async with __pool.acquire() as conn:
        cur= await conn.cursor(aiomysql.DictCursor)
        # 这里利用 sql 占位符 替换 字符串,防止sql注入
        await cur.execute(sql.replace("?","%s"),args or ())
        if size:
            rs=await cur.fetchmany(size)
        else:
            rs=await cur.fetchall()
        await cur.close()
        logging.info("获取了%s条数据"%len(rs))
        return rs

#INSERT UPDATE DELETE
async def execute(sql,args,autocommit=True):
    """执行"""
    logging.log(sql)
    async with __pool.acquire() as conn:
        if not autocommit:
            await conn.begin()
        try:
            cur=await conn.cursor()
            # 这里利用 sql 占位符 替换 字符串,防止sql注入
            await cur.execute(sql.replace("?","%s"),args or ()) 
            # 此处返回的执行结果数
            affected=cur.rowcount()
            if not autocommit:
                await cur.commit()
        except BaseException:
            if not autocommit:
                await cur.rollback()
            raise
        return affected

def create_args_string(num):
    return ', '.join(['?'] * num)

class ModelMetaclass(type):
    '''
    参考type式创建 type("类名",(父类集合,),{函数及属性})
    Hello = type('Hello', (object,), {hello:fn})
    参数: 
    1.类
    2.类名 
    3.bases代表被动态修改的类的所有父类
    4.代表被动态修改的类的所有属性、方法组成的 字典
    '''
    def __new__(cls,name,bases,attrs):
        #1.排除对 ORM的基类本身 的修改
        if name=='Model':
            return type.__name__(cls,name,bases,attrs)
        #2.1.获取table名
        tableName=attrs.get('__table__',None) or name
        print("发现model %s(table:%s)"%(name,tableName))
        #2.2获取所有字段和主键名称
        mappings=dict()
        fields=[]
        primaryKey=None
        # 如果找到'字段'属性,则保存到__mappings__,
        for k,v in attrs.items():
            if isinstance(v,Field):
                print("发现映射%s==>%s"%(k,v) )
                mappings[k]=v
                #发现主键
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        #如果没有发现主键
        if not primaryKey:
            raise RuntimeError('没找到Primary key ')
        #同时从类属性中删除该属性
        for k in mappings.keys():
            attrs.pop(k)
        '''
        ### 放弃该构建
        map(作用函数,被作用的函数序列)
        # 字段全部输入 %f来构建字段字符串
        escapsed_fields=list(map(lambda f:'%s'%f,fields))
        '''
        #3.保存映射,列等
        attrs['__mappings__']=mappings
        attrs['__table__']=tableName#把表名保存在 __table__ 里
        attrs['__primary_key__']=primaryKey
        attrs['__select__'] = 'SELECT %s, %s FROM %s' % (primaryKey, ', '.join(fields), tableName)
        attrs['__insert__'] = 'INSERT INTO %s (%s, %s) VALUES (%s)' % (
            tableName, ', '.join(fields), primaryKey, create_args_string(len(fields) + 1))
        attrs['__update__'] = 'UPDATE %s SET %s WHERE %s = ?' % (
            tableName, ', '.join(map(lambda f: '%s = ?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'DELETE FROM %s WHERE %s = ?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

# ORM的基类
# 继承自字典,可以使用字典所有功能 如 user['id']
class Model(dict,metaclass=ModelMetaclass):
    def __init__(self,**kw):
        super(Model,self).__init__(**kw)

    #可以使用.方法取值 如user.id
    def __getattr__(self, key: str) :
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model'对象没有%s属性"%key)
    def __setattr__(self, key: str, value: Any) -> None:
        self[key] =value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value=getattr(self,key,None)
        if value is None:
            field=self.__mappings__[key]
            if field.default() is not None:
                value=field.default() if callable(field.default) else field.default
                logging.debug("使用默认值 %s:%s"%(key,str(value)))
                setattr(self,key,value)
            return value

    @classmethod
    async def find_all(cls,where=None,args=None,**kw):
        sql=[cls.__select__]
        if where:
            sql.append('WHERE')
            sql.append(where)
        if args is None:
            args=[]
        order_by=kw.get('order_by',None)
        


    '''
    def save(self):
        fields=[]
        params=[]
        args=[]
        for k,v in self.__mappings.item():
            fields.append(v.name)
            params.append("?")
            args.append(getattr(self,k,None))
        # (field,field,fields ) values(params,param,param)
        sql='insert into %s (%s) values (%s)'%(self.__table__,",".join(fields),",".join(params))
        print("SQL: %s" %sql)
        print("ARGS:%s"%str(args))
    '''
class Field:
    def __init__(self,name,column_type,primary_key,default) -> None:
        self.name=name
        self.column_type=column_type
        self.primary=primary_key
        self.default=default
    def __str__(self) -> str:
        return '<%s:%s>'%(self.__class__.__name__,self.column_type,self.name)

class BooleanField(Field):
    def __init__(self, name=None,default=None) -> None:
        super().__init__(name,'boolean',False,default)

class StringField(Field):
    def __init__(self, name=None,primary_key=False,default=None,ddl="varchar(100)") -> None:
        super().__init__(name,ddl,primary_key,default)

class IntegerField(Field):
    def __init__(self, name=None,primary_key=False,default=0) -> None:
        super().__init__(name,'bigint',primary_key,default)

class FloatField(Field):
    def __init__(self, name=None,primary_key=False,default=0.0) -> None:
        super().__init__(name,'real',primary_key,default)

class TextField(Field):
    def __init__(self, name=None,default=None) -> None:
        super().__init__(name,'text',False,default)


class User(Model):
    id=IntegerField("id")
    name=StringField("username")
    email=StringField("email")
    password=StringField("password")

if __name__=='__main__':
    print(111)
    u = User(id=12345, name='Michael', email='test@orm.org', password='my-pwd')
    # 保存到数据库：
    u.save()