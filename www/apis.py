import json,logging,inspect,functools
'''
JSON API definition.
'''
class APIError(Exception):
    """ APIError 的基类包含 error(required), data(optional) 和 message(optional).
    """
    def __init__(self, error,data='',message=''):
        super(APIError,self).__init__(message)
        self.error=error
        self.data=data
        self.message=message
        
class APIValueError(APIError):
    """Indicate the input value has error or invalid. The data specifies the error field of input form.
    """
    def __init__(self, field,message=''):
        super(APIError,self).__init__('value:invalid',field,message)
        
class APIResourceNotFoundError(APIError):
    """Indicate the resource was not found. The data specifies the resource name.
    """
    def __init__(self, field,message=''):
        super(APIResourceNotFoundError,self).__init__('value:notfound', field, message)
        
class APIPermissionError(APIError):
    """Indicate the api has no permission.
    """
    def __init__(self, message=""):
        super(APIPermissionError,self).__init__('permission:forbidden','permission',message)