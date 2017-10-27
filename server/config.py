class BaseConfig:
    """Base configuration"""
    DEBUG = False
    TESTING = False
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = set(['vcf', 'gz'])


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True


class TestingConfig(BaseConfig):
    """Testing configuration"""
    DEBUG = True
    TESTING = True


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
