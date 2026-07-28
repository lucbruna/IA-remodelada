import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestModelManager:
    def test_import(self):
        from core.model_manager import (
            detect_system, recommend_model, list_available_models,
            get_model_info, benchmark_model, get_system_recommendation,
        )
        assert callable(detect_system)
        assert callable(recommend_model)
        assert callable(list_available_models)
        assert callable(get_model_info)
        assert callable(benchmark_model)
        assert callable(get_system_recommendation)

    def test_list_available_models(self):
        from core.model_manager import list_available_models
        models = list_available_models()
        assert len(models) > 0
        names = [m["name"] for m in models]
        assert "qwen2.5:7b" in names
        assert "qwen2.5:32b" in names
        assert "llava" in names
        assert "nomic-embed-text" in names

    def test_get_model_info_found(self):
        from core.model_manager import get_model_info
        info = get_model_info("qwen2.5:7b")
        assert info is not None
        assert info["name"] == "qwen2.5:7b"
        assert "quality" in info
        assert "size_gb" in info

    def test_get_model_info_not_found(self):
        from core.model_manager import get_model_info
        info = get_model_info("nonexistent:999b")
        assert info is None

    def test_detect_system(self):
        from core.model_manager import detect_system
        with patch("core.model_manager._get_ram_gb", return_value=32):
            with patch("core.model_manager._get_vram_gb", return_value=0):
                with patch("core.model_manager._check_ollama_health", return_value=(True, "ok")):
                    system = detect_system()
                    assert system["ram_gb"] == 32
                    assert system["vram_gb"] == 0
                    assert system["tier"] == "medium"

    def test_detect_system_large(self):
        from core.model_manager import detect_system
        with patch("core.model_manager._get_ram_gb", return_value=64):
            with patch("core.model_manager._get_vram_gb", return_value=48):
                with patch("core.model_manager._check_ollama_health", return_value=(True, "ok")):
                    system = detect_system()
                    assert system["tier"] == "large"

    def test_recommend_model_small(self):
        from core.model_manager import recommend_model
        with patch("core.model_manager.detect_system") as mock_detect:
            mock_detect.return_value = {
                "ram_gb": 8, "vram_gb": 0, "has_gpu": False,
                "tier": "small", "ollama_health": True, "ollama_message": "ok",
                "platform": "win32",
            }
            with patch("core.model_manager._get_ollama_models", return_value=[]):
                rec = recommend_model("text")
                assert rec["recommended"]["name"] == "qwen2.5:7b"

    def test_recommend_model_medium(self):
        from core.model_manager import recommend_model
        with patch("core.model_manager.detect_system") as mock_detect:
            mock_detect.return_value = {
                "ram_gb": 24, "vram_gb": 16, "has_gpu": True,
                "tier": "medium", "ollama_health": True, "ollama_message": "ok",
                "platform": "win32",
            }
            with patch("core.model_manager._get_ollama_models", return_value=[]):
                rec = recommend_model("text")
                assert rec["recommended"]["name"] == "qwen2.5:32b"

    def test_recommend_vision(self):
        from core.model_manager import recommend_model
        with patch("core.model_manager._get_ollama_models", return_value=[]):
            rec = recommend_model("vision")
            assert rec["task_type"] == "vision"
            assert rec["recommended"]["type"] == "vision"

    def test_recommend_embedding(self):
        from core.model_manager import recommend_model
        with patch("core.model_manager._get_ollama_models", return_value=[]):
            rec = recommend_model("embedding")
            assert rec["task_type"] == "embedding"
            assert rec["recommended"]["type"] == "embedding"

    def test_recommend_already_installed(self):
        from core.model_manager import recommend_model
        with patch("core.model_manager.detect_system") as mock_detect:
            mock_detect.return_value = {
                "ram_gb": 8, "vram_gb": 0, "has_gpu": False,
                "tier": "small", "ollama_health": True, "ollama_message": "ok",
                "platform": "win32",
            }
            with patch("core.model_manager._get_ollama_models", return_value=[
                {"name": "gemma4:E4B", "size_gb": 3.8, "modified": ""}
            ]):
                rec = recommend_model("text")
                assert rec["already_have"] is True
                assert rec["recommended"]["name"] == "gemma4:E4B"

    def test_benchmark_model_error(self):
        from core.model_manager import benchmark_model
        with patch("core.llm._call_ollama_with_timeout", side_effect=Exception("ollama not available")):
            result = benchmark_model("qwen2.5:7b", quick=True)
            assert "error" in result or result.get("summary", {}).get("successful", 0) == 0

    def test_get_system_recommendation(self):
        from core.model_manager import get_system_recommendation
        with patch("core.model_manager.detect_system") as mock_detect:
            mock_detect.return_value = {
                "ram_gb": 16, "vram_gb": 0, "has_gpu": False,
                "tier": "medium", "ollama_health": True, "ollama_message": "ok",
                "platform": "win32",
            }
            with patch("core.model_manager._get_ollama_models", return_value=[]):
                rec = get_system_recommendation()
                assert "recommended_model" in rec
                assert "system" in rec
                assert "message" in rec

    def test_set_default_model(self):
        from core.model_manager import set_default_model
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = ["AGENTE_MODEL=old\n"]
            result = set_default_model("qwen2.5:32b")
            assert "success" in result


class TestModelTools:
    def test_import(self):
        from core.model_tools import (
            model_detect, model_recommend, model_list,
            model_info, model_download, model_benchmark, model_switch,
        )
        assert callable(model_detect)
        assert callable(model_recommend)
        assert callable(model_list)
        assert callable(model_info)
        assert callable(model_download)
        assert callable(model_benchmark)
        assert callable(model_switch)

    def test_model_detect(self):
        from core.model_tools import model_detect
        with patch("core.model_tools._detect_system") as mock_detect:
            mock_detect.return_value = {
                "ram_gb": 16, "vram_gb": 0, "has_gpu": False,
                "tier": "medium", "ollama_health": True,
                "ollama_message": "ok", "platform": "win32",
            }
            result = model_detect()
            assert "RAM:" in result
            assert "16GB" in result

    def test_model_recommend(self):
        from core.model_tools import model_recommend
        with patch("core.model_tools._recommend_model") as mock_rec:
            mock_rec.return_value = {
                "system": {"ram_gb": 16, "vram_gb": 0, "tier": "medium"},
                "recommended": {"name": "qwen2.5:32b", "quality": "alto", "size_gb": 19, "ctx": 32768},
                "already_have": False,
            }
            result = model_recommend("text")
            assert "qwen2.5:32b" in result

    def test_model_list(self):
        from core.model_tools import model_list
        with patch("core.model_manager._get_ollama_models", return_value=[
            {"name": "qwen2.5:7b", "size_gb": 4.5, "modified": ""}
        ]):
            with patch("core.model_manager.list_available_models") as mock_cat:
                mock_cat.return_value = [
                    {"name": "qwen2.5:7b", "tier": "small", "quality": "medio", "ctx": 32768},
                    {"name": "qwen2.5:32b", "tier": "medium", "quality": "alto", "ctx": 32768},
                ]
                result = model_list()
                assert "qwen2.5:7b" in result
                assert "qwen2.5:32b" in result

    def test_model_info(self):
        from core.model_tools import model_info
        with patch("core.model_manager.get_model_info") as mock_info:
            mock_info.return_value = {
                "name": "qwen2.5:7b", "type": "text", "quality": "medio",
                "size_gb": 4.5, "ctx": 32768, "tier": "small",
            }
            result = model_info("qwen2.5:7b")
            assert "qwen2.5:7b" in result

    def test_model_info_not_found(self):
        from core.model_tools import model_info
        with patch("core.model_manager.get_model_info", return_value=None):
            with patch("core.model_manager._get_ollama_models", return_value=[]):
                result = model_info("nonexistent:999b")
                assert "nao encontrado" in result

    def test_model_download(self):
        from core.model_tools import model_download
        with patch("core.model_manager.download_model") as mock_dl:
            mock_dl.return_value = {"success": True, "model": "qwen2.5:7b"}
            result = model_download("qwen2.5:7b")
            assert "concluido" in result.lower()

    def test_model_download_error(self):
        from core.model_tools import model_download
        with patch("core.model_tools._download_model") as mock_dl:
            mock_dl.return_value = {"success": False, "error": "not found"}
            result = model_download("nonexistent:999b")
            assert "erro" in result.lower()

    def test_model_switch(self):
        from core.model_tools import model_switch
        with patch("core.model_manager.set_default_model") as mock_sw:
            mock_sw.return_value = {"success": True, "model": "qwen2.5:32b"}
            result = model_switch("qwen2.5:32b")
            assert "alterado" in result.lower()
