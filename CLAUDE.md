# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Tool to bulk-generate personalized event invitation messages (aimed at WhatsApp) from an Excel guest list. It only *drafts* messages and puts them on the clipboard — it never sends them, and the user opens each WhatsApp chat themselves (phone numbers are deliberately not used). There is no test suite and no linter config.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web app (primary interface)
streamlit run app.py

# Run the batch CLI (writes output/Invite_Drafts.md)
python Invite_draft.py
```

## Entry points, shared conventions

- **`app.py`** — Streamlit web UI. Three-column flow: select guests → edit template & image → copy & send one guest at a time. Stateful via `st.session_state`. Designed to run both on local macOS and Streamlit Community Cloud — see "Platform dependency" below.
- **`invite_helpers.py`** — pure helpers (no Streamlit) used by `app.py`: `render_message`, `whatsapp_to_html` (preview), `build_guest_list_template`, `mark_row` (Excel write-back), `prepare_image`/`image_mime`, `copy_buttons_html`. Checkable from a plain Python shell.
- **`Invite_draft.py`** — Stateless batch script. Reads the same inputs and dumps every drafted message to `output/Invite_Drafts.md`. No write-back.

`app.py` and `Invite_draft.py` independently reimplement `load_config()` and the same Excel-reading conventions — changes to data handling usually need to be mirrored in both files.

## Critical data conventions (easy to break)

- **Excel headers are on row 2** (`HEADER_ROW` in `invite_helpers.py`), so reads use `pd.read_excel(..., header=1)` and `mark_row` looks for headers on row 2. Pandas keeps blank rows, so **Excel row = DataFrame index + 3**.
- **Guests are identified by row index**, not by name: the multiselect options, `current_row` and `sent_rows` are row indices, so duplicate `Addressable Names` stay distinct (duplicates are labelled with their Excel row). `mark_row` checks the name in that row before writing and always uses the **first** sheet (`wb.worksheets[0]`, matching pandas — not `wb.active`).
- **Required columns** (case-insensitive after `.strip()`): `Addressable Names`, `Add to Invite List?`. Optional: `Invited` / `Invited?` (`mark_row` adds `Invited?` if missing). All other columns, including any phone number, are ignored.
- **Filtering logic** (app.py): include rows where `Add to Invite List?` == "yes" AND `Invited` != "yes" AND the name is non-empty. The CLI only applies the first condition.
- **Template placeholder**: `{name}` is substituted with `str.replace` (in both scripts), so any other `{`/`}` in the template is harmless. Do not switch back to `str.format`.
- **Templates are written in WhatsApp-native formatting** (`*bold*`, `_italic_`, `~strike~`, ```` ```mono``` ````, `` `code` ``, `> quote`) — what's typed is what's pasted. Legacy Markdown `**bold**` is converted to `*bold*` when rendering (both scripts). The preview (`whatsapp_to_html` + `st.html`) mimics WhatsApp's rules; never render messages with `st.markdown` (Markdown treats `*x*` as italic and `$…$` as LaTeX).

## Data input (app.py)

The guest list comes from either an `st.file_uploader` (key `guest_upload`; preferred — required on the cloud) or, if nothing is uploaded, the `config.json` path read from disk (local dev). Session-state buffers:
- **`source_bytes`** — the unchanged list; drives display/filtering and is kept stable during a session so the guest options don't shift mid-session. `load_data` is cached on these bytes.
- **`workbook_bytes`** — a working copy mutated in memory by "Mark sent"/"Undo" and offered back via download. Reset (with `sent_rows`, `selected_rows`, `current_row`) whenever a new source is detected.
- **`last_saved_bytes`** — what "Mark sent" last wrote to the on-disk list (local only), so the app doesn't mistake its own write for a new source.

The template text lives in `st.session_state.template_text` (the text area's key); the template uploader's `on_change` callback replaces it. The invite image comes from the image uploader, else `invite_image_file`.

## Streamlit gotcha: the guest navigator

The send column's selectbox (`key="current_row"`) has ✅/⏳ labels, so Streamlit rebuilds it (new widget id) whenever a guest is marked/unmarked or the selection changes — and then falls back to a stale value. That's why `app.py` re-assigns `st.session_state.current_row` on **every** run before rendering the selectbox. Keep that if you touch the navigator.

## Configuration

`config.json` defines all file paths (`guest_list_file`, `invite_image_file`, `prompt_file`, `output_file`). Both scripts fall back to hardcoded `data/...` defaults if it's missing. On the cloud, the uploaders supersede these.

## Platform dependency

- **Copying** (image and text) uses the browser Clipboard API inside a `components.html` iframe (`copy_buttons_html`; Streamlit grants the iframe `clipboard-write`). Works locally and on the cloud — no `osascript`/`pyperclip`. Browsers only put **PNG** on the clipboard, so `prepare_image` converts (and caps at 2048 px). The clipboard holds one item, so image and text are copied separately.
- `IS_DESKTOP = sys.platform == "darwin"` now only gates **disk writes**: "Mark sent" also saves to the on-disk guest list (after a one-time `(backup)` copy per session, since openpyxl drops images/charts), and "Save as default template" writes `prompt_file`. Both are hidden/skipped on the cloud, whose filesystem is ephemeral and shared by every visitor.

## Gitignored at runtime

`output/` and `generated_invites.txt` are gitignored — the `output/` dir is created on demand by `Invite_draft.py`.
