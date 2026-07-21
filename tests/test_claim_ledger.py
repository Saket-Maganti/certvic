from certvic.reporting.claim_ledger import build_claim_ledger


def test_uncertified_claim_not_safe():
    ledger = build_claim_ledger({"n": 1}, {"certified": False}, [])
    assert not ledger[0].safe
