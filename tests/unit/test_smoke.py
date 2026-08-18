import juicebox


def test_package_exposes_version():
    assert juicebox.__version__ == "0.1.0"
