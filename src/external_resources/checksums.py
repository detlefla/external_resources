from hashlib import sha256, sha384
from typing import Final, Literal


ALGO_SHA256: Final = "sha256"  # only sensible way to make mypy happy
ALGO_SHA384: Final = "sha384"
ALGO_LIST: Final[list[Literal["sha256", "sha384"]]] = [
        ALGO_SHA256, ALGO_SHA384]


def get_checksum(
        data: bytes,
        *,
        algo: Literal["sha256", "sha384"] = ALGO_SHA384,
        ) -> str:
    """
    Calculates the hash of a byte string and returns it (with an algorithm id).
    """
    if algo == ALGO_SHA256:
        return f"sha256:{sha256(data).hexdigest()}"
    elif algo == ALGO_SHA384:
        return f"sha384:{sha384(data).hexdigest()}"
    else:
        raise ValueError(f"unsupported checksum algorithm “{algo}”")


def verify_checksum(
        data: bytes,
        hash: str,
        ) -> bool:
    """
    Verifies that the hash of a byte string agrees with a given value.
    
    The hash is always prefixed with an algorith id.
    Currently only sha256 is supported.
    """
    for algo in ALGO_LIST:
        if hash.startswith(f"{algo}:") or hash.startswith(f"{algo}-"):
            pfx_len = len(algo) + 1
            ref = get_checksum(data, algo=algo)
            return hash[pfx_len:] == ref
    return False
