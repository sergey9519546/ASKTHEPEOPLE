"""
Celery Application Module Alias
Re-exports celery_app from app.celery_app for flexibility.
"""

from .celery_app import celery_app

__all__ = ['celery_app']
