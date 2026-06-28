# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Tool to bulk-generate personalized event invitation messages (aimed at WhatsApp) from an Excel guest list. It only *drafts* messages — it never sends them. There is no test suite and no linter config.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web app (primary interface)
streamlit run app.py

# Run the batch CLI (writes output/Invite_Drafts.md)
python Invite_draft.py
```

## Two entry points, shared conventions

- **`app.py`** — Streamlit web UI. Three-column flow: select guests → edit template → review/copy/send per-guest. Stateful via `st.session_state`. Designed to run both on local macOS (full features) and Streamlit Community Cloud (cloud-safe equivalents) — see "Platform dependency" below.
- **`Invite_draft.py`** — Stateless batch script. Reads the same inputs and dumps every drafted message to `output/Invite_Drafts.md`. No write-back.

Both scripts independently reimplement `load_config()` and the same Excel-reading conventions — changes to data handling usually need to be mirrored in both files.

## Critical data conventions (easy to break)

- **Excel headers are on row 2**, so all reads use `pd.read_excel(..., header=1)`. The write-back logic in `app.py` (`update_excel_status`) hardcodes `header_row = 2` to match.
- **Required columns** (exact, case-insensitive after `.strip()`): `Addressable Names`, `Add to Invite List?`. Optional: `Phone Number`, `Invited` / `Invited?`.
- **Filtering logic** (app.py): include rows where `Add to Invite List?` == "yes" AND `Invited` != "yes". The CLI only applies the first condition.
- **Template placeholder**: messages use Python `str.format`, so `{name}` is the only substitution. Any literal `{`/`}` in `data/invitation_prompt.md` will break formatting.
- **Markdown → WhatsApp bold**: the template uses `**bold**`; before copying/sending, app.py converts `**` → `*` (WhatsApp's bold syntax). Preserve this conversion when touching copy/link code.

## Data input (app.py)

The guest list comes from either an `st.file_uploader` (preferred — required on the cloud) or, if nothing is uploaded, the `config.json` path read from disk (local dev). Two distinct session-state byte buffers back this:
- **`source_bytes`** — the unchanged list; drives display/filtering and is kept stable during a session so the multiselect options don't shift mid-session. `load_data` is cached on these bytes.
- **`workbook_bytes`** — a working copy mutated in memory by "Mark as Sent" and offered back via download. Reset (and `sent_guests` cleared) whenever a new source is detected.

## Configuration

`config.json` defines all file paths (`guest_list_file`, `invite_image_file`, `prompt_file`, `output_file`). Both scripts fall back to hardcoded `data/...` defaults if it's missing. On the cloud, the uploader supersedes `guest_list_file`.

## Platform dependency

`app.py` degrades gracefully via `IS_DESKTOP = sys.platform == "darwin"`:
- **Image-to-clipboard** (`copy_image_to_clipboard`, shells out to `osascript`) renders **only when `IS_DESKTOP`** — it cannot work on the cloud's Linux container. A **Download Image** button is the cross-platform fallback.
- **Text copy** uses `st.code()`'s built-in browser copy button (no `pyperclip` dependency, works everywhere).
- **"Mark as Sent"** (`update_excel_status`) edits the workbook **in memory** (the cloud filesystem is ephemeral) and exposes a "Download updated guest list" button. On local macOS with an on-disk source it *also* saves back to that file.

## Gitignored at runtime

`output/` and `generated_invites.txt` are gitignored — the `output/` dir is created on demand by `Invite_draft.py`.
