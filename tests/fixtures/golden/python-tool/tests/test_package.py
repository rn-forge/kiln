import golden_tool


def test_package_imports():
    assert golden_tool.__spec__ is not None
