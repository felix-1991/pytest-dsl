"""Variables belonging to one remote call, never a process-wide cache.

ContextVar tokens also isolate nested calls and are reset on failure. Inputs
are separate from output captures, so large snapshots are not echoed back.
"""

from contextvars import ContextVar
from copy import deepcopy


_current = ContextVar('pytest_dsl_request_variables', default=None)


def current_request_variables():
    return _current.get()


class RequestVariables:
    def __init__(self, values, *, isolated=True, global_names=()):
        self.values = deepcopy(values)
        self.isolated = isolated
        self.global_names = {name for name in values if name.startswith('g_')}
        self.global_names.update(name for name in global_names if name in values)
        self.updates = {}
        self.deleted = set()

    def __enter__(self):
        self._token = _current.set(self)
        return self

    def __exit__(self, *exc):
        _current.reset(self._token)

    def set(self, name, value):
        self.global_names.add(name)
        self.values[name] = value
        self.updates[name] = value
        self.deleted.discard(name)

    def delete(self, name):
        self.values.pop(name, None)
        self.updates.pop(name, None)
        self.deleted.add(name)

    def effects(self):
        return {'set': dict(self.updates), 'deleted': sorted(self.deleted)}
