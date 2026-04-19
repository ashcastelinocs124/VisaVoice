import hashlib


def hash_caller(caller_number: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}|{caller_number}".encode()).hexdigest()
