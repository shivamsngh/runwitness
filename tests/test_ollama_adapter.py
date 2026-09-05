import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "examples" / "docubench" / "ollama_subset.py"
SPEC = importlib.util.spec_from_file_location("fieldkit_ollama_subset", MODULE_PATH)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


class OllamaAdapterTests(unittest.TestCase):
    def test_model_identity_records_digest_and_capabilities(self):
        def fake_api(_base, route, _payload=None):
            if route == "/api/show":
                return {"details": {"parameter_size": "8.9B"}, "capabilities": ["vision"]}
            return {"models": [{"name": "ministral-3:latest", "digest": "abc123"}]}

        with patch.object(ADAPTER, "api", side_effect=fake_api):
            identity = ADAPTER.model_identity("http://local", "ministral-3:latest")
        self.assertEqual(identity["digest"], "abc123")
        self.assertEqual(identity["capabilities"], ["vision"])

    def test_text_run_writes_docubench_shaped_data_and_runtime_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            for name in ("documents", "schemas", "prompts", "guidelines"):
                (repo / name).mkdir()
            (repo / "documents" / "sample.txt").write_text("Invoice number 42", encoding="utf-8")
            (repo / "schemas" / "sample.json").write_text(json.dumps({
                "type": "object", "properties": {"invoice": {"type": "string"}}
            }), encoding="utf-8")
            (repo / "prompts" / "extraction_prompt.txt").write_text("Extract {doc_id}", encoding="utf-8")

            def fake_api(_base, route, _payload=None):
                if route == "/api/chat":
                    return {"message": {"content": '{"invoice":"42"}'}, "eval_count": 4}
                if route == "/api/ps":
                    return {"models": [{"name": "phi3.5:latest", "size": 10, "size_vram": 8}]}
                raise AssertionError(route)

            identity = {"tag": "phi3.5:latest", "digest": "digest"}
            with patch.object(ADAPTER, "api", side_effect=fake_api):
                result = ADAPTER.run_model(repo, "http://local", "phi3.5:latest", "text",
                                           "sample", 1, identity)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["data"], {"invoice": "42"})
            self.assertEqual(result["meta"]["ollama_runtime"]["vram_bytes"], 8)
            self.assertIn("not host peak RSS", result["meta"]["ollama_runtime"]["scope"])


if __name__ == "__main__":
    unittest.main()
