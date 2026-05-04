def test_imports():
    import function_app
    assert hasattr(function_app, "app")
