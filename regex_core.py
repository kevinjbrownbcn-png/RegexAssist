"""Regex-building logic shared by the Tkinter desktop app (RegexAssist.py) and
the Streamlit web app (streamlit_app.py). No GUI toolkit imports here — this
module must stay importable in minimal/headless environments (e.g. Streamlit
Cloud, which does not have Tk installed).
"""
import json
import re
from dataclasses import dataclass

FONT_FAMILY = "Segoe UI"

BG_APP = "#0f172a"
BG_PANEL = "#1e293b"
BG_HEADER = "#0b0f19"
ACCENT_TEAL = "#2dd4bf"
ACCENT_AMBER = "#eab308"
ACCENT_PURPLE = "#a855f7"
TEXT_MUTED = "#64748b"
BORDER = "#30363d"
TEXT_MAIN = "#f8fafc"
SUCCESS = "#10b981"
ERROR = "#ef4444"
WARNING = "#f97316"

STATUS_COLORS = {
    "default": TEXT_MUTED,
    "success": SUCCESS,
    "warning": WARNING,
    "error": ERROR,
}


@dataclass
class RegexRule:
    name: str
    pattern: str
    purpose: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "pattern": self.pattern, "purpose": self.purpose}


def parse_custom_rule_line(line: str, index: int) -> RegexRule | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    parts = [part.strip() for part in stripped.split("|")]
    if len(parts) >= 2:
        return RegexRule(
            name=parts[0] or f"Custom ICU rule {index}",
            pattern=parts[1],
            purpose=parts[2] if len(parts) > 2 and parts[2] else "Loaded from TXT file.",
        )

    if " - " in stripped:
        pattern, purpose = stripped.split(" - ", 1)
        return RegexRule(
            name=f"Custom ICU rule {index}",
            pattern=pattern.strip(),
            purpose=purpose.strip() or "Loaded from TXT file.",
        )

    return RegexRule(
        name=f"Custom ICU rule {index}",
        pattern=stripped,
        purpose="Loaded from TXT file.",
    )


def load_custom_rules_from_path(path: str) -> list[RegexRule]:
    with open(path, "r", encoding="utf-8") as file_handle:
        lines = file_handle.readlines()

    parsed_rules: list[RegexRule] = []
    for line in lines:
        rule = parse_custom_rule_line(line, len(parsed_rules) + 1)
        if rule:
            parsed_rules.append(rule)
    return parsed_rules


def parse_custom_rules_from_text(text: str) -> list[RegexRule]:
    parsed_rules: list[RegexRule] = []
    for line in text.splitlines():
        rule = parse_custom_rule_line(line, len(parsed_rules) + 1)
        if rule:
            parsed_rules.append(rule)
    return parsed_rules


def load_saved_custom_rules(path: str) -> list[RegexRule]:
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return []

    rules: list[RegexRule] = []
    if not isinstance(data, list):
        return rules

    for item in data:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", "")).strip()
        if not pattern:
            continue
        rules.append(
            RegexRule(
                name=str(item.get("name", f"Custom regex {len(rules) + 1}")).strip() or f"Custom regex {len(rules) + 1}",
                pattern=pattern,
                purpose=str(item.get("purpose", "User saved custom regex.")).strip() or "User saved custom regex.",
            )
        )
    return rules


def save_custom_rules(rules: list[RegexRule], path: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump([rule.as_dict() for rule in rules], file_handle, indent=2)
    except OSError:
        return False
    return True


def classify_input(user_input: str) -> str:
    text = user_input.strip()
    if is_icu_plural_message(text):
        return "icu_plural"
    if re.search(r"<[^>]+>", text):
        return "markup"
    if re.search(r"\{[^{}]+\}", text):
        return "brace_placeholders"
    if re.search(r"%(\d+\$)?[sdfoxegc]", text, re.IGNORECASE):
        return "printf"
    return "generic_text"


def build_specific_tag_rule(user_input: str) -> RegexRule | None:
    match = re.fullmatch(r"\s*<\s*([a-zA-Z][\w:-]*)\s*>\s*", user_input)
    if not match:
        return None
    tag_name = match.group(1)
    return RegexRule(
        name=f"Specific opening tag <{tag_name}>",
        pattern=rf"<{re.escape(tag_name)}\b[^>]*?>",
        purpose="Protect only this opening tag (with optional attributes).",
    )


def is_icu_plural_message(text: str) -> bool:
    return bool(
        re.search(
            r"^\s*\{\s*[A-Za-z_]\w*\s*,\s*plural\s*,",
            text,
            flags=re.IGNORECASE,
        )
    )


def build_icu_plural_rules() -> list[RegexRule]:
    return [
        RegexRule(
            name="Plural opening string",
            pattern=r"\{\s*(\w+),\s*(\w+),\s*[^{}]*\{",
            purpose="Covers opening plural strings. Keep this first in rule order.",
        ),
        RegexRule(
            name="Plural internal separators",
            pattern=r"(\}\s*?(\w+)\s*?\{)",
            purpose="Covers internal non-translatable plural separators. Keep this second.",
        ),
        RegexRule(
            name="Plural stray closing brace",
            pattern=r"\}+",
            purpose="Covers stray closing braces. Keep this third.",
        ),
        RegexRule(
            name="Plural stray opening brace",
            pattern=r"\{+",
            purpose="Covers stray opening braces. Keep after {+.*?}+ when that rule is used.",
        ),
    ]


def build_delimiter_generic_rules(user_input: str) -> list[RegexRule]:
    text = user_input.strip()
    delimiter_rules: list[RegexRule] = []

    if re.search(r"\[[^\]]*\]", text):
        delimiter_rules.append(
            RegexRule(
                name="Square-bracket content",
                pattern=r"\[[^\]]*?\]",
                purpose="Generic match for content inside [...].",
            )
        )
    if re.search(r"\([^)]*\)", text):
        delimiter_rules.append(
            RegexRule(
                name="Parentheses content",
                pattern=r"\([^)]*?\)",
                purpose="Generic match for content inside (...).",
            )
        )
    if re.search(r"\{[^{}]*\}", text):
        delimiter_rules.append(
            RegexRule(
                name="Curly-brace content",
                pattern=r"\{[^{}]*?\}",
                purpose="Generic match for content inside {...}.",
            )
        )
    if re.search(r"<[^>]*>", text):
        delimiter_rules.append(
            RegexRule(
                name="Angle-bracket content",
                pattern=r"<[^>]*?>",
                purpose="Generic match for content inside <...>.",
            )
        )
    if '"' in text:
        delimiter_rules.append(
            RegexRule(
                name="Double-quoted content",
                pattern=r'"[^"\n]*?"',
                purpose='Generic match for content inside "..."',
            )
        )
    if "'" in text:
        delimiter_rules.append(
            RegexRule(
                name="Single-quoted content",
                pattern=r"'[^'\n]*?'",
                purpose="Generic match for content inside '...'.",
            )
        )

    return delimiter_rules


def build_special_token_rules(user_input: str) -> list[RegexRule]:
    text = user_input.strip()
    rules: list[RegexRule] = []

    if re.search(r"\$\[[^\]]*\]", text):
        rules.append(
            RegexRule(
                name="Dollar square token",
                pattern=r"\$\[[^\]]*?\]",
                purpose="Generic match for tokens like $[abc].",
            )
        )

    if re.search(r"\$\{[^{}]*\}", text):
        rules.append(
            RegexRule(
                name="Dollar curly token",
                pattern=r"\$\{[^{}]*?\}",
                purpose="Generic match for tokens like ${abc}.",
            )
        )

    if re.search(r"%\d+\$[A-Za-z]", text):
        rules.append(
            RegexRule(
                name="Indexed printf token",
                pattern=r"%\d+\$[A-Za-z]",
                purpose="Generic match for placeholders like %1$d.",
            )
        )

    if re.search(r"<[^/][^>]*?/>", text):
        rules.append(
            RegexRule(
                name="Self-closing tag",
                pattern=r"<[^/][^>]*?/>",
                purpose="Generic match for self-closing tags like <b/>.",
            )
        )

    if "\\n" in text:
        rules.append(
            RegexRule(
                name="Escaped newline literal",
                pattern=r"\\n",
                purpose="Match literal escaped newline sequence \\n.",
            )
        )

    return rules


def build_contextual_rules(user_input: str) -> list[RegexRule]:
    input_type = classify_input(user_input)
    generic_delimiters = build_delimiter_generic_rules(user_input)
    special_tokens = build_special_token_rules(user_input)

    if input_type in ("markup", "icu_plural"):
        rules = [
            RegexRule(
                name="Generic opening tag",
                pattern=r"<[^/]*?>",
                purpose="Protect opening-like tags in HTML/XML content.",
            ),
            RegexRule(
                name="Generic closing tag",
                pattern=r"</[^>]+>",
                purpose="Protect closing tags in HTML/XML content.",
            ),
        ]
        specific = build_specific_tag_rule(user_input)
        if specific:
            rules.insert(1, specific)
        for delimiter_rule in generic_delimiters:
            if delimiter_rule.pattern not in {rule.pattern for rule in rules}:
                rules.append(delimiter_rule)
        rules.extend(special_tokens)
        return dedupe_rules(rules)

    if input_type == "brace_placeholders":
        rules = [
            RegexRule(
                name="Curly-brace placeholders",
                pattern=r"\{[^{}]+\}",
                purpose="Protect single-level placeholders like {name}, {0}, {value}.",
            ),
            RegexRule(
                name="ICU-like token start",
                pattern=r"\{\s*[A-Za-z_]\w*\s*,\s*[a-zA-Z]+\s*,",
                purpose="Protect ICU header-like tokens when present.",
            ),
        ]
        rules.extend(generic_delimiters)
        rules.extend(special_tokens)
        return dedupe_rules(rules)

    if input_type == "printf":
        rules = [
            RegexRule(
                name="Printf placeholders",
                pattern=r"%(\d+\$)?[sdfoxegc]",
                purpose="Protect printf-style placeholders such as %s, %d, %1$s.",
            ),
        ]
        rules.extend(generic_delimiters)
        rules.extend(special_tokens)
        return dedupe_rules(rules)

    if generic_delimiters:
        rules = list(generic_delimiters)
        rules.extend(special_tokens)
        return dedupe_rules(rules)

    if special_tokens:
        return dedupe_rules(special_tokens)

    return [
        RegexRule(
            name="Generic token (non-whitespace chunk)",
            pattern=r"\S+",
            purpose="Fallback generic pattern when no delimiters are detected.",
        )
    ]


def dedupe_rules(rules: list[RegexRule]) -> list[RegexRule]:
    seen: set[str] = set()
    deduped: list[RegexRule] = []
    for rule in rules:
        if rule.pattern in seen:
            continue
        seen.add(rule.pattern)
        deduped.append(rule)
    return deduped


def build_mode_rules(user_input: str, mode: str) -> list[RegexRule]:
    text = user_input.strip()
    if mode == "exact match":
        return [
            RegexRule(
                name="Exact match",
                pattern=re.escape(text),
                purpose="Matches exactly the entered content.",
            )
        ]
    if mode == "word-only":
        parts: list[str] = []
        for token in re.findall(r"[A-Za-z\s]+|.", text):
            if re.fullmatch(r"[A-Za-z\s]+", token):
                parts.append(r"([A-Za-z]+\s*)+")
            else:
                parts.append(re.escape(token))
        word_shaped = "".join(parts) if parts else r"([A-Za-z]+\s*)+"
        return [
            RegexRule(
                name="Word-only",
                pattern=word_shaped,
                purpose="Matches input shape with repeatable word+whitespace grouping and punctuation preserved.",
            )
        ]
    if mode == "number-only":
        parts: list[str] = []
        for token in re.findall(r"[A-Za-z0-9]+|.", text):
            if re.fullmatch(r"[A-Za-z0-9]+", token):
                parts.append(r"\d+")
            else:
                parts.append(re.escape(token))
        number_shaped = "".join(parts) if parts else r"\d+"
        return [
            RegexRule(
                name="Number-only",
                pattern=number_shaped,
                purpose="Matches input shape with numbers generalized and punctuation preserved.",
            )
        ]
    return build_contextual_rules(text)
