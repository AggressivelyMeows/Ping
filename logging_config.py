# just a seperate file for handling the logging
# of sanic to use with logging
from sanic.log import DefaultFilter
import sys

LOGGING = {
'version': 1,
'disable_existing_loggers': False,
'filters': {
    'accessFilter': {
        '()': DefaultFilter,
        'param': [0, 10, 20]
    },
    'errorFilter': {
        '()': DefaultFilter,
        'param': [30, 40, 50]
    }
},
'formatters': {
    'simple': {
        'format': '%(asctime)s - (%(name)s)[%(levelname)s]: %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S'
    },
    'access': {
        'format': '%(asctime)s - (%(name)s)[%(levelname)s][%(host)s]: ' +
                  '%(request)s %(message)s %(status)d %(byte)d',
        'datefmt': '%Y-%m-%d %H:%M:%S'
    }
},
'handlers': {
    'internalFile': {
        'class': 'logging.FileHandler',
        'filters': ['accessFilter'],
        'formatter': 'simple',
        'filename': "temp/clickinternal.log"
    },
    'accessFile': {
        'class': 'logging.FileHandler',
        'filters': ['accessFilter'],
        'formatter': 'access',
        'filename': "temp/clickaccess.log"
    },
    'errorFile': {
        'class': 'logging.FileHandler',
        'filters': ['errorFilter'],
        'formatter': 'simple',
        'filename': "temp/clickerr.log"
    },
    'internal': {
        'class': 'logging.StreamHandler',
        'filters': ['accessFilter'],
        'formatter': 'simple',
        'stream': sys.stderr
    },
    'accessStream': {
        'class': 'logging.StreamHandler',
        'filters': ['accessFilter'],
        'formatter': 'access',
        'stream': sys.stderr
    },
    'errorStream': {
        'class': 'logging.StreamHandler',
        'filters': ['errorFilter'],
        'formatter': 'simple',
        'stream': sys.stderr
    }
},
'loggers': {
    'sanic': {
        'level': 'DEBUG',
        'handlers': ['internal','errorStream','internalFile', 'errorFile']
    },
    'network': {
        'level': 'DEBUG',
        'handlers': ['accessStream','errorStream','accessFile', 'errorFile']
    }
}
}