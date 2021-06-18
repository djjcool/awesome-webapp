import functools
import inspect
import logging
import os

from urllib import parse

from aiohttp import web

#from apis import APIError

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