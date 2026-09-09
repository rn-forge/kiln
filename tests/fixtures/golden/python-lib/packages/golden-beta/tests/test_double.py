from golden_beta import scale


def test_scale_doubles_by_default():
    assert scale(21) == 42


def test_scale_honours_an_override():
    assert scale(21, factor=3) == 63
