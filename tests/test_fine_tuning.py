import os
import sys
import json
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_data():
    tmp = tempfile.mkdtemp()
    old_data = os.environ.get("AGENTE_DATA_DIR")
    os.environ["AGENTE_DATA_DIR"] = tmp
    yield tmp
    if old_data:
        os.environ["AGENTE_DATA_DIR"] = old_data
    else:
        del os.environ["AGENTE_DATA_DIR"]
    shutil.rmtree(tmp, ignore_errors=True)


class TestFineTuningPipeline:
    def test_import(self):
        from core.fine_tuning import FineTuningPipeline
        assert callable(FineTuningPipeline)

    def test_init(self):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        assert pipeline.datasets_dir is not None
        assert pipeline.models_dir is not None
        assert pipeline.evals_dir is not None

    def test_prepare_dataset_humaneval(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        path = pipeline.prepare_dataset("humaneval")
        assert os.path.exists(path)
        assert path.endswith(".jsonl")
        with open(path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_prepare_dataset_mbpp(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        path = pipeline.prepare_dataset("mbpp")
        assert os.path.exists(path)
        with open(path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_prepare_dataset_existing_code(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        path = pipeline.prepare_dataset("existing_code")
        assert os.path.exists(path)

    def test_prepare_dataset_from_file_jsonl(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        dataset_path = os.path.join(tmp_data, "test_dataset.jsonl")
        with open(dataset_path, "w") as f:
            f.write(json.dumps({"prompt": "test", "completion": "result"}) + "\n")
        pipeline = FineTuningPipeline()
        path = pipeline.prepare_dataset(dataset_path, "custom_test")
        assert os.path.exists(path)

    def test_prepare_dataset_invalid_source(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        with pytest.raises(ValueError):
            pipeline.prepare_dataset("invalid_source")

    def test_train_prompt_engineering(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        dataset_path = pipeline.prepare_dataset("humaneval")
        with patch("core.fine_tuning.FineTuningPipeline._evaluate_prompt_engineering") as mock_eval:
            mock_eval.return_value = {"accuracy": 0.5, "correct": 1, "total": 2}
            result = pipeline.train(dataset_path, "qwen2.5:7b", epochs=3, method="prompt_engineering")
            assert result["success"] is True
            assert result["method"] == "prompt_engineering"
            assert "adapter_path" in result

    def test_train_unknown_method(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        dataset_path = pipeline.prepare_dataset("humaneval")
        result = pipeline.train(dataset_path, "qwen2.5:7b", method="unknown")
        assert result["success"] is False

    def test_evaluate_humaneval(self, tmp_data):
        import sys
        import types
        mock_ollama = types.ModuleType("ollama")
        mock_ollama.chat = MagicMock()
        sys.modules["ollama"] = mock_ollama
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        with patch("core.llm._call_ollama_with_timeout") as mock_call:
            mock_call.return_value = {
                "message": {"content": "def has_close_elements(numbers, threshold):\n    sorted_numbers = sorted(numbers)\n    for i in range(len(sorted_numbers) - 1):\n        if sorted_numbers[i + 1] - sorted_numbers[i] < threshold:\n            return True\n    return False"}
            }
            result = pipeline.evaluate("qwen2.5:7b", "humaneval")
            assert result["benchmark"] == "humaneval"

    def test_evaluate_unknown_benchmark(self):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        result = pipeline.evaluate("test-model", "unknown_benchmark")
        assert "error" in result

    def test_deploy(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        result = pipeline.deploy("qwen2.5:7b")
        assert result["success"] is True
        assert result["status"] == "ready"

    def test_deploy_with_adapter(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        adapter_path = os.path.join(tmp_data, "adapter.json")
        with open(adapter_path, "w") as f:
            json.dump({"model": "qwen2.5:7b", "method": "prompt_engineering"}, f)
        pipeline = FineTuningPipeline()
        result = pipeline.deploy("qwen2.5:7b", adapter_path)
        assert result["success"] is True
        assert "adapter" in result

    def test_list_datasets(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        pipeline.prepare_dataset("humaneval")
        datasets = pipeline.list_datasets()
        assert len(datasets) > 0
        assert all(d.endswith(".jsonl") for d in datasets)

    def test_list_models(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        models = pipeline.list_models()
        assert isinstance(models, list)

    def test_training_history(self, tmp_data):
        from core.fine_tuning import FineTuningPipeline
        pipeline = FineTuningPipeline()
        prev_count = len(pipeline.get_training_history())
        result = {"success": True, "model": "test", "method": "prompt_engineering"}
        pipeline.save_training_result(result)
        history = pipeline.get_training_history()
        assert len(history) == prev_count + 1
        assert history[-1]["model"] == "test"
