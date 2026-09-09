from golden_alpha import first


def test_first_returns_the_head():
    assert first([2, 3]) == 2


def test_first_of_nothing_is_the_default():
    assert first([], default=7) == 7
