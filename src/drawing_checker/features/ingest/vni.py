"""Giải mã bảng mã VNI-Windows (font "VNI-*") sang Unicode.

Bản vẽ CAD cũ còn dùng font VNI: mỗi chữ có dấu = chữ gốc + một ký tự dấu đứng sau
(vd. "LÔÙP VÖÕA XI MAÊNG" = "LỚP VỮA XI MĂNG"). PDF giữ nguyên mã ký tự đó nên phải giải mã mới tìm kiếm được.
"""

import unicodedata

_CIRCUMFLEX, _BREVE, _HORN = "̂", "̆", "̛"
_ACUTE, _GRAVE, _HOOK, _TILDE, _DOT = "́", "̀", "̉", "̃", "̣"

# Ký tự dấu đứng sau nguyên âm (dạng chữ hoa; chữ thường là .lower() của nó) → dấu tổ hợp Unicode.
_MODIFIERS: dict[str, str] = {
    "Ù": _ACUTE, "Ø": _GRAVE, "Û": _HOOK, "Õ": _TILDE, "Ï": _DOT,
    "Â": _CIRCUMFLEX, "Á": _CIRCUMFLEX + _ACUTE, "À": _CIRCUMFLEX + _GRAVE, "Å": _CIRCUMFLEX + _HOOK,
    "Ã": _CIRCUMFLEX + _TILDE, "Ä": _CIRCUMFLEX + _DOT,
    "Ê": _BREVE, "É": _BREVE + _ACUTE, "È": _BREVE + _GRAVE, "Ú": _BREVE + _HOOK,
    "Ü": _BREVE + _TILDE, "Ë": _BREVE + _DOT,
}
_MODIFIERS.update({k.lower(): v for k, v in list(_MODIFIERS.items())})
# Nguyên âm gốc; "Ô" / "Ö" của VNI là Ơ / Ư.
_BASES: dict[str, str] = {c: c for c in "AEOUYaeouy"}
_BASES.update({"Ô": "O" + _HORN, "ô": "o" + _HORN, "Ö": "U" + _HORN, "ö": "u" + _HORN})
# Ký tự đơn không theo quy tắc gốc + dấu.
_SINGLES: dict[str, str] = {"Ñ": "Đ", "ñ": "đ", "Æ": "Ỉ", "æ": "ỉ", "Ó": "Ĩ", "ó": "ĩ", "Ò": "Ị", "ò": "ị",
                            "Î": "Ỵ", "î": "ỵ"}


def is_vni_font(font: str) -> bool:
    return font.upper().startswith("VNI")


def decode_vni(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        base = _BASES.get(ch)
        if base is not None:
            mark = _MODIFIERS.get(text[i + 1]) if i + 1 < len(text) else None
            out.append(base + (mark or ""))
            i += 2 if mark else 1
            continue
        out.append(_SINGLES.get(ch, ch))
        i += 1
    return unicodedata.normalize("NFC", "".join(out))
