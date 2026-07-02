import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
import json
import os
import webbrowser


def _app_dir() -> str:
    """Directory of the running exe/script — used for files that must be written (persist across runs)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def _resource_dir() -> str:
    """Directory of bundled read-only resources — PyInstaller extracts these to a temp dir at runtime."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(__file__)


DEFAULT_ICU_RULE_PATH = os.path.join(_resource_dir(), "Plural_form_regex.txt")
CUSTOM_RULES_PATH = os.path.join(_app_dir(), "custom_regex_rules.json")
README_PATH = os.path.join(_resource_dir(), "README.md")

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


def load_saved_custom_rules() -> list[RegexRule]:
    try:
        with open(CUSTOM_RULES_PATH, "r", encoding="utf-8") as file_handle:
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


def save_custom_rules(rules: list[RegexRule]) -> bool:
    try:
        with open(CUSTOM_RULES_PATH, "w", encoding="utf-8") as file_handle:
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


class RegexApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CAT Regex Protector")
        self.root.geometry("760x540")
        self.root.minsize(700, 500)
        self.root.configure(bg=BG_APP)

        self._configure_style()

        header = ttk.Frame(root, style="Header.TFrame", padding=(14, 12))
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Regex Builder for CAT Tools",
            style="Title.TLabel",
        ).pack(anchor="w")
        tk.Frame(root, height=2, bg=ACCENT_TEAL, bd=0, highlightthickness=0).pack(fill="x")

        container = ttk.Frame(root, padding=14)
        container.pack(fill="both", expand=True)

        instructions = (
            "Enter content to protect (for example <b>, <i>, {0}, %s, ICU plural messages). "
            "Generate separate rules and copy them one-by-one for CAT tool regex settings."
        )
        ttk.Label(container, text=instructions, wraplength=720, style="Muted.TLabel").pack(
            anchor="w", pady=(0, 10)
        )

        tool_frame = ttk.Frame(container)
        tool_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(tool_frame, text="Target regex flavor:").pack(side="left")
        self.tool_var = tk.StringVar(value="Generic (works in most CAT tools)")
        tool_picker = ttk.Combobox(
            tool_frame,
            textvariable=self.tool_var,
            state="readonly",
            values=[
                "Generic (works in most CAT tools)",
                "Java-like (Trados/memoQ often similar)",
                ".NET-like",
            ],
            width=42,
        )
        tool_picker.pack(side="left", padx=(8, 0))

        input_frame = ttk.Frame(container)
        input_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(input_frame, text="Input:").pack(side="left")
        ttk.Label(
            input_frame,
            text="(include full code, e.g. [abc])",
            style="Muted.TLabel",
        ).pack(side="left", padx=(6, 10))
        self.user_input = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self.user_input)
        input_entry.pack(side="left", fill="x", expand=True)
        input_entry.focus_set()
        input_entry.bind("<Return>", self.generate)

        action_frame = ttk.Frame(container)
        action_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(action_frame, text="Generate mode:").pack(side="left")
        self.mode_var = tk.StringVar(value="generic match")
        mode_picker = ttk.Combobox(
            action_frame,
            textvariable=self.mode_var,
            state="readonly",
            values=["generic match", "exact match", "word-only", "number-only", "custom regex"],
            width=16,
        )
        mode_picker.pack(side="left", padx=(8, 10))

        ttk.Button(action_frame, text="Generate Regex", style="Accent.TButton", command=self.generate).pack(
            side="left"
        )
        ttk.Button(action_frame, text="Clear", command=self.clear).pack(side="left", padx=(8, 0))
        ttk.Button(action_frame, text="Open README", command=self.open_readme).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Save Selected as Custom",
            style="Purple.TButton",
            command=self.save_selected_as_custom,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Delete Custom Rule",
            style="Purple.TButton",
            command=self.delete_selected_custom,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Load ICU TXT Rules",
            style="Amber.TButton",
            command=self.load_icu_rules_file,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(action_frame, text="Copy Selected Rule", command=self.copy_selected_rule).pack(
            side="left", padx=(8, 0)
        )

        list_frame = ttk.Frame(container)
        list_frame.pack(fill="both", expand=True)

        self.rule_list = tk.Listbox(
            list_frame,
            height=12,
            bg=BG_PANEL,
            fg=TEXT_MAIN,
            selectbackground=ACCENT_TEAL,
            selectforeground=BG_APP,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT_TEAL,
            relief="flat",
            borderwidth=0,
        )
        self.rule_list.pack(side="left", fill="both", expand=True)
        self.rule_list.bind("<<ListboxSelect>>", self.on_rule_selected)

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.rule_list.yview)
        scroll.pack(side="right", fill="y")
        self.rule_list.config(yscrollcommand=scroll.set)

        ttk.Label(container, text="Selected rule details:").pack(anchor="w", pady=(10, 4))
        self.details = tk.Text(
            container,
            height=9,
            wrap="word",
            font=("Consolas", 10),
            bg=BG_PANEL,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT_TEAL,
            relief="flat",
            borderwidth=0,
        )
        self.details.pack(fill="both", expand=False)

        bottom_frame = ttk.Frame(container)
        bottom_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(bottom_frame, text="Copy Details Panel", command=self.copy_details).pack(side="left")
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(side="right")

        self.rules: list[RegexRule] = []
        self.custom_icu_rules: list[RegexRule] = []
        self.saved_custom_rules: list[RegexRule] = load_saved_custom_rules()
        self.try_load_default_icu_rules()
        self._write_welcome()

    def _configure_style(self) -> None:
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(font_name).configure(family=FONT_FAMILY, size=10)

        self.root.option_add("*TCombobox*Listbox*Background", BG_PANEL)
        self.root.option_add("*TCombobox*Listbox*Foreground", TEXT_MAIN)
        self.root.option_add("*TCombobox*Listbox*selectBackground", ACCENT_TEAL)
        self.root.option_add("*TCombobox*Listbox*selectForeground", BG_APP)

        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("TFrame", background=BG_APP)
        style.configure("TLabel", background=BG_APP, foreground=TEXT_MAIN)
        style.configure("Muted.TLabel", background=BG_APP, foreground=TEXT_MUTED)
        style.configure("Header.TFrame", background=BG_HEADER)
        style.configure(
            "Title.TLabel", background=BG_HEADER, foreground=TEXT_MAIN, font=(FONT_FAMILY, 14, "bold")
        )

        style.configure(
            "TButton",
            background=BG_PANEL,
            foreground=TEXT_MAIN,
            bordercolor=BORDER,
            focuscolor=ACCENT_TEAL,
            padding=6,
        )
        style.map(
            "TButton",
            background=[("active", ACCENT_TEAL), ("pressed", ACCENT_TEAL)],
            foreground=[("active", BG_APP), ("pressed", BG_APP)],
        )

        style.configure("Accent.TButton", background=ACCENT_TEAL, foreground=BG_APP, bordercolor=ACCENT_TEAL)
        style.map("Accent.TButton", background=[("active", "#5eead4")], foreground=[("active", BG_APP)])

        style.configure("Amber.TButton", background=BG_PANEL, foreground=ACCENT_AMBER, bordercolor=ACCENT_AMBER)
        style.map("Amber.TButton", background=[("active", ACCENT_AMBER)], foreground=[("active", BG_APP)])

        style.configure("Purple.TButton", background=BG_PANEL, foreground=ACCENT_PURPLE, bordercolor=ACCENT_PURPLE)
        style.map("Purple.TButton", background=[("active", ACCENT_PURPLE)], foreground=[("active", TEXT_MAIN)])

        style.configure(
            "TEntry",
            fieldbackground=BG_PANEL,
            foreground=TEXT_MAIN,
            insertcolor=TEXT_MAIN,
            bordercolor=BORDER,
        )
        style.map("TEntry", bordercolor=[("focus", ACCENT_TEAL)])

        style.configure(
            "TCombobox",
            fieldbackground=BG_PANEL,
            background=BG_PANEL,
            foreground=TEXT_MAIN,
            arrowcolor=TEXT_MUTED,
            bordercolor=BORDER,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", BG_PANEL)],
            foreground=[("readonly", TEXT_MAIN)],
            bordercolor=[("focus", ACCENT_TEAL)],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=BG_PANEL,
            troughcolor=BG_APP,
            bordercolor=BORDER,
            arrowcolor=TEXT_MUTED,
        )

    def _set_status(self, message: str, kind: str = "default") -> None:
        self.status_var.set(message)
        self.status_label.configure(foreground=STATUS_COLORS.get(kind, TEXT_MUTED))

    def _write_welcome(self) -> None:
        self.rule_list.delete(0, "end")
        self.details.delete("1.0", "end")
        self.details.insert(
            "end",
            "Enter input and click Generate Regex.\n\n"
            "If input is an ICU plural message, specialized ordered rules will be generated.\n"
            "For ICU branch content, use capture group 1 as translatable text.\n"
            "You can also load your own ICU regex list from TXT.\n",
        )

    def generate(self, event=None) -> None:
        text = self.user_input.get().strip()
        selected_mode = self.mode_var.get()
        if not text and selected_mode != "custom regex":
            messagebox.showwarning("Missing input", "Please enter text to generate regex.")
            return

        if selected_mode == "custom regex":
            self.rules = list(self.saved_custom_rules)
            if not self.rules:
                self._set_status("No saved custom regex rules yet.", "warning")
                self.rule_list.delete(0, "end")
                self.details.delete("1.0", "end")
                self.details.insert("end", "No custom regex rules saved.\nUse 'Save Selected as Custom'.")
                return
        elif selected_mode == "generic match" and is_icu_plural_message(text):
            # Prefer a user-loaded ICU rule set (Load ICU TXT Rules) over the
            # four built-in ordered rules, if one has been loaded.
            self.rules = list(self.custom_icu_rules) if self.custom_icu_rules else build_icu_plural_rules()
        else:
            self.rules = build_mode_rules(text, selected_mode)

        self.rule_list.delete(0, "end")
        for idx, rule in enumerate(self.rules, start=1):
            self.rule_list.insert("end", f"{idx}. {rule.name}")

        if self.rules:
            self.rule_list.selection_set(0)
            self.on_rule_selected()

        flavor = self.tool_var.get()
        self._set_status(f"Generated {len(self.rules)} rules for {flavor}.", "success")

    def clear(self) -> None:
        self.user_input.set("")
        self._write_welcome()
        self.rules = []
        self._set_status("Cleared.", "default")

    def on_rule_selected(self, event=None) -> None:
        selection = self.rule_list.curselection()
        if not selection:
            return

        idx = selection[0]
        rule = self.rules[idx]
        panel_text = (
            f"Rule: {rule.name}\n"
            f"Regex: {rule.pattern}\n"
            f"Purpose: {rule.purpose}\n"
        )
        self.details.delete("1.0", "end")
        self.details.insert("end", panel_text)

    def copy_selected_rule(self) -> None:
        selection = self.rule_list.curselection()
        if not selection:
            self._set_status("Select a rule first.", "warning")
            return
        idx = selection[0]
        self.root.clipboard_clear()
        self.root.clipboard_append(self.rules[idx].pattern)
        self._set_status(f"Copied regex: {self.rules[idx].name}", "success")

    def copy_details(self) -> None:
        content = self.details.get("1.0", "end").strip()
        if not content:
            self._set_status("Nothing to copy.", "warning")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self._set_status("Copied details panel.", "success")

    def open_readme(self) -> None:
        if not os.path.exists(README_PATH):
            messagebox.showwarning("README missing", "README.md was not found next to regex-app.py.")
            return
        try:
            os.startfile(README_PATH)  # type: ignore[attr-defined]
            self._set_status("Opened README.md", "success")
        except OSError:
            try:
                webbrowser.open(f"file://{README_PATH}")
                self._set_status("Opened README.md", "success")
            except Exception:
                messagebox.showerror("Open failed", "Could not open README.md.")
                self._set_status("Failed to open README.md.", "error")

    def load_icu_rules_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select ICU regex TXT file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            parsed_rules = load_custom_rules_from_path(path)
        except OSError as exc:
            messagebox.showerror("Read error", f"Could not read file:\n{exc}")
            self._set_status("Could not read ICU rules file.", "error")
            return

        if not parsed_rules:
            messagebox.showwarning(
                "No rules found",
                "No valid ICU rules were found in the file.\n"
                "Expected either:\n"
                "regex\nname|regex|purpose\nor\nregex - notes",
            )
            self._set_status("No valid ICU rules found in file.", "warning")
            return

        self.custom_icu_rules = parsed_rules
        self._set_status(f"Loaded {len(parsed_rules)} custom ICU rules.", "success")

    def save_selected_as_custom(self) -> None:
        selection = self.rule_list.curselection()
        if not selection:
            self._set_status("Select a generated rule first.", "warning")
            return
        idx = selection[0]
        selected_rule = self.rules[idx]
        if any(rule.pattern == selected_rule.pattern for rule in self.saved_custom_rules):
            self._set_status("Custom regex already saved.", "warning")
            return

        custom_rule = RegexRule(
            name=selected_rule.name,
            pattern=selected_rule.pattern,
            purpose=f"Custom: {selected_rule.purpose}",
        )
        self.saved_custom_rules.append(custom_rule)
        if not save_custom_rules(self.saved_custom_rules):
            self.saved_custom_rules.pop()
            messagebox.showerror("Save failed", "Could not save custom regex rules to disk.")
            self._set_status("Failed to save custom regex.", "error")
            return
        self._set_status(f"Saved custom regex: {custom_rule.name}", "success")

    def delete_selected_custom(self) -> None:
        if self.mode_var.get() != "custom regex":
            self._set_status("Switch to 'custom regex' mode to delete saved rules.", "warning")
            return
        selection = self.rule_list.curselection()
        if not selection:
            self._set_status("Select a custom rule to delete.", "warning")
            return

        idx = selection[0]
        if idx >= len(self.saved_custom_rules):
            return
        removed = self.saved_custom_rules.pop(idx)
        if not save_custom_rules(self.saved_custom_rules):
            self.saved_custom_rules.insert(idx, removed)
            messagebox.showerror("Delete failed", "Could not update saved custom regex rules.")
            self._set_status("Failed to delete custom regex.", "error")
            return
        self._set_status(f"Deleted custom regex: {removed.name}", "success")
        self.generate()

    def try_load_default_icu_rules(self) -> None:
        try:
            parsed_rules = load_custom_rules_from_path(DEFAULT_ICU_RULE_PATH)
        except OSError:
            return
        if parsed_rules:
            self.custom_icu_rules = parsed_rules
            self._set_status(f"Loaded default ICU cheat sheet ({len(parsed_rules)} rules).", "success")


def main() -> None:
    root = tk.Tk()
    app = RegexApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
