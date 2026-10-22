import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import io
import json
import os
import shutil
import sys

from invite_helpers import (
    HEADER_ROW,
    build_guest_list_template,
    copy_buttons_html,
    image_mime,
    mark_row,
    prepare_image,
    render_message,
    whatsapp_to_html,
)

# True on local macOS, where changes are also saved back to the files on disk.
# False on Streamlit Community Cloud / Linux, whose filesystem is ephemeral and
# shared by every visitor, so downloads are the only way to keep changes.
IS_DESKTOP = sys.platform == "darwin"

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Used when the configured template file is missing.
FALLBACK_TEMPLATE = (
    "Dear {name},\n\n"
    "We are excited to invite you to *[Event Name]*!\n\n"
    "*Date:* [Date]\n*Time:* [Time]\n*Address:* [Address]\n\n"
    "Warm regards,\n*[Host Name]*\n"
)

# Set page configuration
st.set_page_config(layout="wide", page_title="Event Invitation Generator")

st.title("🎉 Event Invitation Generator")

# Load configuration
def load_config():
    config_path = 'config.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {
        "guest_list_file": "data/WhatsApp Invite List dummy.xlsx",
        "invite_image_file": "data/WhatsApp Invite.png",
        "prompt_file": "data/invitation_prompt.md"
    }

config = load_config()
GUEST_LIST_FILE = config.get("guest_list_file", "WhatsApp Invite List.xlsx")
INVITE_IMAGE_FILE = config.get("invite_image_file", "WhatsApp Invite.png")
PROMPT_FILE = config.get("prompt_file", "invitation_prompt.md")

# Initialize session state for persistence
# Guests are identified by their DataFrame row index (Excel row = index +
# HEADER_ROW + 1), so guests sharing the same "Addressable Names" stay distinct.
if 'selected_rows' not in st.session_state:
    st.session_state.selected_rows = []
if 'current_row' not in st.session_state:
    st.session_state.current_row = None
if 'sent_rows' not in st.session_state:
    st.session_state.sent_rows = set()
# source_bytes: the unchanged guest list as loaded (drives display/filtering, kept
# stable during a session so the guest options don't shift mid-session).
# workbook_bytes: a working copy mutated in memory by "Mark sent" and offered
# back as a download (the persistent path on the cloud's ephemeral filesystem).
if 'source_bytes' not in st.session_state:
    st.session_state.source_bytes = None
if 'workbook_bytes' not in st.session_state:
    st.session_state.workbook_bytes = None
# last_saved_bytes: what "Mark sent" last wrote to the on-disk guest list (local
# only), so that our own write isn't mistaken for a newly loaded list.
if 'last_saved_bytes' not in st.session_state:
    st.session_state.last_saved_bytes = None
if 'backup_done' not in st.session_state:
    st.session_state.backup_done = False
if 'template_text' not in st.session_state:
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            st.session_state.template_text = f.read()
    else:
        st.session_state.template_text = FALLBACK_TEMPLATE

# Match the app theme in the custom HTML (preview bubble, copy buttons).
IS_DARK = st.context.theme.type == "dark"

# Load data function. Operates on raw bytes so the same code path works for an
# uploaded file (cloud) and a file read from disk (local dev).
@st.cache_data
def load_data(file_bytes):
    try:
        # Headers are on row 2 of the sheet
        df = pd.read_excel(io.BytesIO(file_bytes), header=HEADER_ROW - 1)
        # Clean up column names just in case
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return None

@st.cache_data
def guest_list_template():
    return build_guest_list_template()

@st.cache_data
def image_png_base64(image_bytes):
    return base64.b64encode(prepare_image(image_bytes)).decode("ascii")

# Resolve the guest-list source: an uploaded file takes priority; otherwise fall
# back to the configured path on disk (local dev convenience).
st.markdown(
    "**Excel format:** column headers must be on **row 2**. "
    "Required columns: `Addressable Names` (replaces `{name}` in the message), "
    "`Add to Invite List?` (set to `Yes` to include). "
    "Optional: `Invited?` (set by *Mark sent*). Other columns are ignored."
)
upload_col, template_col = st.columns([3, 1], vertical_alignment="center")
with upload_col:
    uploaded_file = st.file_uploader(
        "Upload guest list (.xlsx)", type=["xlsx"], key="guest_upload",
        help="Headers must be on row 2. On the cloud, upload your own file — nothing is stored on the server."
    )
with template_col:
    st.download_button(
        "⬇️ Download blank template (.xlsx)", data=guest_list_template(),
        file_name="Guest List Template.xlsx", mime=XLSX_MIME,
        on_click="ignore", width="stretch",
        help="An empty guest list in the expected layout: fill it in, save, and upload it here.",
    )

if uploaded_file is not None:
    source_bytes = uploaded_file.getvalue()
elif os.path.exists(GUEST_LIST_FILE):
    with open(GUEST_LIST_FILE, "rb") as f:
        source_bytes = f.read()
    # "Mark sent" also saves to this file locally; that write is not a new list.
    if source_bytes == st.session_state.last_saved_bytes:
        source_bytes = st.session_state.source_bytes
else:
    st.info("Please upload a guest list (.xlsx) to get started, or download the blank template above.")
    st.stop()

# When the source changes (new upload), reset the working copy, selection and sent tracking.
if source_bytes != st.session_state.source_bytes:
    st.session_state.source_bytes = source_bytes
    st.session_state.workbook_bytes = source_bytes
    st.session_state.sent_rows = set()
    st.session_state.selected_rows = []
    st.session_state.current_row = None

df = load_data(st.session_state.source_bytes)
if df is None:
    st.stop()

# Normalize column names for easier (case-insensitive) access
col_map = {c.lower(): c for c in df.columns}
name_col = col_map.get('addressable names')
invite_col = col_map.get('add to invite list?')
invited_col = col_map.get('invited?') or col_map.get('invited')

if name_col is None:
    st.error(
        "Column 'Addressable Names' not found in row 2 of the guest list. "
        "Download the blank template above to see the expected layout."
    )
    st.stop()

# 1. Filtering Logic
# Criteria: 'Add to Invite List?' == 'Yes' AND 'Invited?' != 'Yes'
if invite_col:
    mask_invite = df[invite_col].astype(str).str.strip().str.lower() == 'yes'
else:
    st.warning("Column 'Add to Invite List?' not found. Showing all rows.")
    mask_invite = pd.Series(True, index=df.index)

if invited_col:
    # We want rows where Invited is NOT 'Yes' (so 'No', NaN, empty, etc. are okay)
    mask_not_invited = df[invited_col].astype(str).str.strip().str.lower() != 'yes'
else:
    mask_not_invited = pd.Series(True, index=df.index)
    st.info("No 'Invited?' column found — it will be added when you mark a guest as sent.")

has_name = df[name_col].notna() & (df[name_col].astype(str).str.strip() != "")
df_final = df[mask_invite & mask_not_invited & has_name]

# Guest names by row; duplicate names get their Excel row number so they stay distinguishable.
guest_names = df_final[name_col].astype(str).str.strip()
duplicate_names = set(guest_names[guest_names.duplicated(keep=False)])
valid_rows = guest_names.index.tolist()

def guest_label(row):
    name = guest_names[row]
    return f"{name} (row {row + HEADER_ROW + 1})" if name in duplicate_names else name

# Widget callbacks (run before the next rerun, so the UI updates immediately)
def select_rows(rows):
    st.session_state.selected_rows = rows

def go_to(row):
    st.session_state.current_row = row

def load_template():
    upload = st.session_state.template_upload
    if upload is None:  # file removed from the uploader: keep the current text
        return
    raw = upload.getvalue()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    st.session_state.template_text = text.replace("\r\n", "\n").replace("\r", "\n")

def save_workbook_locally():
    # On local macOS with the on-disk guest list (nothing uploaded), also save
    # the change to that file to preserve the original desktop behavior.
    if not (IS_DESKTOP and st.session_state.get("guest_upload") is None and os.path.exists(GUEST_LIST_FILE)):
        return
    # openpyxl drops images/charts when re-saving, so back up the original once per session.
    if not st.session_state.backup_done:
        root, ext = os.path.splitext(GUEST_LIST_FILE)
        shutil.copy2(GUEST_LIST_FILE, f"{root} (backup){ext}")
        st.session_state.backup_done = True
    with open(GUEST_LIST_FILE, "wb") as f:
        f.write(st.session_state.workbook_bytes)
    st.session_state.last_saved_bytes = st.session_state.workbook_bytes

def set_sent(row, guest, sent, order=None):
    try:
        st.session_state.workbook_bytes = mark_row(
            st.session_state.workbook_bytes, row + HEADER_ROW + 1, guest, "Yes" if sent else None
        )
    except Exception as e:
        st.error(f"Error updating Excel: {e}")
        return
    try:
        save_workbook_locally()
    except OSError as e:
        st.warning(f"Updated in the app, but couldn't save to '{GUEST_LIST_FILE}': {e}. Use the download button instead.")

    if not sent:
        st.session_state.sent_rows.discard(row)
        return
    st.session_state.sent_rows.add(row)
    st.toast(f"Marked {guest} as sent!", icon="✅")
    # Move on to the next guest (in selection order) who hasn't been sent yet.
    if order and row in order:
        pos = order.index(row)
        upcoming = order[pos + 1:] + order[:pos]
        next_row = next((r for r in upcoming if r not in st.session_state.sent_rows), None)
        if next_row is not None:
            st.session_state.current_row = next_row

# Layout: 3 columns with wider 3rd column
col1, col2, col3 = st.columns([0.8, 1.2, 2.0])

with col1:
    st.subheader("👥 1. Select Guests")

    # Diagnostics
    count_total_yes = int(mask_invite.sum())
    count_already_invited = int((mask_invite & ~mask_not_invited).sum())

    with st.expander("Filter Details", expanded=True):
        st.info(f"""
        **Filter Breakdown:**
        - Marked 'Add to Invite List?': **{count_total_yes}**
        - Already Marked 'Invited': **{count_already_invited}**
        - **Available to Invite: {len(df_final)}**
        """)

    sel_all, sel_clear = st.columns(2)
    sel_all.button("Select all", on_click=select_rows, args=(valid_rows,), width="stretch")
    sel_clear.button("Clear", on_click=select_rows, args=([],), width="stretch")

    # Multiselect bound to session state (options are row indices)
    selected_rows = st.multiselect(
        "Choose guests to invite:",
        options=valid_rows,
        format_func=guest_label,
        key="selected_rows"
    )

    st.metric("Total Selected", len(selected_rows))

with col2:
    st.subheader("✍️ 2. Message & Image")

    with st.expander("📂 Load / save template"):
        st.file_uploader(
            "Load a template (.txt / .md)", type=["txt", "md"],
            key="template_upload", on_change=load_template,
        )
        st.download_button(
            "💾 Download template (.txt)", data=st.session_state.template_text,
            file_name="invitation_template.txt", mime="text/plain",
            on_click="ignore", width="stretch",
        )
        # Saving to disk is local-only: the cloud filesystem is ephemeral and shared.
        if IS_DESKTOP and st.button("Save as default template", width="stretch", help=f"Overwrites {PROMPT_FILE}"):
            with open(PROMPT_FILE, "w", encoding="utf-8") as f:
                f.write(st.session_state.template_text)
            st.toast("Saved as the default template.", icon="💾")

    st.text_area(
        "Message template — `{name}` is replaced by each guest's Addressable Name",
        key="template_text",
        height=380
    )
    st.caption("WhatsApp formatting: `*bold*` · `_italic_` · `~strikethrough~` · `` ```monospace``` `` · `> quote`")
    template = st.session_state.template_text
    if "{name}" not in template:
        st.warning("The template has no `{name}` placeholder, so every guest gets the same text.")

    # Preview as WhatsApp renders it (not as Markdown: *x* is bold in WhatsApp).
    preview_name = guest_names[selected_rows[0]] if selected_rows else "Guest Name"
    st.caption(f"Preview for {preview_name}:")
    st.html(whatsapp_to_html(render_message(template, preview_name), dark=IS_DARK))

    st.markdown("---")
    st.subheader("🖼️ Invite Image")
    image_upload = st.file_uploader(
        "Upload invite image (sent before the text)", type=["png", "jpg", "jpeg", "webp"],
        key="image_upload",
    )
    if image_upload is not None:
        image_bytes, image_name = image_upload.getvalue(), image_upload.name
    elif os.path.exists(INVITE_IMAGE_FILE):
        with open(INVITE_IMAGE_FILE, "rb") as imgf:
            image_bytes = imgf.read()
        image_name = os.path.basename(INVITE_IMAGE_FILE)
    else:
        image_bytes = image_name = None

    # PNG (base64) for the browser clipboard; None means text-only invites.
    png_base64 = None
    if image_bytes:
        try:
            png_base64 = image_png_base64(image_bytes)
            image_type = image_mime(image_bytes)
        except Exception as e:
            st.error(f"Couldn't read the image '{image_name}': {e}")
            image_bytes = None

    if image_bytes:
        st.image(image_bytes, width=300)
        if not st.checkbox("Attach this image", value=True, help="Untick to send text-only invites."):
            png_base64 = None
        # Download works everywhere — e.g. to attach the image manually.
        st.download_button(
            "⬇️ Download Image", data=image_bytes, file_name=image_name, mime=image_type,
            on_click="ignore", width="stretch",
        )
    else:
        st.info("No image: invites will be text only.")

with col3:
    st.subheader("📤 3. Copy & Send")

    if not selected_rows:
        st.info("Select guests in column 1 to start.")
    else:
        sent_rows = st.session_state.sent_rows
        sent_count = sum(r in sent_rows for r in selected_rows)
        st.progress(sent_count / len(selected_rows), text=f"{sent_count} of {len(selected_rows)} sent")
        if sent_count == len(selected_rows):
            st.success("All selected guests are marked as sent 🎉 — download the updated guest list below.")

        # Current guest: keep it valid when the selection changes, and set it on
        # every run - the selectbox below is rebuilt whenever its labels (✅/⏳)
        # or options change, and would otherwise fall back to a stale value.
        current_row = st.session_state.get("current_row")
        if current_row not in selected_rows:
            current_row = next((r for r in selected_rows if r not in sent_rows), selected_rows[0])
        st.session_state.current_row = current_row
        pos = selected_rows.index(current_row)

        # Guest navigator
        sent_snapshot = set(sent_rows)
        nav_prev, nav_pick, nav_next = st.columns([1, 6, 1], vertical_alignment="bottom")
        nav_prev.button(
            "◀", key="nav_prev", help="Previous guest", width="stretch",
            on_click=go_to, args=(selected_rows[max(pos - 1, 0)],), disabled=pos == 0,
        )
        row = nav_pick.selectbox(
            "Guest", options=selected_rows, key="current_row", label_visibility="collapsed",
            format_func=lambda r: ("✅ " if r in sent_snapshot else "⏳ ") + guest_label(r),
        )
        nav_next.button(
            "▶", key="nav_next", help="Next guest", width="stretch",
            on_click=go_to, args=(selected_rows[min(pos + 1, len(selected_rows) - 1)],),
            disabled=pos == len(selected_rows) - 1,
        )

        guest = guest_names[row]
        message = render_message(template, guest)

        with st.container(border=True):
            st.markdown(f"**Message for: {guest}**" + ("  ·  ✅ sent" if row in sent_rows else ""))
            if png_base64:
                st.caption("Post 1 — image")
                st.image(image_bytes, width=200)
                st.caption("Post 2 — text")
            st.html(whatsapp_to_html(message, dark=IS_DARK))

            # Copy buttons (browser clipboard; works locally and on the cloud)
            components.html(copy_buttons_html(message, png_base64, dark=IS_DARK), height=85)
            if png_base64:
                st.caption(
                    "With this guest's chat open in WhatsApp: **📷 Copy image** → paste (⌘V / Ctrl+V) → send, "
                    "then **📋 Copy text** → paste → send."
                )
            else:
                st.caption("With this guest's chat open in WhatsApp: **📋 Copy text** → paste (⌘V / Ctrl+V) → send.")

            if row in sent_rows:
                st.button(
                    "↩️ Undo mark as sent", key=f"undo_{row}", width="stretch",
                    on_click=set_sent, args=(row, guest, False),
                )
            else:
                st.button(
                    "✅ Mark sent & next", key=f"sent_{row}", type="primary", width="stretch",
                    on_click=set_sent, args=(row, guest, True, selected_rows),
                )

            with st.expander("Raw text (manual copy)"):
                st.code(message, language=None, wrap_lines=True)

        output_text = "".join(
            f"--- MESSAGE FOR: {guest_names[r]} ---\n{render_message(template, guest_names[r])}\n{'-' * 40}\n\n"
            for r in selected_rows
        )
        st.download_button(
            label="Download All (.txt)",
            data=output_text,
            file_name="generated_invites.txt",
            mime="text/plain",
            on_click="ignore",
        )

    # Updated guest list with "Mark sent" changes. This is the persistent
    # path on the cloud, where on-disk write-back would be lost on restart.
    if st.session_state.sent_rows:
        st.markdown("---")
        st.caption(f"{len(st.session_state.sent_rows)} guest(s) marked as sent this session.")
        st.download_button(
            label="⬇️ Download updated guest list (.xlsx)",
            data=st.session_state.workbook_bytes,
            file_name="guest_list_updated.xlsx",
            mime=XLSX_MIME,
            on_click="ignore",
        )
