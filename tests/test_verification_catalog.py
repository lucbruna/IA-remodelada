import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


class TestVerificationCatalog:
    def test_import(self):
        from core.verification_catalog import verify_task, get_catalog_entry, list_catalog
        assert callable(verify_task)
        assert callable(get_catalog_entry)
        assert callable(list_catalog)

    def test_list_catalog(self):
        from core.verification_catalog import list_catalog
        catalog = list_catalog()
        assert "codigo" in catalog
        assert "arquivo" in catalog
        assert "web" in catalog
        assert "api" in catalog
        assert "dados" in catalog
        assert "sistema" in catalog

    def test_python_syntax_valid(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "valid.py")
        with open(filepath, "w") as f:
            f.write("x = 1\nprint(x)\n")
        result = verify_task("codigo", "python_syntax", filepath)
        assert result["passed"] is True

    def test_python_syntax_invalid(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "invalid.py")
        with open(filepath, "w") as f:
            f.write("x = 1\ny = ")
        result = verify_task("codigo", "python_syntax", filepath)
        assert result["passed"] is False

    def test_python_syntax_not_found(self):
        from core.verification_catalog import verify_task
        result = verify_task("codigo", "python_syntax", "/nonexistent/file.py")
        assert result["passed"] is False

    def test_python_imports(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "import_test.py")
        with open(filepath, "w") as f:
            f.write("import os\nimport sys\nimport json\n")
        result = verify_task("codigo", "python_imports", filepath)
        assert result["passed"] is True

    def test_python_imports_missing(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "missing_import.py")
        with open(filepath, "w") as f:
            f.write("import nonexistent_module_xyz\n")
        result = verify_task("codigo", "python_imports", filepath)
        assert result["passed"] is False

    def test_file_exists(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "exists.txt")
        with open(filepath, "w") as f:
            f.write("test")
        result = verify_task("arquivo", "exists", filepath)
        assert result["passed"] is True
        assert "size" in result

    def test_file_not_exists(self):
        from core.verification_catalog import verify_task
        result = verify_task("arquivo", "exists", "/nonexistent/file.txt")
        assert result["passed"] is False

    def test_file_hash(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "hash_test.txt")
        with open(filepath, "w") as f:
            f.write("test content")
        result = verify_task("arquivo", "hash", filepath)
        assert result["passed"] is True
        assert "hash" in result

    def test_file_hash_with_expected(self, tmp_dir):
        from core.verification_catalog import verify_task
        import hashlib
        filepath = os.path.join(tmp_dir, "hash_expected.txt")
        with open(filepath, "w") as f:
            f.write("test content")
        expected = hashlib.sha256(b"test content").hexdigest()
        result = verify_task("arquivo", "hash", filepath, expected)
        assert result["passed"] is True
        assert result["hash"] == expected

    def test_file_size_within_limit(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "small.txt")
        with open(filepath, "w") as f:
            f.write("small")
        result = verify_task("arquivo", "size", filepath, 1)
        assert result["passed"] is True

    def test_file_size_exceeds_limit(self, tmp_dir):
        from core.verification_catalog import verify_task
        filepath = os.path.join(tmp_dir, "large.txt")
        with open(filepath, "w") as f:
            f.write("a" * 1024 * 1024 * 5)
        result = verify_task("arquivo", "size", filepath, 1)
        assert result["passed"] is False

    def test_json_schema_valid(self):
        from core.verification_catalog import verify_task
        data = {"name": "test", "value": 42}
        result = verify_task("api", "json_schema", data, ["name", "value"])
        assert result["passed"] is True

    def test_json_schema_missing_keys(self):
        from core.verification_catalog import verify_task
        data = {"name": "test"}
        result = verify_task("api", "json_schema", data, ["name", "value"])
        assert result["passed"] is False
        assert "value" in result.get("missing", [])

    def test_json_schema_not_dict(self):
        from core.verification_catalog import verify_task
        result = verify_task("api", "json_schema", [1, 2, 3], ["key"])
        assert result["passed"] is False

    def test_unknown_verification(self):
        from core.verification_catalog import verify_task
        result = verify_task("unknown", "nonexistent")
        assert result["passed"] is False
        assert "KeyError" in result.get("error", "")

    def test_verify_all_for_task_python(self, tmp_dir):
        from core.verification_catalog import verify_all_for_task
        filepath = os.path.join(tmp_dir, "task_test.py")
        with open(filepath, "w") as f:
            f.write("x = 1\n")
        results = verify_all_for_task("python_file", filepath)
        assert len(results) > 0
        assert any(r.get("passed", False) for r in results if r.get("name") == "exists")

    def test_run_preflight_check(self, tmp_dir):
        from core.verification_catalog import run_preflight_check
        filepath = os.path.join(tmp_dir, "preflight.py")
        with open(filepath, "w") as f:
            f.write("x = 1\n")
        result = run_preflight_check(filepath, "python_file")
        assert "passed" in result
        assert "total_checks" in result

    def test_get_catalog_entry(self):
        from core.verification_catalog import get_catalog_entry
        func = get_catalog_entry("codigo", "python_syntax")
        assert func is not None
        assert callable(func)

    def test_get_catalog_entry_nonexistent(self):
        from core.verification_catalog import get_catalog_entry
        func = get_catalog_entry("nonexistent", "nonexistent")
        assert func is None

    def test_save_and_load_result(self, tmp_dir):
        from core.verification_catalog import save_verification_result, load_verification_result
        with patch("core.verification_catalog.VERIFICATION_DIR", tmp_dir):
            save_verification_result("test_task", {"passed": True, "details": "ok"})
            loaded = load_verification_result("test_task")
            assert loaded is not None
            assert loaded["passed"] is True
