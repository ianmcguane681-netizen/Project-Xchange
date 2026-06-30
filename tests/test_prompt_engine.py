from components.comp_001_prompt_engine.prompt_engine import (
    approve_prompt,
    create_prompt,
    create_prompt_version,
    list_prompt_versions,
    rollback_prompt,
    run_prompt_test,
    search_prompts,
)
from project_exchange.database import init_db


def test_prompt_engine_create_approve_and_test(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    prompt = create_prompt(
        db_path,
        worker_id="PX-A001",
        prompt_type="System prompt",
        prompt_text="Audit research records and return JSON.",
    )
    assert prompt["status"] == "Draft"

    approved = approve_prompt(db_path, prompt["id"])
    assert approved["status"] == "Approved"

    result = run_prompt_test(db_path, prompt["id"], "Audit this maintenance complaint", "PX-A001")
    assert result["result"] == "pass"

    updated = create_prompt_version(db_path, prompt["id"], "New prompt text", "v1.0.1")
    assert updated["version"] == "v1.0.1"
    assert len(list_prompt_versions(db_path, prompt["id"])) == 2
    assert search_prompts(db_path, "new prompt")

    rolled_back = rollback_prompt(db_path, prompt["id"], "v1.0.0")
    assert rolled_back["version"] == "v1.0.0"
