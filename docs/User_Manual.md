# CAT Regex Protector — User Manual

CAT Regex Protector (RegexAssist) is a small tool for building regular expressions for two related but different jobs:

- **Protecting non-translatable content** inside a CAT (Computer-Assisted Translation) tool — small tokens like `<b>`, `{0}`, `%s`, or ICU plural syntax that must survive translation untouched.
- **Building or testing general-purpose regex** against everyday text — log lines, documents, code — using presets or your own sample text.

It's available as a desktop app and a web (Streamlit) app, both built on the same underlying logic, so a regex generated one way behaves identically the other way. Custom rules you save are shared between them when run from the same folder.

---

## 1. Getting started

### Desktop app

Run the pre-built executable (`CAT Regex Protector.exe`), or from source:

```bash
pip install -r requirements.txt
python RegexAssist.py
```

The desktop app uses `ttkbootstrap` for a modern rounded look on top of Tkinter.

### Web app

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Opens in your browser. If run from the same folder as the desktop app, it reads and writes the same `custom_regex_rules.json` and `Plural_form_regex.txt` files — a custom rule saved in one shows up in the other.

### Building a standalone .exe

```bash
python build_exe.py
```

Produces `dist/CAT Regex Protector.exe`, a single-file build with `README.md` and `Plural_form_regex.txt` bundled inside it (read-only) and `icon.ico` as the app icon. Custom rules and your theme preference are still written next to the exe at runtime, so they persist across launches. (Note: as of this manual, `build_exe.py` only produces the one-file build — no separate one-dir or debug variants yet.)

---

## 2. The interface

Both apps share the same layout:

- **Header** — app title ("Regex Builder") and a **theme switcher** (Dark/Light), defaulting to Dark. The desktop app remembers your choice in `theme_prefs.json` next to the exe; the web app remembers it for the current browser session only.
- **Two tabs** — **CAT Tools** and **Generic Regex** (described below).
- **Footer** — copyright line on the left, and README/GitHub links on the right.

> **Known issue:** switching to Light theme currently makes a few labels (the inactive tab name, the "Pattern" and "Sample text" field labels) very low-contrast or invisible on both the desktop and web versions. Worth fixing, but doesn't block using the app — the fields themselves still work, just without visible labels.

---

## 3. CAT Tools tab

Use this tab to generate narrow regex rules that protect small non-translatable tokens inside a CAT tool.

### Input guidance

Always include the **full code/token wrapper**, not just its contents. For example, enter `[abc]`, not `abc`.

### Workflow

1. Enter the source token/content in **Input**.
2. Choose a **Generate mode** (see below).
3. Click **Generate Regex**.
4. Select a rule from the generated list to see its pattern and purpose.
5. Click **Copy Selected Rule** (desktop) or use the **Copy details** popover (web), then paste into your CAT tool's regex settings.

### Generate modes

| Mode | What it does |
|---|---|
| `generic match` | Builds a structural regex based on the shape of your input. Examples: `[abc]` → `\[[^\]]*?\]`, `${abc}` → `\$\{[^{}]*?\}`, `$[abc]` → `\$\[[^\]]*?\]`, `%1$d` → `%\d+\$[A-Za-z]`, `<b/>` → `<[^/][^>]*?/>`, `\n` → `\\n` |
| `exact match` | Escapes and matches the exact input, nothing else. |
| `word-only` | Preserves punctuation exactly, generalizes alphabetic chunks to match any letters. |
| `number-only` | Preserves punctuation exactly, generalizes alphanumeric chunks to `\d+`. |
| `custom regex` | Shows your saved custom rule library instead of generating anything new — use this when the built-in modes don't fit your CAT workflow. |

### ICU plural messages

If your input is recognized as an ICU plural string (starts with something like `{count, plural,`) and mode is `generic match`, the app outputs exactly four ordered rules instead of the usual generic-match output:

1. Plural opening string — must stay first.
2. Plural internal separators — must stay second.
3. Stray closing braces — third.
4. Stray opening braces — should come after `{+.*?}+` if you use that extra rule in your CAT setup.

If you've loaded a custom ICU rule set (see below), that replaces these four built-in rules for ICU input until you restart the app or load a different file.

### Loading a custom ICU rule set

**Load ICU TXT Rules** (desktop button) / **Load custom ICU rule set from TXT** (web expander) lets you override the four built-in ICU rules with your own, from a `.txt` file. Accepted line formats:

- `regex` (pattern only)
- `name|regex|purpose`
- `regex - notes`

The app also auto-loads a default cheat sheet (`Plural_form_regex.txt`) at startup if present.

---

## 4. Generic Regex tab

Use this tab to build or test a regex for matching whole sections of general text — not for CAT-tool token protection.

### Three ways to get a pattern

1. **Pick a preset** — choose from the built-in list (see Appendix) and click **Load Preset**.
2. **Generate from a sample segment** — type a short example (e.g. `john@example.com`) with a segment mode (`generic match`, `exact match`, `word-only`, `number-only`) and click **Generate from Segment**. Uses the same shape-detection logic as the CAT Tools tab.
3. **Load from your saved library** — pick a previously saved pattern from **My Library** and click **Load from Library**.

### Testing a pattern

Paste sample text into **Sample text**. If both a pattern and sample text are present, matches are highlighted live in the text — no extra button needed on the web app; on the desktop app, click **Highlight Matches**.

### Saving a pattern

Name it under **Save current pattern as**, then click **Save to Library**.

---

## 5. Custom regex library

Both tabs share one library file (`custom_regex_rules.json`), but each tab only shows the rules it saved — internally tagged `cat` or `generic`. The CAT Tools library and the Generic Regex library are separate views onto the same file.

| Action | CAT Tools | Generic Regex |
|---|---|---|
| **Save a rule** | Generate a rule, select it, click "Save Selected as Custom" | Name the current pattern, click "Save to Library" |
| **Use saved rules** | Switch mode to `custom regex`, click "Generate Regex" | Pick one from "My Library", click "Load from Library" |
| **Delete a rule** | In `custom regex` mode, select and click "Delete Custom Rule" | Pick one from "My Library", click "Delete from Library" |
| **Flag as not working** | Select a saved rule, "Toggle Working/Flagged" | Next to a loaded rule, "Toggle Working/Flagged" |

Flagging prompts for an optional note explaining the problem. If you flag a rule while specific input/sample text is active, that exact text is remembered — the rule won't be auto-proposed or loadable again for that *exact* text (though it still appears normally for other input).

---

## 6. Troubleshooting

- **"Invalid regex" error while testing a Generic Regex pattern** — your pattern has a syntax error; check brackets/escaping. The error message from Python's `re` module is shown directly.
- **A saved custom rule doesn't appear when generating** — it may be flagged as not working for the exact input text you're using. Rules flagged for one specific sample are hidden only for that sample, not globally.
- **Custom rules don't show up in the other app (desktop vs web)** — make sure both are being run from the same folder; the shared library file is resolved relative to the app's own directory.
- **Web app "forgets" your theme after closing the tab** — expected; the web app only remembers theme choice for the current browser session, not permanently. The desktop app persists it to `theme_prefs.json`.

---

## Appendix: built-in Generic Regex presets

| Preset | Purpose |
|---|---|
| Email address | Matches a single email address, including multi-part domains like `.co.uk` |
| URL (http/https) | Matches an http(s) URL up to the next whitespace or quote |
| IPv4 address | Matches an IPv4 address |
| Date (YYYY-MM-DD) | Matches an ISO-style date |
| Date (D/M/Y or M/D/Y) | Matches a slash-separated date |
| Time (HH:MM[:SS]) | Matches a 24h or 12h time value |
| Phone number (loose) | Loosely matches international/local phone numbers — may also catch dates/IDs with a similar shape |
| Hex color code | Matches a 3- or 6-digit hex color |
| Whole line | Matches an entire line of text |
| Paragraph (blank-line separated) | Matches a block of text up to the next blank line |
| Quoted string (single line) | Matches double-quoted text on one line |
| Quoted block (multi-line) | Matches double-quoted text that can span multiple lines |
| HTML/XML tag with content | Matches an opening tag, its content, and the matching closing tag |
| Trailing whitespace | Matches indentation-breaking trailing spaces/tabs at line end |

---

*This manual covers the app as of the current codebase. Screenshots were intentionally omitted from this version — see the project's build notes if a visual version is added later.*
