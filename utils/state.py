# Shared runtime state

_maintenance_mode = False

def get_maintenance_mode():
    return _maintenance_mode

def set_maintenance_mode(value):
    global _maintenance_mode
    _maintenance_mode = value
