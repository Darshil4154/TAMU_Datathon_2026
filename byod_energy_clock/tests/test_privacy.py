from src.check import forbidden_name


def test_private_name_detection():
    assert forbidden_name("HELLO, Fake Person!", ["fake person"])
    assert not forbidden_name("A fake personality", ["fake person"])
