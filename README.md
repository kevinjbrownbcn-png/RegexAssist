# CAT Regex Protector

Small GUI tool for generating regex rules for CAT-tool protection workflows. Ships as a Tkinter desktop app and a Streamlit web app, both built on the shared regex logic in `regex_core.py`.

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

- Save rule:
  - Generate a rule in any mode.
  - Select it from the list.
  - Click `Save Selected as Custom`.
- Use saved rules:
  - Switch mode to `custom regex`.
  - Click `Generate Regex` to list saved custom rules.
- Delete rule:
  - While in `custom regex` mode, select a rule and click `Delete Custom Rule`.
- Storage:
  - Saved custom rules are stored in `custom_regex_rules.json` next to `regex-app.py`.
