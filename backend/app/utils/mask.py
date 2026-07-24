def mask_middle(value: str | None, keep_start: int = 4, keep_end: int = 4) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) <= keep_start + keep_end:
        return "*" * len(text)
    return f"{text[:keep_start]}{'*' * (len(text) - keep_start - keep_end)}{text[-keep_end:]}"


def mask_name(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) <= 2:
        return text[0] + "*"
    return text[:2] + "*" * max(2, len(text) - 2)

