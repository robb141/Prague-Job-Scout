from findwork.collation import czech_sort_key


def sorted_cz(words):
    return sorted(words, key=czech_sort_key)


def test_c_hacek_sorts_right_after_c_not_after_z():
    words = ["cyklista", "čaj", "auto", "zebra", "cukr"]
    assert sorted_cz(words) == ["auto", "cukr", "cyklista", "čaj", "zebra"]


def test_all_c_words_precede_c_hacek_words():
    assert sorted_cz(["čáp", "cizí"]) == ["cizí", "čáp"]


def test_other_hacek_letters():
    assert sorted_cz(["sto", "šterk", "tir"]) == ["sto", "šterk", "tir"]
    assert sorted_cz(["ryba", "řeka", "sob"]) == ["ryba", "řeka", "sob"]
    assert sorted_cz(["zima", "žaba"]) == ["zima", "žaba"]


def test_accented_vowels_file_next_to_base_letter():
    # accent is only a tie-breaker: "a" and "á" interleave with the base letter
    assert sorted_cz(["ada", "áda", "aby"]) == ["aby", "ada", "áda"]
    assert sorted_cz(["pas", "pás", "paseka"]) == ["pas", "pás", "paseka"]


def test_case_insensitive():
    assert sorted_cz(["Čokoláda", "cesta"]) == ["cesta", "Čokoláda"]


def test_non_alphabet_characters_sort_last():
    assert sorted_cz(["auto", "zebra", "9to5"]) == ["auto", "zebra", "9to5"]
