from fnmatch import fnmatch


def matches_url(pattern: str, url: str) -> bool:
    wildcard = f"*{pattern}*"
    return fnmatch(url, wildcard)
