"""Web version of the CAT Regex Protector, built on the same regex_core logic
used by the Tkinter desktop app (RegexAssist.py). Run with:

    streamlit run streamlit_app.py
"""
import datetime
import os

import streamlit as st

from regex_core import (
    DEFAULT_THEME,
    FONT_FAMILY,
    THEMES,
    RegexRule,
    build_icu_plural_rules,
    build_mode_rules,
    is_icu_plural_message,
    load_saved_custom_rules,
    parse_custom_rules_from_text,
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
    st.title("Regex Builder for CAT Tools")
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
        st.session_state.rules = list(st.session_state.saved_custom_rules)
        if not st.session_state.rules:
            st.warning("No saved custom regex rules yet. Use 'Save as custom' below after generating a rule.")
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
                custom_rule = RegexRule(
                    name=selected_rule.name,
                    pattern=selected_rule.pattern,
                    purpose=f"Custom: {selected_rule.purpose}",
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
    if not st.session_state.saved_custom_rules:
        st.caption("No custom regex rules saved yet.")
    for idx, rule in enumerate(st.session_state.saved_custom_rules):
        rule_col, delete_col = st.columns([5, 1])
        with rule_col:
            st.markdown(f"**{rule.name}**")
            st.code(rule.pattern, language="regex")
            st.caption(rule.purpose)
        with delete_col:
            if st.button("Delete", key=f"delete_custom_{idx}"):
                st.session_state.saved_custom_rules.pop(idx)
                save_custom_rules(st.session_state.saved_custom_rules, CUSTOM_RULES_PATH)
                st.rerun()

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
        <div class="left">© {_year} CAT Regex Protector | Regex Builder for CAT Tools</div>
        <div class="right">
            <a href="{GITHUB_README_URL}" target="_blank">README</a>
            <a href="{GITHUB_URL}" target="_blank">GitHub</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
