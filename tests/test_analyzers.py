from school_lab import analyzers


def test_nonempty_line_numbers() -> None:
    test_str = "\n a \n\n b\n"

    assert analyzers.nonempty_line_numbers(test_str) == (2, 4)

def test_empty_line_numbers() -> None:
    test_str = ""

    assert analyzers.nonempty_line_numbers(test_str) == ()

def test_without_spaces_numbers() -> None:
    test_str = "a\nb"

    assert analyzers.nonempty_line_numbers(test_str) == (1, 2)

def test_spaces_and_newlines_numbers() -> None:
    test_str = "          \n     \n"

    assert analyzers.nonempty_line_numbers(test_str) == ()