import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevConfig(Config):
    ENV = 'development'
    DEBUG = True
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url:
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        _instance_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'instance',
        )
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_instance_path, 'waaahgame.db')


class ProdConfig(Config):
    ENV = 'production'
    DEBUG = False
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url:
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        _instance_path = os.environ.get(
            'WAAAHGAME_INSTANCE_DIR',
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance'),
        )
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_instance_path, 'waaahgame.db')


_config_map = {
    'dev': DevConfig,
    'prod': ProdConfig,
    'default': DevConfig,
}


def get_config(name='dev'):
    return _config_map.get(name, DevConfig)
