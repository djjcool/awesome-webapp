import logging,aiomysql
from typing import Any
from aiohttp.web import main
from attr import field
# from attr import field
# from pymysql import charset
#from app import *




async def create_pool(loop,**kw):
    """
    创建异步连接池
    这里使用字典解析为参数的方式
    """
    logging.info("创建数据库连接池...")
    global __pool
    __pool=await aiomysql.create_pool(
        # 字典的get方法其实就是如果key不存在,备选后面的
        host=kw.get('host','localhost'),
        port=kw.get('port',3306),
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
    """
    第三个参数用于限定获取数据大小
    """
    logging.info(sql,args)
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
    logging.info(sql)
    async with __pool.acquire() as conn:
        if not autocommit:
            await conn.begin()
        try:
            cur=await conn.cursor()
            # 这里利用 sql 占位符 替换 字符串,防止sql注入
            await cur.execute(sql.replace("?","%s"),args) 
            # 此处返回的执行结果数
            affected=cur.rowcount
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
    def __new__(mcs, name, bases, attrs):
        # 排除 Model 类本身
        if name == 'Model':
            return type.__new__(mcs, name, bases, attrs)
        #2.1.获取table名
        tableName=attrs.get('__table__',None) or name
        print("发现model %s(table:%s)"%(name,tableName))
        #2.2获取所有字段和主键名称
        mappings=dict()
        fields=[]
        primary_key =None
        # 如果找到'字段'属性,则保存到__mappings__,
        for k,v in attrs.items():
            if isinstance(v,Field):
                print("发现映射%s==>%s"%(k,v) )
                mappings[k]=v
                #发现主键
                if v.primary_key:
                    if primary_key :
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primary_key  = k
                else:
                    fields.append(k)
        #如果没有发现主键
        if not primary_key:
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
        attrs['__primary_key__']=primary_key
        # 除主键外的属性名
        attrs['__fields__'] = fields
        attrs['__select__'] = 'SELECT %s, %s FROM %s' % (primary_key, ', '.join(fields), tableName)
        attrs['__insert__'] = 'INSERT INTO %s (%s, %s) VALUES (%s)' % (
            tableName, ', '.join(fields), primary_key, create_args_string(len(fields) + 1))
        attrs['__update__'] = 'UPDATE %s SET %s WHERE %s = ?' % (
            tableName, ', '.join(map(lambda f: '%s = ?' % (mappings.get(f).name or f), fields)), primary_key)
        attrs['__delete__'] = 'DELETE FROM %s WHERE %s = ?' % (tableName, primary_key)
        return type.__new__(mcs, name, bases, attrs)


class Model(dict,metaclass=ModelMetaclass):
    """ORM的基类
    继承自字典,可以使用字典所有功能 如 user['id'].
    """
    def __init__(self,**kw):
        super(Model,self).__init__(**kw)

    #可以使用.方法取值 如user.id
    def __getattr__(self, key: str) :
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model'对象没有%s属性"%key)
    #设置属性
    def __setattr__(self, key: str, value: Any) -> None:
        self[key] =value
    #通过属性获取值
    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value=getattr(self,key,None)
        #如果value为空,定位 Key,如果不为空则返回
        if value is None:
            field=self.__mappings__[key]
            if field.default is not None:
                # 如果field.default不为空,就赋值给value
                value=field.default() if callable(field.default) else field.default
                logging.debug("使用存在的默认值 %s:%s"%(key,str(value)))
                setattr(self,key,value)
        return value

    @classmethod
    async def find_all(cls,where=None,args=None,**kw):
        """ 查询全部值
        """
        sql=[cls.__select__]
        if where:# 如果where有值则加上字符串 WHERE 和变量where
            sql.append('WHERE')
            sql.append(where)
        if args is None: # 如果find_all函数没有传入where 则将'[]'传入 args
            args=[]
        #如果 order_by的值不存在,则返回空值
        order_by=kw.get('order_by',None)
        if order_by:
            sql.append('ORDER BY')
            sql.append(order_by)
        #如果 limit的值不存在,则返回空值
        limit=kw.get('limit',None)
        if limit is not None:
            sql.append("LIMIT")
            #如果 limit为整数
            if isinstance(limit,int):
                sql.append('?')
                args.append(limit)
            #如果 limit为元组且只有两个元素
            elif isinstance(limit,tuple) and len(limit)==2:
                sql.append('?,?')
                # 就把limit加在末尾
                args.extend(limit)
            else:
                raise ValueError("limit子句数值错误: %s "%str(limit))
        rows= await select(" ".join(sql),args)
        return [cls(**row) for row in rows]

    @classmethod
    async def find_number(cls,select_field,where=None,args=None):
        """找到选中的数和它的位置
        """
        sql=['SELECT %s _num_ FROM %s'%(select_field,cls.__table__)]
        if where:
            sql.append('WHERE')
            sql.append(where)
        rows=await select(" ".join(sql),args,1)
        if len(rows)==0:
            return None
        return rows[0]['_num_']    

    @classmethod
    async def find(cls,primary_key):
        """通过主键查找对象
        """
        rows= await select('%s WHERE %s =?'%(cls.__select__,cls.__primary_key__),[primary_key],1)
        if len(rows)==0:
            return None
        return cls(**rows[0])

    # Model类里添加的实例方法可以让所有子类调用
    async def save(self):
        """执行插入对象数据
        """
        print(self.__fields__)
        args=list(map(self.getValueOrDefault,self.__fields__))
        print(args)
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows=await execute(self.__insert__,args)
        if rows!=1:
            logging.warning("插入失败: affected rows: %s" % rows)

    async def update(self):
        """执行更新对象数据
        """
        args=list(map(self.getValue,self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows=await execute(self.__update__,args)
        if rows!=1:
            logging.warning("更新失败:affected rows :%s"%rows)

    async def remove(self):
        """执行删除数据
        """
        args=[self.getValue(self.__primary_key__)]
        print("args: %s"%args)
        rows =await execute(self.__delete__,args)
        if rows!=1:
            logging.warning("删除失败:affected rows :%s"%rows)


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
class Field(object):
    """字段名/类型/主键/默认值
    """
    def __init__(self,name,column_type,primary_key,default) -> None:
        self.name=name
        self.column_type=column_type
        self.primary_key=primary_key
        self.default=default
    def __str__(self) -> str:
        return '<%s:%s:%s>'%(self.__class__.__name__,self.column_type,self.name)

class BooleanField(Field):
    def __init__(self, name=None,default=False) -> None:
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


