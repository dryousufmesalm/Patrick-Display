"""
Api package - Compatibility layer for legacy PocketBase API
Now uses Supabase authentication under the hood
"""

from .APIHandler import API, APIHandler

__all__ = ['API', 'APIHandler']
