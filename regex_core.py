"""Regex-building logic shared by the Tkinter desktop app (RegexAssist.py) and
the Streamlit web app (streamlit_app.py). No GUI toolkit imports here — this
module must stay importable in minimal/headless environments (e.g. Streamlit
Cloud, which does not have Tk installed).
"""
import json
import re
from dataclasses import dataclass, field

FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
FONT_FAMILY_TK = "Segoe UI"  # Tkinter needs a single concrete family, not a CSS stack

DEFAULT_THEME = "dark"

THEMES = {
    "dark": {
        "bg_app": "#0f172a",
        "bg_panel": "#1e293b",
        "bg_header": "#0b0f19",
        "accent_teal": "#2dd4bf",
        "accent_amber": "#eab308",
        "accent_purple": "#a855f7",
        "text_muted": "#64748b",
        "border": "#30363d",
        "text_main": "#f8fafc",
        "success": "#10b981",
        "error": "#ef4444",
        "warning": "#f97316",
    },
    "light": {
        "bg_app": "#f8fafc",
        "bg_panel": "#ffffff",
        "bg_header": "#e2e8f0",
        "accent_teal": "#0d9488",
        "accent_amber": "#b45309",
        "accent_purple": "#9333ea",
        "text_muted": "#475569",
        "border": "#cbd5e1",
        "text_main": "#0f172a",
        "success": "#16a34a",
        "error": "#dc2626",
        "warning": "#ea580c",
    },
}


def status_colors(theme: str) -> dict[str, str]:
    colors = THEMES[theme]
    return {
        "default": colors["text_muted"],
        "success": colors["success"],
        "warning": colors["warning"],
        "error": colors["error"],
    }


@dataclass
class RegexRule:
    name: str
    pattern: str
    purpose: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "pattern": self.pattern, "purpose": self.purpose}


MODULE_CAT = "cat"
MODULE_GENERIC = "generic"
MODULE_LABELS = {MODULE_CAT: "CAT Tools", MODULE_GENERIC: "Generic Regex"}

STATUS_WORKING = "working"
STATUS_FLAGGED = "flagged"


@dataclass
class SavedRegex:
    """A user-saved regex in the shared custom-regex library. Distinct from
    RegexRule (the ephemeral output of the generators) because it carries
    library-management state that generated rules never need."""

    name: str
    pattern: str
    purpose: str
    module: str = MODULE_CAT
    status: str = STATUS_WORKING
    note: str = ""
    flagged_samples: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "purpose": self.purpose,
            "module": self.module,
            "status": self.status,
            "note": self.note,
            "flagged_samples": self.flagged_samples,
        }

    def is_flagged_for(self, sample: str) -> bool:
        sample = sample.strip()
        return bool(sample) and sample in self.flagged_samples


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


def load_saved_custom_rules(path: str) -> list[SavedRegex]:
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return []

    rules: list[SavedRegex] = []
    if not isinstance(data, list):
        return rules

    for item in data:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", "")).strip()
        if not pattern:
            continue
        flagged_samples = item.get("flagged_samples", [])
        if not isinstance(flagged_samples, list):
            flagged_samples = []
        rules.append(
            SavedRegex(
                name=str(item.get("name", f"Custom regex {len(rules) + 1}")).strip() or f"Custom regex {len(rules) + 1}",
                pattern=pattern,
                purpose=str(item.get("purpose", "User saved custom regex.")).strip() or "User saved custom regex.",
                # Files saved before the Generic Regex tab existed predate the module
                # tag entirely — they were always CAT-tab saves, so default to that.
                module=item.get("module") if item.get("module") in MODULE_LABELS else MODULE_CAT,
                status=item.get("status") if item.get("status") in (STATUS_WORKING, STATUS_FLAGGED) else STATUS_WORKING,
                note=str(item.get("note", "")),
                flagged_samples=[str(s) for s in flagged_samples],
            )
        )
    return rules


def save_custom_rules(rules: list[SavedRegex], path: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump([rule.as_dict() for rule in rules], file_handle, indent=2)
    except OSError:
        return False
    return True


def rules_for_module(rules: list[SavedRegex], module: str, exclude_sample: str = "") -> list[SavedRegex]:
    """Saved rules belonging to a module, skipping ones flagged against exclude_sample
    exactly — the 'don't propose this again for the same text' behavior."""
    return [rule for rule in rules if rule.module == module and not rule.is_flagged_for(exclude_sample)]


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


# --- Generic (non-CAT-tool) regex ---------------------------------------
# For matching whole sections of general text (log lines, documents, code)
# rather than small CAT-tool non-translatable placeholders.

GENERIC_SEGMENT_MODES = ["generic match", "exact match", "word-only", "number-only"]

GENERIC_PRESETS: list[RegexRule] = [
    RegexRule(
        name="Email address",
        pattern=r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}",
        purpose="Matches a single email address, including multi-part domains like .co.uk.",
    ),
    RegexRule(
        name="URL (http/https)",
        pattern=r"https?://[^\s<>\"]+",
        purpose="Matches an http(s) URL up to the next whitespace or quote.",
    ),
    RegexRule(
        name="IPv4 address",
        pattern=r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        purpose="Matches an IPv4 address.",
    ),
    RegexRule(
        name="Date (YYYY-MM-DD)",
        pattern=r"\b\d{4}-\d{2}-\d{2}\b",
        purpose="Matches an ISO-style date.",
    ),
    RegexRule(
        name="Date (D/M/Y or M/D/Y)",
        pattern=r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        purpose="Matches a slash-separated date.",
    ),
    RegexRule(
        name="Time (HH:MM[:SS])",
        pattern=r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
        purpose="Matches a 24h or 12h time value.",
    ),
    RegexRule(
        name="Phone number (loose)",
        pattern=r"\+?\d[\d ()-]{7,}\d",
        purpose="Loosely matches international/local phone numbers. May also catch dates/IDs with a similar digit-dash shape — tighten if needed.",
    ),
    RegexRule(
        name="Hex color code",
        pattern=r"#(?:[0-9a-fA-F]{3}){1,2}\b",
        purpose="Matches a 3- or 6-digit hex color.",
    ),
    RegexRule(
        name="Whole line",
        pattern=r"^.*$",
        purpose="Matches an entire line of text.",
    ),
    RegexRule(
        name="Paragraph (blank-line separated)",
        pattern=r"(?:(?!\n[ \t]*\n)[\s\S])+",
        purpose="Matches a block of text (can span multiple lines) up to the next blank line.",
    ),
    RegexRule(
        name="Quoted string (single line)",
        pattern=r'"[^"\n]*"',
        purpose="Matches double-quoted text on one line.",
    ),
    RegexRule(
        name="Quoted block (multi-line)",
        pattern=r'"[\s\S]*?"',
        purpose="Matches double-quoted text that can span multiple lines.",
    ),
    RegexRule(
        name="HTML/XML tag with content",
        pattern=r"<(\w+)[^>]*>[\s\S]*?</\1>",
        purpose="Matches an opening tag, its content, and the matching closing tag.",
    ),
    RegexRule(
        name="Trailing whitespace",
        pattern=r"[ \t]+$",
        purpose="Matches indentation-breaking trailing spaces/tabs at the end of a line.",
    ),
]


def find_matches(pattern: str, text: str) -> list[re.Match]:
    """Run pattern against text for the generic live tester. MULTILINE so ^/$
    anchor per line (needed by presets like 'Whole line'); raises re.error on
    an invalid pattern so callers can show the message to the user."""
    compiled = re.compile(pattern, re.MULTILINE)
    return list(compiled.finditer(text))
