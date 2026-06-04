"""App configuration for the pipeline app."""
from django.apps import AppConfig


class PipelineConfig(AppConfig):
    """Standard Django app config - sets the default primary key type."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pipeline'
