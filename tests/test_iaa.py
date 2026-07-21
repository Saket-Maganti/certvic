from certvic.validation.iaa import cohens_kappa, percent_agreement


def test_kappa_perfect_agreement():
    assert percent_agreement(["yes", "no"], ["yes", "no"]) == 1.0
    assert cohens_kappa(["yes", "no"], ["yes", "no"]) == 1.0
