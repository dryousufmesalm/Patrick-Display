"""
Event and data handlers for MetaTrader integration

This package contains handlers for processing events, managing data flow,
and handling real-time updates between MetaTrader and Supabase.
"""

from .event_handler import EventHandler, EventType, EventSeverity

__all__ = [
    'EventHandler',
    'EventType',
    'EventSeverity'
]
