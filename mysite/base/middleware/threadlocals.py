# threadlocals middleware
from django.db import connections
from django.core import signals

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()
def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_request():
    return getattr(_thread_locals, 'req', None)

class ThreadLocals(object):
    """Middleware that gets various objects from the
    request object and saves them in thread local storage."""
    def process_request(self, request):
        _thread_locals.req = request
        _thread_locals.user = getattr(request, 'user', None)


# Register an event that resets _thread_locals.current_request
# when a Django request is started.
def reset_request(**kwargs):
    _thread_locals.req = None
    _thread_locals.user = None

signals.request_started.connect(reset_request)
