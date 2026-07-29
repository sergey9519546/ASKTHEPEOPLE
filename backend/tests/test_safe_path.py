"""
Unit tests for the path-traversal defense helper `safe_join`.

These tests are pure (no Flask) and cover the documented defense layers:
empty/None rejection, secure_filename mangle detection, realpath/commonpath
containment, and symlink-escape rejection.
"""

import os
import tempfile

import pytest

from app.utils.safe_path import safe_join, SafePathError


@pytest.fixture
def base_dir():
    """A fresh temporary base directory for each test."""
    d = tempfile.mkdtemp(prefix="safejoin_test_")
    yield d


def test_legit_uuid_like_id_returns_path_under_base(base_dir):
    """Realistic ids (sim_<hex>, report_<hex>, uuid with hyphens) survive unchanged."""
    for legit in ("sim_aabbccddeeff", "report_1234567890ab", "abc123-def456"):
        result = safe_join(base_dir, legit)
        assert result == os.path.realpath(os.path.join(base_dir, legit))
        assert os.path.basename(result) == legit
        assert result.startswith(os.path.realpath(base_dir))


def test_relative_traversal_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, "../etc/passwd")


def test_nested_relative_traversal_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, "../../etc/passwd")


def test_absolute_path_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, "/etc/passwd")


def test_windows_absolute_path_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, r"C:\Windows\System32")


def test_empty_string_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, "")


def test_none_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, None)


def test_null_byte_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, "foo\u0000bar")


def test_path_separator_in_id_rejected(base_dir):
    # Forward slash makes secure_filename collapse/strip -> mangled -> rejected.
    with pytest.raises(SafePathError):
        safe_join(base_dir, "a/b")


def test_dotdot_only_rejected(base_dir):
    with pytest.raises(SafePathError):
        safe_join(base_dir, "..")


def test_symlink_escape_rejected(base_dir):
    """A symlink inside base that points outside base must be rejected.

    `realpath` resolves the symlink, and commonpath then sees the target is
    outside base -> SafePathError.
    """
    # Symlink creation typically requires elevated privileges on Windows.
    if os.name == "nt":
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                pytest.skip("creating symlinks on Windows requires admin privileges")
        except OSError:
            pytest.skip("cannot determine admin status on Windows")

    outside = tempfile.mkdtemp(prefix="safejoin_outside_")
    link_name = "evil_link"
    link_path = os.path.join(base_dir, link_name)
    target = os.path.join(outside, "secret.txt")
    try:
        os.symlink(outside, link_path)
        with open(target, "w", encoding="utf-8") as f:
            f.write("secret")
        with pytest.raises(SafePathError):
            safe_join(base_dir, link_name)
    finally:
        if os.path.islink(link_path) or os.path.exists(link_path):
            try:
                os.remove(link_path)
            except OSError:
                pass
        if os.path.exists(target):
            os.remove(target)
        if os.path.exists(outside):
            os.rmdir(outside)


def test_target_stays_under_base_canonicalization(base_dir):
    """A legit id that exists as a real subdir is resolved and stays under base."""
    real_subdir = "real_sim_dir"
    os.mkdir(os.path.join(base_dir, real_subdir))
    result = safe_join(base_dir, real_subdir)
    assert result == os.path.realpath(os.path.join(base_dir, real_subdir))
