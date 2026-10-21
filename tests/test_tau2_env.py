"""Smoke tests for the vendored tau2-bench environments (benchmark integration).

Runs fully offline against the bundled domain databases. Skipped unless the
``tau2`` extra is installed: ``pip install -e ".[tau2]"``.
"""

import pytest

for _mod in ("litellm", "loguru", "deepdiff", "toml", "addict"):
    pytest.importorskip(_mod)

import qqr.tools.tau2_bench  # noqa: E402,F401  (registers the embedded `tau2` package)


@pytest.mark.parametrize("domain,min_tasks", [("retail", 100), ("airline", 40)])
def test_domain_loads_tasks_and_tools(domain, min_tasks):
    mod = __import__(f"tau2.domains.{domain}.environment", fromlist=["get_environment"])
    env = mod.get_environment()
    tasks = mod.get_tasks()
    assert len(tasks) >= min_tasks
    names = {t.name for t in env.get_tools()}
    assert "calculate" in names
    assert env.use_tool("calculate", expression="(2 + 3) * 4") in ("20", "20.0", 20, 20.0)


def test_retail_tools_read_and_mutate_isolated_db():
    from tau2.domains.retail.environment import get_environment

    env = get_environment()
    db = env.tools.db
    user_id = next(iter(db.users))
    user = env.use_tool("get_user_details", user_id=user_id)
    assert user.user_id == user_id

    with pytest.raises(Exception):
        env.use_tool("get_user_details", user_id="no_such_user_123")

    # a fresh environment loads a fresh database (no cross-test state leakage)
    other = get_environment()
    assert other.tools.db is not db
