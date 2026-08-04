"""Web version of the CAT Regex Protector, built on the same regex_core logic
used by the Tkinter desktop app (RegexAssist.py). Run with:

    streamlit run streamlit_app.py
"""
import datetime
import html
import os
import re

import streamlit as st

from regex_core import (
    DEFAULT_THEME,
    FONT_FAMILY,
    GENERIC_PRESETS,
    GENERIC_SEGMENT_MODES,
    MODULE_CAT,
    MODULE_GENERIC,
    STATUS_FLAGGED,
    STATUS_WORKING,
    THEMES,
    RegexRule,
    SavedRegex,
    build_icu_plural_rules,
    build_mode_rules,
    find_matches,
    is_icu_plural_message,
    load_saved_custom_rules,
    parse_custom_rules_from_text,
    rules_for_module,
    save_custom_rules,
)

APP_DIR = os.path.dirname(__file__)
CUSTOM_RULES_PATH = os.path.join(APP_DIR, "custom_regex_rules.json")
DEFAULT_ICU_RULE_PATH = os.path.join(APP_DIR, "Plural_form_regex.txt")
FAVICON_PATH = os.path.join(APP_DIR, "favicon.png")
README_PATH = os.path.join(APP_DIR, "README.md")
GITHUB_URL = "https://github.com/kevinjbrownbcn-png/RegexAssist"
GITHUB_README_URL = f"{GITHUB_URL}/blob/main/README.md"

MODES = ["generic match", "exact match", "word-only", "number-only", "custom regex"]

st.set_page_config(
    page_title="CAT Regex Protector",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else "🛡️",
    layout="wide",
)


def _inject_theme_css(theme: str) -> None:
    c = THEMES[theme]
    st.markdown(
        f"""
        <style>
        :root {{
            --primary-color: {c['accent_teal']};
            --background-color: {c['bg_app']};
            --secondary-background-color: {c['bg_panel']};
            --text-color: {c['text_main']};
        }}
        .stApp {{
            background-color: {c['bg_app']};
            color: {c['text_main']};
            font-family: {FONT_FAMILY};
        }}
        [data-testid="stHeader"] {{
            background-color: {c['bg_header']};
        }}
        [data-testid="stExpander"] {{
            background-color: {c['bg_panel']};
            border: 1px solid {c['border']};
            border-radius: 8px;
        }}
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="base-input"] {{
            background-color: {c['bg_panel']} !important;
            border-color: {c['border']} !important;
            color: {c['text_main']} !important;
        }}
        code, pre {{
            background-color: {c['bg_panel']} !important;
            color: {c['text_main']} !important;
        }}
        hr {{
            border-color: {c['border']};
        }}
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFileUploaderDropzone"],
        [data-testid="stPopover"] > div > button {{
            background-color: {c['bg_panel']} !important;
            color: {c['text_main']} !important;
            border-color: {c['border']} !important;
        }}
        .stButton > button[kind="primary"] {{
            background-color: {c['accent_teal']} !important;
            color: #f8fafc !important;
            border-color: {c['accent_teal']} !important;
        }}
        a {{
            color: {c['accent_teal']};
        }}
        .catregex-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 4px 4px 4px;
            margin-top: 24px;
            border-top: 1px solid {c['border']};
            font-family: {FONT_FAMILY};
        }}
        .catregex-footer .left {{
            color: {c['text_muted']};
            font-size: 0.85rem;
        }}
        .catregex-footer .right a {{
            color: {c['accent_teal']};
            font-weight: 700;
            text-decoration: none;
            margin-left: 18px;
            font-size: 0.85rem;
        }}
        .catregex-footer .right a:hover {{
            text-decoration: underline;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _load_default_icu_rules() -> list[RegexRule]:
    try:
        with open(DEFAULT_ICU_RULE_PATH, "r", encoding="utf-8") as file_handle:
            return parse_custom_rules_from_text(file_handle.read())
    except OSError:
        return []


def _render_highlighted_html(text: str, matches: list[re.Match], accent: str) -> str:
    pieces = []
    last = 0
    for m in matches:
        pieces.append(html.escape(text[last : m.start()]))
        pieces.append(
            f'<mark style="background:{accent};color:#f8fafc;border-radius:3px;padding:0 2px;">'
            f"{html.escape(text[m.start() : m.end()])}</mark>"
        )
        last = m.end()
    pieces.append(html.escape(text[last:]))
    return "".join(pieces)


if "theme" not in st.session_state:
    st.session_state.theme = DEFAULT_THEME
if "rules" not in st.session_state:
    st.session_state.rules = []
if "custom_icu_rules" not in st.session_state:
    st.session_state.custom_icu_rules = _load_default_icu_rules()
if "saved_custom_rules" not in st.session_state:
    st.session_state.saved_custom_rules = load_saved_custom_rules(CUSTOM_RULES_PATH)

_inject_theme_css(st.session_state.theme)

title_col, theme_col = st.columns([5, 1])
with title_col:
    st.title("Regex Builder")
with theme_col:
    theme_choice = st.segmented_control(
        "Theme",
        ["Dark", "Light"],
        default=st.session_state.theme.capitalize(),
        label_visibility="collapsed",
    )
    new_theme = (theme_choice or st.session_state.theme.capitalize()).lower()
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

cat_tab, generic_tab = st.tabs(["CAT Tools", "Generic Regex"])

with cat_tab:
    st.caption(
        "Enter content to protect (for example `<b>`, `<i>`, `{0}`, `%s`, ICU plural messages). "
        "Generate separate rules and copy them one-by-one for CAT tool regex settings."
    )

    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        user_input = st.text_input("Input", placeholder="e.g. [abc] — include the full code, not just abc")
    with top_col2:
        mode = st.selectbox("Generate mode", MODES)

    generate_col, clear_col = st.columns([1, 1])
    generate_clicked = generate_col.button("Generate Regex", type="primary", use_container_width=True)
    clear_clicked = clear_col.button("Clear", use_container_width=True)

    if clear_clicked:
        st.session_state.rules = []
        st.rerun()

    if generate_clicked:
        text = user_input.strip()
        if not text and mode != "custom regex":
            st.warning("Please enter text to generate regex.")
        elif mode == "custom regex":
            st.session_state.rules = rules_for_module(
                st.session_state.saved_custom_rules, MODULE_CAT, exclude_sample=text
            )
            if not st.session_state.rules:
                st.warning(
                    "No saved custom regex rules yet. Use 'Save as custom' below after generating a rule."
                )
        elif mode == "generic match" and is_icu_plural_message(text):
            st.session_state.rules = (
                list(st.session_state.custom_icu_rules)
                if st.session_state.custom_icu_rules
                else build_icu_plural_rules()
            )
            st.success(f"Generated {len(st.session_state.rules)} ICU plural rules.")
        else:
            st.session_state.rules = build_mode_rules(text, mode)
            st.success(f"Generated {len(st.session_state.rules)} rule(s).")

    st.divider()

    list_col, detail_col = st.columns([1, 2])

    with list_col:
        st.subheader("Generated rules")
        if not st.session_state.rules:
            st.caption("Nothing generated yet.")
        else:
            labels = [f"{idx}. {rule.name}" for idx, rule in enumerate(st.session_state.rules, start=1)]
            selected_label = st.radio("Select a rule", labels, label_visibility="collapsed")
            selected_idx = labels.index(selected_label)

    with detail_col:
        st.subheader("Selected rule details")
        if st.session_state.rules:
            selected_rule = st.session_state.rules[selected_idx]
            st.markdown(f"**Rule:** {selected_rule.name}")
            st.code(selected_rule.pattern, language="regex")
            st.markdown(f"**Purpose:** {selected_rule.purpose}")

            with st.popover("Copy details"):
                st.caption("Full rule block — use the copy icon in the corner.")
                st.code(
                    f"Rule: {selected_rule.name}\nRegex: {selected_rule.pattern}\nPurpose: {selected_rule.purpose}",
                    language=None,
                )

            if st.button("Save as custom"):
                if any(r.pattern == selected_rule.pattern for r in st.session_state.saved_custom_rules):
                    st.warning("Custom regex already saved.")
                else:
                    custom_rule = SavedRegex(
                        name=selected_rule.name,
                        pattern=selected_rule.pattern,
                        purpose=f"Custom: {selected_rule.purpose}",
                        module=MODULE_CAT,
                    )
                    st.session_state.saved_custom_rules.append(custom_rule)
                    if save_custom_rules(st.session_state.saved_custom_rules, CUSTOM_RULES_PATH):
                        st.success(f"Saved custom regex: {custom_rule.name}")
                    else:
                        st.session_state.saved_custom_rules.pop()
                        st.error("Could not save custom regex rules to disk.")
        else:
            st.caption("Generate a rule to see its details here.")

    st.divider()

    with st.expander("Custom regex library"):
        cat_saved = rules_for_module(st.session_state.saved_custom_rules, MODULE_CAT)
        if not cat_saved:
            st.caption("No custom regex rules saved yet.")
        for idx, rule in enumerate(cat_saved):
            badge = "🚩 Flagged" if rule.status == STATUS_FLAGGED else "✅ Working"
            st.markdown(f"**{rule.name}** — {badge}")
            st.code(rule.pattern, language="regex")
            st.caption(rule.purpose)
            note_input = st.text_input(
                "Note",
                value=rule.note,
                key=f"cat_note_{idx}",
                label_visibility="collapsed",
                placeholder="Note: why doesn't this work as expected? (optional)",
            )
            toggle_col, delete_col = st.columns([1, 1])
            with toggle_col:
                toggle_label = "Mark as Working" if rule.status == STATUS_FLAGGED else "Flag as Not Working"
                if st.button(toggle_label, key=f"cat_toggle_{idx}", use_container_width=True):
                    if rule.status == STATUS_WORKING:
                        rule.status = STATUS_FLAGGED
                        rule.note = note_input.strip()
                        sample = user_input.strip()
                        if sample and sample not in rule.flagged_samples:
                            rule.flagged_samples.append(sample)
                    else:
                        rule.status = STATUS_WORKING
                        rule.note = ""
                        rule.flagged_samples = []
                    save_custom_rules(st.session_state.saved_custom_rules, CUSTOM_RULES_PATH)
                    st.rerun()
            with delete_col:
                if st.button("Delete", key=f"cat_delete_{idx}", use_container_width=True):
                    st.session_state.saved_custom_rules.remove(rule)
                    save_custom_rules(st.session_state.saved_custom_rules, CUSTOM_RULES_PATH)
                    st.rerun()
            st.divider()

    with st.expander("Load custom ICU rule set from TXT"):
        st.caption(
            "Overrides the 4 built-in ICU plural rules for ICU plural input in 'generic match' mode. "
            "Expected line formats: `regex`, `name|regex|purpose`, or `regex - notes`."
        )
        uploaded = st.file_uploader("ICU rules TXT file", type=["txt"])
        if uploaded is not None:
            parsed = parse_custom_rules_from_text(uploaded.getvalue().decode("utf-8"))
            if parsed:
                st.session_state.custom_icu_rules = parsed
                st.success(f"Loaded {len(parsed)} custom ICU rules.")
            else:
                st.warning("No valid ICU rules found in file.")
        if st.session_state.custom_icu_rules:
            st.caption(f"Currently loaded: {len(st.session_state.custom_icu_rules)} ICU rules.")

with generic_tab:
    st.caption(
        "Build or test a regex for matching whole sections of general text (logs, documents, code) "
        "outside CAT-tool workflows — not for protecting non-translatables."
    )

    if "generic_pattern" not in st.session_state:
        st.session_state.generic_pattern = ""
    if "generic_purpose" not in st.session_state:
        st.session_state.generic_purpose = ""
    if "generic_loaded_saved_name" not in st.session_state:
        st.session_state.generic_loaded_saved_name = None
    current_sample = st.session_state.get("generic_sample", "")

    preset_col, segment_col = st.columns(2)
    with preset_col:
        st.markdown("**Preset**")
        preset_name = st.selectbox(
            "Preset", [""] + [r.name for r in GENERIC_PRESETS], label_visibility="collapsed"
        )
        if st.button("Load Preset", use_container_width=True):
            preset = next((r for r in GENERIC_PRESETS if r.name == preset_name), None)
            if preset:
                st.session_state.generic_pattern = preset.pattern
                st.session_state.generic_purpose = preset.purpose
                st.session_state.generic_loaded_saved_name = None
                st.rerun()
            else:
                st.warning("Select a preset first.")

    with segment_col:
        st.markdown("**Or generate from a sample segment**")
        seg_input_col, seg_mode_col = st.columns([2, 1])
        segment = seg_input_col.text_input(
            "Segment", placeholder="e.g. john@example.com", label_visibility="collapsed"
        )
        segment_mode = seg_mode_col.selectbox(
            "Segment mode", GENERIC_SEGMENT_MODES, label_visibility="collapsed"
        )
        if st.button("Generate from Segment", use_container_width=True):
            if segment.strip():
                rule = build_mode_rules(segment.strip(), segment_mode)[0]
                st.session_state.generic_pattern = rule.pattern
                st.session_state.generic_purpose = rule.purpose
                st.session_state.generic_loaded_saved_name = None
                st.rerun()
            else:
                st.warning("Enter a sample segment first.")

    generic_saved = rules_for_module(st.session_state.saved_custom_rules, MODULE_GENERIC)
    lib_col, save_col = st.columns(2)
    with lib_col:
        st.markdown("**My Library**")
        lib_name = st.selectbox(
            "My Library", [""] + [r.name for r in generic_saved], label_visibility="collapsed"
        )
        if st.button("Load from Library", use_container_width=True):
            saved_rule = next((r for r in generic_saved if r.name == lib_name), None)
            if not saved_rule:
                st.warning("Select a saved rule first.")
            elif saved_rule.is_flagged_for(current_sample):
                st.warning(
                    f"'{saved_rule.name}' was flagged as not working for this exact sample text — not loading."
                )
            else:
                st.session_state.generic_pattern = saved_rule.pattern
                st.session_state.generic_purpose = saved_rule.purpose
                st.session_state.generic_loaded_saved_name = saved_rule.name
                st.rerun()

    with save_col:
        st.markdown("**Save current pattern as**")
        save_name = st.text_input(
            "Save current pattern as", label_visibility="collapsed", placeholder="Name this pattern..."
        )
        if st.button("Save to Library", use_container_width=True):
            name = save_name.strip()
            current_pattern = st.session_state.generic_pattern.strip()
            if not name:
                st.warning("Enter a name for this pattern first.")
            elif not current_pattern:
                st.warning("Enter or generate a pattern first.")
            elif any(
                r.pattern == current_pattern and r.module == MODULE_GENERIC
                for r in st.session_state.saved_custom_rules
            ):
                st.warning("This pattern is already saved.")
            else:
                custom_rule = SavedRegex(
                    name=name,
                    pattern=current_pattern,
                    purpose=st.session_state.generic_purpose or "User saved custom regex.",
                    module=MODULE_GENERIC,
                )
                st.session_state.saved_custom_rules.append(custom_rule)
                if save_custom_rules(st.session_state.saved_custom_rules, CUSTOM_RULES_PATH):
                    st.success(f"Saved to library: {custom_rule.name}")
                    st.rerun()
                else:
                    st.session_state.saved_custom_rules.pop()
                    st.error("Could not save custom regex rules to disk.")

    pattern = st.text_input("Pattern", key="generic_pattern")
    if st.session_state.generic_purpose:
        st.caption(st.session_state.generic_purpose)
    if pattern:
        st.code(pattern, language="regex")

    loaded_rule = next(
        (r for r in generic_saved if r.name == st.session_state.generic_loaded_saved_name), None
    )
    if loaded_rule:
        badge = "🚩 Flagged" if loaded_rule.status == STATUS_FLAGGED else "✅ Working"
        st.caption(f"Loaded from library: **{loaded_rule.name}** — {badge}")
        flag_note = st.text_input(
            "Flag note",
            value=loaded_rule.note,
            key="generic_flag_note",
            label_visibility="collapsed",
            placeholder="Note: why doesn't this work as expected? (optional)",
        )
        toggle_label = "Mark as Working" if loaded_rule.status == STATUS_FLAGGED else "Flag as Not Working"
        if st.button(toggle_label):
            if loaded_rule.status == STATUS_WORKING:
                loaded_rule.status = STATUS_FLAGGED
                loaded_rule.note = flag_note.strip()
                if current_sample.strip() and current_sample.strip() not in loaded_rule.flagged_samples:
                    loaded_rule.flagged_samples.append(current_sample.strip())
            else:
                loaded_rule.status = STATUS_WORKING
                loaded_rule.note = ""
                loaded_rule.flagged_samples = []
            save_custom_rules(st.session_state.saved_custom_rules, CUSTOM_RULES_PATH)
            st.rerun()

    sample = st.text_area(
        "Sample text", height=220, placeholder="Paste text to test the pattern against...", key="generic_sample"
    )

    if pattern and sample:
        try:
            matches = find_matches(pattern, sample)
        except re.error as exc:
            st.error(f"Invalid regex: {exc}")
        else:
            if matches:
                st.success(f"{len(matches)} match(es) found.")
            else:
                st.warning("No matches found.")
            c = THEMES[st.session_state.theme]
            highlighted = _render_highlighted_html(sample, matches, c["accent_teal"])
            st.markdown(
                f'<div style="white-space:pre-wrap; font-family:Consolas,monospace; '
                f'background:{c["bg_panel"]}; color:{c["text_main"]}; border:1px solid {c["border"]}; '
                f'border-radius:6px; padding:12px; max-height:400px; overflow:auto;">{highlighted}</div>',
                unsafe_allow_html=True,
            )
    elif pattern or sample:
        st.caption("Enter both a pattern and sample text to see matches highlighted.")

with st.expander("README"):
    try:
        with open(README_PATH, "r", encoding="utf-8") as file_handle:
            st.markdown(file_handle.read())
    except OSError:
        st.caption("README.md not found next to streamlit_app.py.")

_year = datetime.date.today().year
st.markdown(
    f"""
    <div class="catregex-footer">
        <div class="left">© {_year} CAT Regex Protector | Regex Builder for CAT Tools & General Search</div>
        <div class="right">
            <a href="{GITHUB_README_URL}" target="_blank">README</a>
            <a href="{GITHUB_URL}" target="_blank">GitHub</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
