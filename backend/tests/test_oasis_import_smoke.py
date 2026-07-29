"""The pinned CAMEL/OASIS runtime must be importable without network access."""


def test_camel_oasis_imports_with_compatible_mcp():
    import camel
    import oasis

    assert camel is not None
    assert callable(oasis.make)
