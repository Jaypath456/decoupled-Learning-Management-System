"""Aggregates WebSocket URL patterns across the project, the same way
lms_project/urls.py aggregates each app's REST urls.py. Feature apps
that add their own consumers in later milestones should define their
own `websocket_urlpatterns` (e.g. messaging/routing.py) and get included
here, rather than growing this file indefinitely.
"""
from django.urls import path

from .consumers import EchoConsumer

websocket_urlpatterns = [
    path('ws/echo/', EchoConsumer.as_asgi()),
]
