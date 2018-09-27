from .account import (
    check_permission_safety,
    get_private_key
)

from .contract import (
    create_signed_contract_transaction
)

from .tool import (
    Cached,
    load_module
)

from .swagger import (
    SwaggerParser
)



def remove_slash_prefix(uri):
    if uri.startswith('/'):
        return uri[1:]
    else:
        return uri



__all__ = [
    Cached,
    load_module,
    check_permission_safety,
    get_private_key,
    SwaggerParser,
    remove_slash_prefix
]
