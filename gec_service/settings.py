from os import environ

EXCHANGE = 'grammar'

MQ_HOST = environ.get('MQ_HOST', 'localhost')
MQ_PORT = int(environ.get('MQ_PORT', '5672'))
MQ_USERNAME = environ.get('MQ_USERNAME', 'guest')
MQ_PASSWORD = environ.get('MQ_PASSWORD', 'guest')

MQ_TIMEOUT = int(environ.get('MESSAGE_TIMEOUT', 30)) * 1000  # time in milliseconds
