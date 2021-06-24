"""开发环境用的默认配置文件,生产环境用 config_override.py覆盖部分配置
"""
configs={
    "db":{
        "host": '127.0.0.1',
        'port': 3306,
        'user': 'www-data',
        'password': 'www-data',
        'database': 'awesome'
    },
    'session': {
        'secret': 'AwEsOmE'
    }
}