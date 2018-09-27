import getpass
import json
import logging

import os
import stat

from eth_utils import is_hex, decode_hex, encode_hex, remove_0x_prefix
import eth_keyfile

logger = logging.getLogger('dbot.' + os.path.splitext(os.path.basename(__file__))[0])


def check_permission_safety(path):
    """Check if the file at the given path is safe to use as a state file.

    This checks that group and others have no permissions on the file and that the current user is
    the owner.
    """
    f_stats = os.stat(path)
    return (f_stats.st_mode & (stat.S_IRWXG | stat.S_IRWXO)) == 0 and f_stats.st_uid == os.getuid()


def get_private_key(pk_file, pw_file=None):
    """Open a JSON-encoded private key and return it

    If a password file is provided, uses it to decrypt the key. If not, the
    password is asked interactively. Raw hex-encoded private keys are supported,
    but deprecated."""

    is_hex_key = is_hex(pk_file) and len(remove_0x_prefix(pk_file)) == 64
    is_path = os.path.exists(pk_file)
    assert is_hex_key or is_path, 'Private key must either be a hex key or a file path.'

    # Load private key from file if none is specified on command line.
    if is_path:
        private_key = load_pk(pk_file, pw_file)
        assert private_key is not None, 'Could not load private key from file.'
        return private_key
    else:
        # TODO make sure '0x'
        return pk_file


def load_pk(pk_file, pw_file=None):
    assert pk_file, pk_file
    if not os.path.exists(pk_file):
        logger.fatal("%s: no such file", pk_file)
        return None
    #  if not check_permission_safety(pk_file):
    #      logger.fatal("Private key file %s must be readable only by its owner.", pk_file)
    #      return None
    #
    #  if pw_file and not check_permission_safety(pw_file):
    #      logger.fatal("Password file %s must be readable only by its owner.", pw_file)
    #      return None

    with open(pk_file) as keyfile:
        private_key = keyfile.readline().strip()

        if is_hex(private_key) and len(decode_hex(private_key)) == 32:
            logger.warning("Private key in raw format. Consider switching to JSON-encoded")
        else:
            if pw_file:
                with open(pw_file) as password_file:
                    password = password_file.readline().strip()
            else:
                password = getpass.getpass("Enter the private key password: ")
            private_key = eth_keyfile.extract_key_from_keyfile(pk_file, password).hex()
    return private_key
