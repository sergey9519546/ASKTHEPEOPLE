"""The pinned CAMEL/OASIS runtime must be importable without network access.

Note: This test is skipped if camel/oasis modules are not installed,
as they are optional dependencies for simulation runtime only.
"""

import pytest


def test_camel_oasis_imports_with_compatible_mcp():
    pytest.importorskip("camel", reason="camel-ai not installed (optional dependency)")
    pytest.importorskip("oasis", reason="oasis-ai not installed (optional dependency)")
    
    import camel
    import oasis

    assert camel is not None
    assert callable(oasis.make)
