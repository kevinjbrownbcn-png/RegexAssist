"""Web version of the CAT Regex Protector, built on the same regex_core logic
used by the Tkinter desktop app (RegexAssist.py). Run with:

    streamlit run streamlit_app.py
"""
import os

import streamlit as st

from regex_core import (
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

MODES = ["generic match", "exact match", "word-only", "number-only", "custom regex"]

st.set_page_config(
    page_title="CAT Regex Protector",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else "🛡️",
    layout="wide",
)


def _load_default_icu_rules() -> list[RegexRule]:
    try:
        with open(DEFAULT_ICU_RULE_PATH, "r", encoding="utf-8") as file_handle:
            return parse_custom_rules_from_text(file_handle.read())
    except OSError:
        return []


if "rules" not in st.session_state:
    st.session_state.rules = []
if "custom_icu_rules" not in st.session_state:
    st.session_state.custom_icu_rules = _load_default_icu_rules()
if "saved_custom_rules" not in st.session_state:
    st.session_state.saved_custom_rules = load_saved_custom_rules(CUSTOM_RULES_PATH)


st.title("Regex Builder for CAT Tools")
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
