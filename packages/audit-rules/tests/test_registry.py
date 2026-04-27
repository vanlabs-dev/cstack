from cstack_audit_rules import RULE_REGISTRY


def test_fifteen_rules_registered() -> None:
    assert len(RULE_REGISTRY) == 15


def test_every_rule_id_is_unique() -> None:
    ids = list(RULE_REGISTRY.keys())
    assert len(set(ids)) == len(ids)


def test_every_rule_has_metadata_and_evaluator() -> None:
    for rule_id, rule in RULE_REGISTRY.items():
        assert rule.metadata.id == rule_id
        assert rule.metadata.title
        assert rule.metadata.references
        assert callable(rule.evaluator)
