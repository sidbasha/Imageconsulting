"""Contact-sharing detection (row 31).

Finds phone numbers, email addresses, bank details (IBAN, card and account
numbers), links and social handles, including common disguises: Arabic-Indic
digits, numbers written as words in English or Arabic, digits split by spaces
or dots, "at"/"dot" spelled out.

Rule-based and deliberately strict: a false positive is reviewed by a
moderator (row 58) and released; a missed contact cannot be taken back.
It will not catch everything (photos of numbers, coded language).
"""

import re
from dataclasses import dataclass

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
NUMBER_WORDS = {
    # English
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9",
    # Arabic
    "صفر": "0", "واحد": "1", "اثنين": "2", "اثنان": "2", "ثلاثة": "3", "ثلاث": "3", "اربعة": "4", "أربعة": "4",
    "اربع": "4", "أربع": "4", "خمسة": "5", "خمس": "5", "ستة": "6", "ست": "6", "سبعة": "7", "سبع": "7",
    "ثمانية": "8", "ثمان": "8", "تسعة": "9", "تسع": "9",
}
_WORD = re.compile(r"\b(" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")\b", re.IGNORECASE)

EMAIL = re.compile(
    r"[a-z0-9._%+-]+(?:@|\s*[(\[]at[)\]]\s*|\s+at\s+|\s*آت\s*)[a-z0-9-]+"
    r"(?:\.|\s*[(\[]dot[)\]]\s*|\s+dot\s+|\s*دوت\s*)[a-z]{2,}", re.IGNORECASE)
URL = re.compile(r"(https?://|www\.)\S+|\b[a-z0-9-]+\.(com|net|org|ae|me|io|co|link|ly|app)\b(/\S*)?", re.IGNORECASE)
SOCIAL = re.compile(
    r"(wa\.me|whatsapp|واتس|واتساب|telegram|تيليجرام|t\.me|instagram|انستا|انستقرام|snapchat|سناب|tiktok|تيك ?توك|facebook|فيسبوك)"
    r"|(^|\s)@[a-z0-9_.]{3,}", re.IGNORECASE)
IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]){11,30}\b")
BANK_WORDS = re.compile(r"\b(iban|swift|account (no|number)|bank transfer|حساب بنكي|رقم الحساب|آيبان|ايبان|تحويل بنكي)\b", re.IGNORECASE)


@dataclass
class Finding:
    kind: str  # phone | email | link | social | bank
    match: str


def normalise(text: str) -> str:
    text = text.translate(ARABIC_DIGITS)
    return _WORD.sub(lambda m: NUMBER_WORDS[m.group(1).lower()], text)


def _digit_runs(text: str) -> list[str]:
    """Runs of digits allowing separators people use to hide them: spaces, dots, dashes, slashes, brackets."""
    return [re.sub(r"\D", "", m.group(0)) for m in re.finditer(r"\+?\d(?:[\s.\-/()_]*\d){6,}", text)]


def scan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    norm = normalise(text)
    # Specific patterns first, then cut out, so broader patterns do not report them again.
    for m in EMAIL.finditer(norm):
        findings.append(Finding("email", m.group(0).strip()))
    norm = EMAIL.sub(" ", norm)
    for m in IBAN.finditer(norm.replace("-", " ")):
        if sum(c.isdigit() for c in m.group(0)) >= 10:  # real IBANs are mostly digits
            findings.append(Finding("bank", m.group(0)))
            norm = norm.replace(m.group(0), " ")
    for digits in _digit_runs(norm):
        if 13 <= len(digits) <= 19:
            findings.append(Finding("bank", digits))  # card or account number length
        elif len(digits) >= 7:
            findings.append(Finding("phone", digits))
    for regex, kind in ((URL, "link"), (SOCIAL, "social"), (BANK_WORDS, "bank")):
        findings += [Finding(kind, m.group(0).strip()) for m in regex.finditer(norm)]
    seen, unique = set(), []
    for f in findings:
        if (f.kind, f.match) not in seen:
            seen.add((f.kind, f.match))
            unique.append(f)
    return unique
