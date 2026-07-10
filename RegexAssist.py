import datetime
import json
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
import os
import webbrowser

import ttkbootstrap  # noqa: F401 — side effect: patches tkinter.ttk widgets to accept bootstyle=
from ttkbootstrap.style import Style, ThemeDefinition

from regex_core import (
    DEFAULT_THEME,
    FONT_FAMILY_TK,
    THEMES,
    RegexRule,
    build_icu_plural_rules,
    build_mode_rules,
    is_icu_plural_message,
    load_custom_rules_from_path,
    load_saved_custom_rules,
    save_custom_rules,
    status_colors,
)

GITHUB_URL = "https://github.com/kevinjbrownbcn-png/RegexAssist"


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
THEME_PREFS_PATH = os.path.join(_app_dir(), "theme_prefs.json")


def load_theme_pref() -> str:
    try:
        with open(THEME_PREFS_PATH, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        theme = data.get("theme")
        if theme in THEMES:
            return theme
    except (OSError, json.JSONDecodeError):
        pass
    return DEFAULT_THEME


def save_theme_pref(theme: str) -> None:
    try:
        with open(THEME_PREFS_PATH, "w", encoding="utf-8") as file_handle:
            json.dump({"theme": theme}, file_handle)
    except OSError:
        pass


class RegexApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CAT Regex Protector")
        self.theme = load_theme_pref()
        self.colors = THEMES[self.theme]
        self._status_kind = "default"

        self._configure_style()
        self.root.configure(bg=self.colors["bg_app"])

        header = ttk.Frame(root, style="Header.TFrame", padding=(14, 12))
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Regex Builder for CAT Tools",
            style="Title.TLabel",
        ).pack(side="left")

        switcher_frame = ttk.Frame(header, style="Header.TFrame")
        switcher_frame.pack(side="right")
        ttk.Label(switcher_frame, text="Theme:", style="MutedHeader.TLabel").pack(side="left", padx=(0, 6))
        self.theme_var = tk.StringVar(value=self.theme.capitalize())
        theme_picker = ttk.Combobox(
            switcher_frame,
            textvariable=self.theme_var,
            state="readonly",
            values=["Dark", "Light"],
            width=8,
        )
        theme_picker.pack(side="left")
        theme_picker.bind("<<ComboboxSelected>>", self._on_theme_change)

        self.separator = tk.Frame(root, height=2, bd=0, highlightthickness=0)
        self.separator.pack(fill="x")

        self.footer_border = tk.Frame(root, height=1, bd=0, highlightthickness=0)
        self.footer_border.pack(side="bottom", fill="x")
        footer = ttk.Frame(root, style="Header.TFrame", padding=(14, 8))
        footer.pack(side="bottom", fill="x")

        year = datetime.date.today().year
        self.footer_left = ttk.Label(
            footer,
            text=f"© {year} CAT Regex Protector | Regex Builder for CAT Tools",
            style="MutedHeader.TLabel",
        )
        self.footer_left.pack(side="left")

        footer_right = ttk.Frame(footer, style="Header.TFrame")
        footer_right.pack(side="right")
        self.footer_links: list[ttk.Label] = []
        for text, handler in (("README", self.open_readme), ("GitHub", self._open_github)):
            link = ttk.Label(footer_right, text=text, style="NavLink.TLabel", cursor="hand2")
            link.pack(side="left", padx=(14, 0))
            link.bind("<Button-1>", lambda _event, fn=handler: fn())
            self.footer_links.append(link)

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

        ttk.Button(action_frame, text="Generate Regex", bootstyle="primary", command=self.generate).pack(
            side="left"
        )
        ttk.Button(action_frame, text="Clear", bootstyle="secondary", command=self.clear).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(action_frame, text="Open README", bootstyle="secondary", command=self.open_readme).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(
            action_frame,
            text="Save Selected as Custom",
            bootstyle="info",
            command=self.save_selected_as_custom,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Delete Custom Rule",
            bootstyle="info",
            command=self.delete_selected_custom,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame,
            text="Load ICU TXT Rules",
            bootstyle="warning",
            command=self.load_icu_rules_file,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            action_frame, text="Copy Selected Rule", bootstyle="secondary", command=self.copy_selected_rule
        ).pack(side="left", padx=(8, 0))

        list_frame = ttk.Frame(container)
        list_frame.pack(fill="both", expand=True)

        self.rule_list = tk.Listbox(
            list_frame,
            height=12,
            highlightthickness=1,
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
            highlightthickness=1,
            relief="flat",
            borderwidth=0,
        )
        self.details.pack(fill="both", expand=False)

        bottom_frame = ttk.Frame(container)
        bottom_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(
            bottom_frame, text="Copy Details Panel", bootstyle="secondary", command=self.copy_details
        ).pack(side="left")
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(side="right")

        self.rules: list[RegexRule] = []
        self.custom_icu_rules: list[RegexRule] = []
        self.saved_custom_rules: list[RegexRule] = load_saved_custom_rules(CUSTOM_RULES_PATH)
        self.try_load_default_icu_rules()
        self._write_welcome()
        self._apply_theme(self.theme, persist=False)

        # Size from actual content instead of a guessed constant — the action button
        # row silently overflows a too-small fixed window since Tk doesn't wrap it.
        self.root.update_idletasks()
        req_width = self.root.winfo_reqwidth()
        req_height = self.root.winfo_reqheight()
        self.root.minsize(req_width, req_height)
        self.root.geometry(f"{req_width + 20}x{req_height + 20}")

    def _configure_style(self) -> None:
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(font_name).configure(family=FONT_FAMILY_TK, size=10)

        style = Style()
        hover_accent = {"dark": "#5eead4", "light": "#0f766e"}
        for theme_name, colors in THEMES.items():
            style.register_theme(
                ThemeDefinition(
                    name=f"catregex_{theme_name}",
                    themetype=theme_name,
                    colors={
                        "primary": colors["accent_teal"],
                        "secondary": colors["text_muted"],
                        "success": colors["success"],
                        "info": colors["accent_purple"],
                        "warning": colors["accent_amber"],
                        "danger": colors["error"],
                        "light": colors["bg_panel"],
                        "dark": colors["bg_header"],
                        "bg": colors["bg_app"],
                        "fg": colors["text_main"],
                        "selectbg": colors["accent_teal"],
                        "selectfg": "#f8fafc",
                        "border": colors["border"],
                        "inputfg": colors["text_main"],
                        "inputbg": colors["bg_panel"],
                        "active": hover_accent[theme_name],
                    },
                )
            )

    def _apply_theme(self, theme_name: str, persist: bool = True) -> None:
        self.theme = theme_name
        self.colors = THEMES[theme_name]
        c = self.colors

        self.root.option_add("*TCombobox*Listbox*Background", c["bg_panel"])
        self.root.option_add("*TCombobox*Listbox*Foreground", c["text_main"])
        self.root.option_add("*TCombobox*Listbox*selectBackground", c["accent_teal"])
        self.root.option_add("*TCombobox*Listbox*selectForeground", c["bg_app"])

        style = Style()
        style.theme_use(f"catregex_{theme_name}")

        style.configure("Header.TFrame", background=c["bg_header"])
        style.configure(
            "Title.TLabel", background=c["bg_header"], foreground=c["text_main"], font=(FONT_FAMILY_TK, 14, "bold")
        )
        style.configure("MutedHeader.TLabel", background=c["bg_header"], foreground=c["text_muted"])
        style.configure("Muted.TLabel", background=c["bg_app"], foreground=c["text_muted"])
        style.configure(
            "NavLink.TLabel",
            background=c["bg_header"],
            foreground=c["accent_teal"],
            font=(FONT_FAMILY_TK, 10, "bold"),
        )

        self.root.configure(bg=c["bg_app"])
        self.separator.configure(bg=c["accent_teal"])
        self.footer_border.configure(bg=c["border"])

        self.rule_list.configure(
            bg=c["bg_panel"],
            fg=c["text_main"],
            selectbackground=c["accent_teal"],
            selectforeground="#f8fafc",
            highlightbackground=c["border"],
            highlightcolor=c["accent_teal"],
        )
        self.details.configure(
            bg=c["bg_panel"],
            fg=c["text_main"],
            insertbackground=c["text_main"],
            highlightbackground=c["border"],
            highlightcolor=c["accent_teal"],
        )

        self.theme_var.set(theme_name.capitalize())
        self._set_status(self.status_var.get(), self._status_kind)

        if persist:
            save_theme_pref(theme_name)

    def _on_theme_change(self, event=None) -> None:
        self._apply_theme(self.theme_var.get().lower())

    def _open_github(self) -> None:
        webbrowser.open(GITHUB_URL)

    def _set_status(self, message: str, kind: str = "default") -> None:
        self._status_kind = kind
        self.status_var.set(message)
        self.status_label.configure(foreground=status_colors(self.theme).get(kind, self.colors["text_muted"]))

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
        if not save_custom_rules(self.saved_custom_rules, CUSTOM_RULES_PATH):
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
        if not save_custom_rules(self.saved_custom_rules, CUSTOM_RULES_PATH):
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
