from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

import pytest

from iios_mvp.chatgpt_chat_handoff_v01 import (
    ChatGPTChatHandoffError,
    ChatGPTChatHandoffRequired,
    ChatGPTChatJsonClient,
    import_chatgpt_response,
)
from iios_mvp.chatgpt_chat_runtime_v01 import (
    ChatGPTChatRequestInterpreter,
    build_chatgpt_chat_runtime,
)
from iios_mvp.canonical_runtime_factory_v01 import RuntimeCaseContext
from iios_mvp.canonical_runtime_registry_v01 import validate_canonical_runtime_bindings


def _task_context():
    return {
        "prompt": 'Return only JSON: {"ok":true,"count":2}',
        "run_id": "run-chatgpt-contract-001",
        "request_id": "request-chatgpt-contract-001",
        "case_id": "RC-CN-A-TEST-20261010",
        "cutoff_date": "2026-10-10",
        "stage": "request-intent",
    }


def _save_response(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_client_creates_immutable_prompt_and_blocks_until_operator_imports_response(tmp_path):
    root = tmp_path / ".iios-chatgpt-handoff"
    client = ChatGPTChatJsonClient(root=root)
    values = _task_context()
    with pytest.raises(ChatGPTChatHandoffRequired) as caught:
        client.generate_json(**values)
    task_id = caught.value.task_id
    prompt_file = root / "requests" / f"{task_id}.prompt.txt"
    request_file = root / "requests" / f"{task_id}.json"
    assert prompt_file.read_text(encoding="utf-8") == values["prompt"]
    assert request_file.is_file()
    assert stat.S_IMODE(prompt_file.stat().st_mode) == 0o600
    task = json.loads(request_file.read_text(encoding="utf-8"))
    assert task["prompt_sha256"] == hashlib.sha256(values["prompt"].encode()).hexdigest()
    assert task["provider_origin_verified"] is False
    assert not (root / "responses" / f"{task_id}.json").exists()


def test_import_and_replay_exact_response_is_bound_to_prompt_run_case_and_stage(tmp_path):
    root = tmp_path / "handoff"
    client = ChatGPTChatJsonClient(root=root)
    values = _task_context()
    with pytest.raises(ChatGPTChatHandoffRequired) as caught:
        client.generate_json(**values)
    task_id = caught.value.task_id
    response_file = _save_response(tmp_path / "chatgpt-response.txt", '{"ok":true,"count":2}')
    imported = import_chatgpt_response(root=root, task_id=task_id, response_file=response_file)
    assert imported["status"] == "IMPORTED_NOT_PROVIDER_AUTHENTICATED"
    assert imported["provider_origin_verified"] is False
    response = client.generate_json(**values)
    assert response == {"ok": True, "count": 2}
    receipt = json.loads(Path(imported["receipt_file"]).read_text(encoding="utf-8"))
    assert receipt["prompt_sha256"] == hashlib.sha256(values["prompt"].encode()).hexdigest()
    assert receipt["response_sha256"] == hashlib.sha256(response_file.read_bytes()).hexdigest()
    assert receipt["provider_origin_verified"] is False
    assert receipt["integrity_semantics"] == "HASH_INTEGRITY_ONLY_NOT_PROVIDER_AUTHENTICATION"


def test_wrong_prompt_does_not_reuse_previous_chatgpt_response(tmp_path):
    root = tmp_path / "handoff"
    client = ChatGPTChatJsonClient(root=root)
    values = _task_context()
    with pytest.raises(ChatGPTChatHandoffRequired) as first:
        client.generate_json(**values)
    response_file = _save_response(tmp_path / "response.json", '{"ok":true,"count":2}')
    import_chatgpt_response(root=root, task_id=first.value.task_id, response_file=response_file)
    different = {**values, "prompt": 'Return only JSON: {"ok":false,"count":0}'}
    with pytest.raises(ChatGPTChatHandoffRequired) as second:
        client.generate_json(**different)
    assert first.value.task_id != second.value.task_id


def test_import_rejects_markdown_wrapped_json_and_duplicate_keys(tmp_path):
    root = tmp_path / "handoff"
    client = ChatGPTChatJsonClient(root=root)
    with pytest.raises(ChatGPTChatHandoffRequired) as caught:
        client.generate_json(**_task_context())
    task_id = caught.value.task_id
    markdown = chr(96) * 3 + 'json\n{"ok":true}\n' + chr(96) * 3
    bad_md = _save_response(tmp_path / "markdown.txt", markdown)
    with pytest.raises(ChatGPTChatHandoffError, match="STRICT_JSON"):
        import_chatgpt_response(root=root, task_id=task_id, response_file=bad_md)
    duplicate = _save_response(tmp_path / "duplicate.txt", '{"ok":true,"ok":false}')
    with pytest.raises(ChatGPTChatHandoffError, match="DUPLICATE_JSON_KEY"):
        import_chatgpt_response(root=root, task_id=task_id, response_file=duplicate)


def test_reimport_is_idempotent_for_same_exact_response_only(tmp_path):
    root = tmp_path / "handoff"
    client = ChatGPTChatJsonClient(root=root)
    with pytest.raises(ChatGPTChatHandoffRequired) as caught:
        client.generate_json(**_task_context())
    task_id = caught.value.task_id
    same = _save_response(tmp_path / "one.json", '{"ok":true,"count":2}')
    result1 = import_chatgpt_response(root=root, task_id=task_id, response_file=same)
    result2 = import_chatgpt_response(root=root, task_id=task_id, response_file=same)
    assert result1["status"] == "IMPORTED_NOT_PROVIDER_AUTHENTICATED"
    assert result2["status"] == "ALREADY_IMPORTED"
    other = _save_response(tmp_path / "two.json", '{"ok":false,"count":2}')
    with pytest.raises(ChatGPTChatHandoffError, match="IMMUTABLE_COLLISION"):
        import_chatgpt_response(root=root, task_id=task_id, response_file=other)


def _bundle():
    return {
        "raw_request": "Assess CATL as of 2026-10-10.",
        "request_id": "chatgpt-factory-request-001",
        "run_id": "chatgpt-factory-run-001",
        "company": "CATL",
        "investment_case": {
            "case_id": "RC-CN-A-300750-20261010",
            "market": "CN-A",
            "symbol": "300750",
            "company": "CATL",
            "as_of_date": "2026-10-10",
            "cutoff_date": "2026-10-10",
        },
        "evidence_manifest_path": "/not-read-by-factory/manifest.json",
        "evidence_root": "/not-read-by-factory/raw",
        "artifact_type": "THESIS_ASSESSMENT",
        "semantic_prompt": "Use only admitted evidence; identify thesis mechanism, drivers and falsifiers.",
        "decision_relevance": "Proposal only; never provide an investment action.",
    }


def test_chatgpt_runtime_factory_needs_no_provider_endpoint_or_api_key(tmp_path):
    admission_root = tmp_path / "admissions"
    admission_root.mkdir()
    output_root = tmp_path / "out"
    output_root.mkdir()
    handoff_root = tmp_path / "handoff"
    values = {
        "IIOS_CANONICAL_ADMISSION_ROOT": str(admission_root),
        "IIOS_CHATGPT_HANDOFF_ROOT": str(handoff_root),
    }
    runtime = build_chatgpt_chat_runtime(bundle=_bundle(), output_root=output_root, env=values)
    assert validate_canonical_runtime_bindings(runtime) is runtime
    assert runtime.request_interpreter.interpreter_id == "iios-chatgpt-web-request-interpreter"
    assert runtime.semantic_producer.producer_id == "iios-chatgpt-web-semantic-producer"
    with pytest.raises(ChatGPTChatHandoffRequired):
        runtime.request_interpreter.interpret(_bundle()["raw_request"])
    assert list((handoff_root / "requests").glob("*.prompt.txt"))


def test_operator_response_can_feed_the_real_request_interpreter_contract(tmp_path):
    root = tmp_path / "handoff"
    client = ChatGPTChatJsonClient(root=root)
    context = RuntimeCaseContext(
        case_id="RC-CN-A-300750-20261010",
        market="CN-A",
        symbol="300750",
        company="CATL",
        cutoff_date="2026-10-10",
        run_id="run-1",
        request_id="request-1",
    )
    interpreter = ChatGPTChatRequestInterpreter(client=client, context=context)
    raw_request = "请分析300750，截止2026-10-10"
    with pytest.raises(ChatGPTChatHandoffRequired) as caught:
        interpreter.interpret(raw_request)
    response = {
        "market": "CN-A",
        "symbol": "300750",
        "as_of_date": "2026-10-10",
        "current_position_pct": "0",
        "request_type": "INVESTMENT_DECISION",
    }
    response_file = tmp_path / "intent.json"
    response_file.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
    import_chatgpt_response(root=root, task_id=caught.value.task_id, response_file=response_file)
    result = interpreter.interpret(raw_request)
    assert result.symbol == "300750"
    assert result.as_of_date == "2026-10-10"
