import pytest

from agent_debugger.scenario.vfs import (
    MAX_FILE_BYTES,
    PathViolation,
    VirtualFileSystem,
    normalize_path,
)


class TestNormalizePath:
    def test_simple(self):
        assert normalize_path("src/app.py") == "src/app.py"

    def test_backslashes_and_dots(self):
        assert normalize_path("src\\.\\app.py") == "src/app.py"

    @pytest.mark.parametrize(
        "bad",
        ["../etc/passwd", "src/../../x", "/etc/passwd", "C:\\Windows\\system32", "~/секрет", "a\x00b", ""],
    )
    def test_rejects_unsafe(self, bad):
        with pytest.raises(PathViolation):
            normalize_path(bad)

    def test_violation_attributed_to_agent(self):
        try:
            normalize_path("../x")
        except PathViolation as exc:
            assert exc.actor == "agent"


class TestVfs:
    def test_write_read_delete(self):
        vfs = VirtualFileSystem({"a.txt": "hello"})
        assert vfs.read("a.txt") == "hello"
        vfs.write("b/c.txt", "world")
        assert vfs.exists("b/c.txt")
        vfs.delete("a.txt")
        assert not vfs.exists("a.txt")

    def test_read_missing_raises(self):
        with pytest.raises(FileNotFoundError):
            VirtualFileSystem().read("nope.txt")

    def test_list_dir(self):
        vfs = VirtualFileSystem({"src/a.py": "", "src/sub/b.py": "", "top.md": "x"})
        names = {e["name"]: e["type"] for e in vfs.list_dir(".")}
        assert names == {"src": "dir", "top.md": "file"}
        assert {e["name"] for e in vfs.list_dir("src")} == {"a.py", "sub"}

    def test_search_plain_and_regex(self):
        vfs = VirtualFileSystem({"a.py": "alpha\nbeta secret", "b.md": "beta"})
        assert len(vfs.search("beta")) == 2
        assert vfs.search("beta", glob="*.py")[0]["path"] == "a.py"
        assert vfs.search(r"^al", regex=True)[0]["line"] == 1

    def test_size_limit(self):
        vfs = VirtualFileSystem()
        with pytest.raises(PathViolation):
            vfs.write("big.txt", "x" * (MAX_FILE_BYTES + 1))

    def test_digests_stable(self):
        files = {"a": "1", "b": "2"}
        assert VirtualFileSystem(files).digests() == VirtualFileSystem(dict(files)).digests()
