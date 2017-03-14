from env import *

# Common configuration
class Config(object):
    """
    # Put any configurations here that are common across all environments
    """


# Development configurations
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SECRET_KEY = THE_SECRET_KEY
    SQLALCHEMY_DATABASE_URI = "mysql://" + DB_USER + ":" + DB_PASS + "@127.0.0.1:3307/" + DB_NAME

# Production configurations
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = True
    SECRET_KEY = THE_SECRET_KEY
    SQLALCHEMY_DATABASE_URI = "mysql://" + DB_USER + ":" + DB_PASS + "@127.0.0.1:3307/" + DB_NAME

app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
