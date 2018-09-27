from .dbots import v1 as dbots_v1


def api_root():
    return "ok", 200


__all__ = [
    dbots_v1,
    api_root
]
