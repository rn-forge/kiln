from golden_tool import greet


def test_greet_names_the_caller():
    assert greet("world") == "Hello, world!"


def test_greet_merges_overrides_over_the_defaults():
    assert greet("world", greeting="Hi", punctuation="?") == "Hi, world?"
