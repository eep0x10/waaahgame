"""
Registry for wargame system validators.

Usage:
    @register
    class MyValidator(BaseValidator):
        code = 'my_code'
        ...

    get('my_code')()   # instantiate
    all_systems()      # {'my_code': MyValidator, ...}
"""

_REGISTRY: dict = {}


def register(cls):
    """Class decorator: registers a BaseValidator subclass by its code."""
    if not cls.code:
        raise ValueError(f"Validator class {cls.__name__} has no code set")
    _REGISTRY[cls.code] = cls
    return cls


def get(code: str):
    """Return the validator *class* for the given system code."""
    if code not in _REGISTRY:
        raise ValueError(
            f"Unknown wargame system: {code!r}. "
            f"Registered systems: {list(_REGISTRY)}"
        )
    return _REGISTRY[code]


def all_systems() -> dict:
    """Return a copy of the full registry {code: ValidatorClass}."""
    return dict(_REGISTRY)
