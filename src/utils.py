
import re

RE_ATU_PARENT = re.compile(r"^\s*(?:ATU[_\s-]*)?(\d{1,4})")

def atu_parent(label: str) -> str:
    if label is None:
        return ""
    s = str(label).strip()
    if not s:
        return ""
    m = RE_ATU_PARENT.search(s)
    return m.group(1) if m else ""