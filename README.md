# CAT Regex Protector

Small GUI tool for generating regex rules for CAT-tool protection workflows, plus a general-purpose regex builder/tester. Ships as a Tkinter desktop app and a Streamlit web app, both built on the shared regex logic in `regex_core.py`. Each app has two tabs:

- **CAT Tools** — generate narrow regex rules that protect small non-translatable tokens (`<b>`, `{0}`, `%s`, ICU plurals) inside a CAT tool.
- **Generic Regex** — build or test a regex for matching whole sections of general text (log lines, documents, code) outside CAT-tool workflows. Pick a preset (email, URL, IP, date, whole line, paragraph, quoted/HTML block, etc.), or generate one from a small typed segment using the same shape-detection logic as the CAT tab. Paste sample text to see matches highlighted live.

## Run (desktop)

```bash
pip install -r requirements.txt
python RegexAssist.py
```

Uses [ttkbootstrap](https://ttkbootstrap.readthedocs.io/) for a modern, rounded dark theme on top of Tkinter.

## Run (web)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The web app reads/writes the same `custom_regex_rules.json` and `Plural_form_regex.txt` files as the desktop app when run from the same folder, so a custom rule saved in one shows up in the other.

## Build a standalone .exe

```bash
python build_exe.py
```

Produces `dist/CAT Regex Protector.exe` (see `launcher.py` for the entry point used).

## Theme

Both apps ship a dark and a light theme (colors defined once in `regex_core.py`) with a switcher in the header, defaulting to dark. The desktop app remembers your choice in `theme_prefs.json` next to the exe; the web app remembers it for the current browser session.

## Input Guidance

- In the input box, include full code/token wrappers.
- Example: use `[abc]` instead of only `abc`.

## Generate Modes

- `generic match`
  - Builds generic structural regex based on input shape.
  - Examples:
    - `[abc]` -> `\[[^\]]*?\]`
    - `${abc}` -> `\$\{[^{}]*?\}`
    - `$[abc]` -> `\$\[[^\]]*?\]`
    - `%1$d` -> `%\d+\$[A-Za-z]`
    - `<b/>` -> `<[^/][^>]*?/>`
    - `\n` -> `\\n`
- `exact match`
  - Escapes and matches the exact input.
- `word-only`
  - Preserves punctuation exactly, generalizes alphabetic chunks.
- `number-only`
  - Preserves punctuation exactly, generalizes alphanumeric chunks to `\d+`.
- `custom regex`
  - Shows your saved custom regex library.
  - Use this when built-in patterns do not fit your CAT workflow.

## ICU Plural Behavior

When input is an ICU plural string and mode is `generic match`, the app outputs only these four rules in this order:

1. `\{\s*(\w+),\s*(\w+),\s*[^{}]*\{`
2. `(\}\s*?(\w+)\s*?\{)`
3. `\}+`
4. `\{+`

Notes:
- Rule 1 must be first.
- Rule 2 must be second.
- Rule 3 must be third.
- Rule 4 should come after `{+.*?}+` if you use that extra rule in your CAT setup.
- If you load a custom ICU rule set via `Load ICU TXT Rules` (or the default cheat-sheet path), that loaded set replaces these four built-in rules for ICU plural input until the app is restarted or a new file is loaded.

## UI Workflow

1. Enter source token/content in `Input`.
2. Choose `Generate mode`.
3. Click `Generate Regex`.
4. Select a rule in the list.
5. Click `Copy Selected Rule` and paste into your CAT tool.

## Custom Regex Library

Both tabs share one library file, `custom_regex_rules.json`, but each tab only shows the rules it saved (tagged `cat` or `generic` internally) — the CAT Tools library and the Generic Regex library are separate views onto the same file.

- Save a rule:
  - **CAT Tools:** generate a rule, select it from the list, click `Save Selected as Custom`.
  - **Generic Regex:** name the current pattern under "Save current pattern as", click `Save to Library`.
- Use saved rules:
  - **CAT Tools:** switch mode to `custom regex`, click `Generate Regex` to list them.
  - **Generic Regex:** pick one from "My Library", click `Load from Library`.
- Delete a rule:
  - **CAT Tools:** in `custom regex` mode, select a rule and click `Delete Custom Rule`.
  - **Generic Regex:** pick one from "My Library", click `Delete from Library`.
- Flagging a rule as not working:
  - Toggle a saved rule's status between Working and Flagged (`Toggle Working/Flagged` in CAT Tools; `Toggle Working/Flagged` next to a loaded rule in Generic Regex). Flagging prompts for an optional note explaining the problem.
  - If you flag a rule while specific input/sample text is active, that exact text is remembered — the rule won't be auto-proposed (CAT Tools' `custom regex` mode) or loadable (Generic Regex' `Load from Library`) again for that *exact* text, though it still appears for other input.
