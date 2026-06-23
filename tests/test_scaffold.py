def test_pydantic_importable():
    import pydantic  # noqa: F401
    assert pydantic.VERSION.startswith("2")
