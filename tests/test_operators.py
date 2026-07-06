from __future__ import annotations

from project_exchange.database import init_db
from project_exchange.operators import operator_definitions, provena_operator_registry, validate_operator_contracts


def test_operator_definitions_are_real_system_functions():
    operators = operator_definitions()

    assert operators
    for operator in operators:
        assert operator["operator_id"].startswith("PX-")
        assert operator["operator_name"].endswith("Operator")
        assert operator["backend_module"]
        assert operator["backend_function"]
        assert operator["status_source"]
        assert operator["input_contract"]
        assert operator["output_contract"]
        assert operator["activity_table"] == "worker_activity"


def test_operator_contracts_resolve_to_callable_functions():
    checks = validate_operator_contracts()

    assert checks
    assert all(check["status"] == "pass" for check in checks)


def test_provena_operator_registry_includes_runtime_status_and_traceability(tmp_path):
    db_path = tmp_path / "px.db"
    init_db(db_path)

    operators = provena_operator_registry(db_path)

    assert {operator["operator_id"] for operator in operators} == {"PX-H001", "PX-R001", "PX-A001", "PX-L001"}
    for operator in operators:
        assert operator["status"]
        assert operator["input"]
        assert operator["output"]
        assert operator["traceable_activity"] == "worker_activity"
        assert operator["contract_status"] == "pass"
