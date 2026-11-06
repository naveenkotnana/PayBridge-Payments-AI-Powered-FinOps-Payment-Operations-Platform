"""Structured model output must request JSON mode and degrade safely."""
from app.rag import ollama_client


def test_model_requests_json_output(monkeypatch):
    captured = {}
    monkeypatch.setattr(ollama_client, "resolve_model", lambda: "test-model")
    def post(path, payload, timeout):
        captured.update(payload)
        return {"response": '{"what_happened":"Evidence available"}'}
    monkeypatch.setattr(ollama_client, "_post", post)
    result, parsed = ollama_client.generate_json("Explain evidence")
    assert result.ok
    assert parsed["what_happened"] == "Evidence available"
    assert captured["format"] == "json"


def test_truncated_model_output_is_not_presented_as_ai_result(monkeypatch):
    monkeypatch.setattr(ollama_client, "resolve_model", lambda: "test-model")
    monkeypatch.setattr(ollama_client, "_post", lambda *args: {"response": '{"what_happened":'})
    result, parsed = ollama_client.generate_json("Explain evidence")
    assert result.ok
    assert parsed is None
