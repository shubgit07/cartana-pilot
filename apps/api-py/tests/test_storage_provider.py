"""Unit tests for the local StorageProvider implementation."""
from __future__ import annotations

import pytest

from app.providers.storage_provider import (
    LocalStorageProvider,
    build_storage_key,
    safe_filename,
)


def test_safe_filename():
    assert safe_filename("simple.pdf") == "simple.pdf"
    assert safe_filename("C:\\Users\\user\\Documents\\my_spec.md") == "my_spec.md"
    assert safe_filename("/var/uploads/test.txt") == "test.txt"
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("file with spaces & symbols!.doc") == "file_with_spaces___symbols_.doc"


def test_build_storage_key():
    key = build_storage_key("proj-123", "spec.pdf")
    assert key.startswith("projects/proj-123/")
    assert key.endswith("-spec.pdf")


def test_local_storage_provider(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    key = "projects/test/123-doc.txt"
    data = b"Hello local storage!"

    saved_key = provider.save(key, data)
    assert saved_key == key

    read_data = provider.read(key)
    assert read_data == data

    provider.remove(key)
    with pytest.raises(FileNotFoundError):
        provider.read(key)

    # Removing missing key should be a no-op (no error)
    provider.remove(key)


def test_local_remove_prefix_deletes_project_tree_only(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    provider.save("projects/proj-a/1-a.txt", b"a")
    provider.save("projects/proj-a/2-b.txt", b"b")
    provider.save("projects/proj-b/1-c.txt", b"c")

    provider.remove_prefix("projects/proj-a/")

    assert provider.read("projects/proj-b/1-c.txt") == b"c"
    with pytest.raises(FileNotFoundError):
        provider.read("projects/proj-a/1-a.txt")

    # Missing prefix is a no-op
    provider.remove_prefix("projects/does-not-exist/")


def test_local_remove_prefix_refuses_storage_root(tmp_path):
    provider = LocalStorageProvider(root=tmp_path)
    with pytest.raises(ValueError):
        provider.remove_prefix("./")
