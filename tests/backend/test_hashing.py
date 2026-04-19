from visavoice.backend.hashing import hash_caller

def test_deterministic():
    assert hash_caller("+12175550199", "salt") == hash_caller("+12175550199", "salt")

def test_salt_changes_output():
    assert hash_caller("+12175550199", "a") != hash_caller("+12175550199", "b")

def test_empty_number_allowed():
    assert hash_caller("", "salt") != ""
