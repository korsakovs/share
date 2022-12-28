from updateme.core.utils import join_strings_with_commas


def test_join_strings_with_commas():
    assert join_strings_with_commas([]) == ""
    assert join_strings_with_commas([""]) == ""
    assert join_strings_with_commas(["", ""]) == " and "
    assert join_strings_with_commas(["1"]) == "1"
    assert join_strings_with_commas(["1", "2"]) == "1 and 2"
    assert join_strings_with_commas(["1", "2", "3"]) == "1, 2, and 3"
    assert join_strings_with_commas(["1", "2", "3", "4"]) == "1, 2, 3, and 4"
