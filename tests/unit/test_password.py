from utils.password import hash_password, verify_password


def test_password_hash_and_verify():
    password = "TestPassword123!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password) is True
    assert verify_password("WrongPassword123!", hashed_password) is False
    