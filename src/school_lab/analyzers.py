def nonempty_line_numbers(text: str) -> tuple[int, ...]:
    res: tuple[int, ...] = ()

    lines = text.splitlines()

    for i in range(len(lines)):
        if lines[i].strip():
            res += (i + 1, )

    return res
