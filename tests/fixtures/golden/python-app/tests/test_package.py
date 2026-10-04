import golden_app


def test_package_imports():
    assert golden_app.__spec__ is not None
