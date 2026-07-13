from findwork.roles import match_role, role_terms


ROLES = [
    "Cloud engineer",
    "DevOps engineer",
    "Platform engineer",
    "Site reliability engineer",
    "SRE",
    "Kubernetes engineer",
    "Python developer",
    "Data engineer",
]


def test_generic_words_are_stripped():
    terms = dict(role_terms(ROLES))
    assert terms["python"] == "Python developer"
    assert terms["site reliability"] == "Site reliability engineer"
    assert terms["devops"] == "DevOps engineer"


def test_python_role_matches_without_the_word_developer():
    assert match_role("Senior Python Engineer (Prague)", ROLES) == "Python developer"


def test_data_engineer_matches():
    assert match_role("Data Engineer - Praha 8", ROLES) == "Data engineer"


def test_word_boundaries_prevent_substring_hits():
    # "data" must not match inside "database"
    assert match_role("Database Administrator", ["Data engineer"]) == ""


def test_longer_terms_win_over_shorter():
    assert match_role("site reliability engineer", ROLES) == "Site reliability engineer"


def test_no_match_returns_empty():
    assert match_role("Accountant", ROLES) == ""


def test_role_without_specific_words_uses_whole_role():
    assert dict(role_terms(["Developer"])) == {"developer": "Developer"}
    assert match_role("developer wanted", ["Developer"]) == "Developer"
