import streamlit as st
import pandas as pd
import re
import subprocess
import os
import sys
import io
import urllib.parse
import openpyxl

# True on local macOS (desktop clipboard features available),
# False on Streamlit Community Cloud / Linux (no user-facing clipboard).
IS_DESKTOP = sys.platform == "darwin"

def copy_image_to_clipboard(image_path):
    try:
        # AppleScript to set the clipboard to the image file
        # We use 'set the clipboard to (read (POSIX file "path") as JPEG picture)'
        # Assuming generic image handling
        
        # Robust method for PNG/JPG on macOS:
        cmd = f'''osascript -e 'set the clipboard to (read (POSIX file "{image_path}") as versatile)' '''
        
        # Standard practice for various file types
        cmd = f"""osascript -e 'set the clipboard to (read (POSIX file "{image_path}") as TIFF picture)'"""
        
        subprocess.run(cmd, shell=True, check=True)
        return True
    except Exception as e:
        print(f"Error copying image: {e}")
        return False

# Set page configuration
st.set_page_config(layout="wide", page_title="Event Invitation Generator")

st.title("🎉 Event Invitation Generator")

# Initialize session state for persistence
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'selected_guests_list' not in st.session_state:
    st.session_state.selected_guests_list = []
if 'sent_guests' not in st.session_state:
    st.session_state.sent_guests = set()
# source_bytes: the unchanged guest list as loaded (drives display/filtering, kept
# stable during a session so the multiselect options don't shift mid-session).
# workbook_bytes: a working copy mutated in memory by "Mark as Sent" and offered
# back as a download (the persistent path on the cloud's ephemeral filesystem).
if 'source_bytes' not in st.session_state:
    st.session_state.source_bytes = None
if 'workbook_bytes' not in st.session_state:
    st.session_state.workbook_bytes = None

# Load configuration
import json
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

# Load data function. Operates on raw bytes so the same code path works for an
# uploaded file (cloud) and a file read from disk (local dev).
@st.cache_data
def load_data(file_bytes):
    try:
        # header=1 as per previous script usage
        df = pd.read_excel(io.BytesIO(file_bytes), header=1)
        # Clean up column names just in case
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return None

# Resolve the guest-list source: an uploaded file takes priority; otherwise fall
# back to the configured path on disk (local dev convenience).
uploaded_file = st.file_uploader(
    "Upload guest list (.xlsx)", type=["xlsx"],
    help="Headers must be on row 2. On the cloud, upload your own file — nothing is stored on the server."
)

if uploaded_file is not None:
    source_bytes = uploaded_file.getvalue()
elif os.path.exists(GUEST_LIST_FILE):
    with open(GUEST_LIST_FILE, "rb") as f:
        source_bytes = f.read()
else:
    st.info("Please upload a guest list (.xlsx) to get started.")
    st.stop()

# When the source changes (new upload), reset the working copy and sent tracking.
if source_bytes != st.session_state.source_bytes:
    st.session_state.source_bytes = source_bytes
    st.session_state.workbook_bytes = source_bytes
    st.session_state.sent_guests = set()

df = load_data(st.session_state.source_bytes)

def update_excel_status(guest_name, status="Yes"):
    try:
        from openpyxl import load_workbook

        # Load the workbook from the in-memory bytes (works on the cloud's
        # ephemeral filesystem, where writing back to a disk path would be lost).
        wb = load_workbook(io.BytesIO(st.session_state.workbook_bytes))
        # Assume first sheet
        ws = wb.active
        
        # Find the column for "Addressable Names" and "Invited"
        # Since we use header=1 in pandas, the headers are likely on row 2 in Excel (1-indexed)
        # But let's scan the first few rows to be safe or blindly assume header is row 2 based on config.
        # Ideally, we match the pandas logic.
        
        header_row = 2
        name_col_idx = None
        invited_col_idx = None
        
        # Find column indices
        for col in range(1, ws.max_column + 1):
            cell_val = ws.cell(row=header_row, column=col).value
            if cell_val:
                clean_val = str(cell_val).strip()
                if clean_val == "Addressable Names":
                    name_col_idx = col
                elif clean_val in ["Invited", "Invited?"]:
                    invited_col_idx = col
        
        if not name_col_idx:
            st.error("Could not find 'Addressable Names' column in Excel to update.")
            return False
            
        if not invited_col_idx:
            # Try to find empty column or create one? 
            # For now, error out if column structure isn't as expected/template
            st.error("Could not find 'Invited' or 'Invited?' column in Excel to update.")
            return False

        # Find the row with the guest name
        row_updated = False
        for row in range(header_row + 1, ws.max_row + 1):
            val = ws.cell(row=row, column=name_col_idx).value
            if val == guest_name:
                ws.cell(row=row, column=invited_col_idx).value = status
                row_updated = True
                break
        
        if row_updated:
            # Persist the change in memory and offer it back via download.
            buf = io.BytesIO()
            wb.save(buf)
            st.session_state.workbook_bytes = buf.getvalue()
            st.session_state.sent_guests.add(guest_name)

            # On local macOS with a real on-disk source, also save to that file
            # to preserve the original desktop behavior.
            if IS_DESKTOP and uploaded_file is None and os.path.exists(GUEST_LIST_FILE):
                wb.save(GUEST_LIST_FILE)
            return True
        else:
            st.error(f"Could not find guest '{guest_name}' in the file.")
            return False

    except Exception as e:
        st.error(f"Error updating Excel: {e}")
        return False

if df is not None:
    # 1. Advanced Filtering Logic
    # Criteria: 'Add to Invite List?' == 'Yes' AND 'Invited' != 'Yes'
    
    # Normalize column names for easier access
    col_map = {c.strip().lower(): c.strip() for c in df.columns}
    
    invite_col = col_map.get('add to invite list?', 'Add to Invite List?')
    # Check for 'invited' or 'invited?'
    invited_col = col_map.get('invited') or col_map.get('invited?', 'Invited')
    phone_col = col_map.get('phone number', 'Phone Number')
    
    if invite_col in df.columns:
        # Step 1: Filter those marked for invite
        mask_invite = df[invite_col].astype(str).str.strip().str.lower() == 'yes'
        
        # Step 2: Filter out those already invited (if column exists)
        if invited_col in df.columns:
            # We want rows where Invited is NOT 'Yes' (so 'No', NaN, empty, etc. are okay)
            mask_not_invited = df[invited_col].astype(str).str.strip().str.lower() != 'yes'
            df_final = df[mask_invite & mask_not_invited].copy()
        else:
            df_final = df[mask_invite].copy()
            st.warning("'Invited' column not found in Excel. Write-back feature may not work as expected.")
    else:
        st.warning(f"Column '{invite_col}' not found. Showing all rows.")
        df_final = df.copy()

    if 'Addressable Names' not in df_final.columns:
        st.error("Column 'Addressable Names' not found in input file.")
        st.stop()

    # Layout: 3 columns with wider 3rd column
    col1, col2, col3 = st.columns([0.8, 1.2, 2.0])

    valid_names = df_final['Addressable Names'].dropna().astype(str).unique().tolist()

    with col1:
        st.subheader("👥 1. Select Guests")
        
        # Diagnostics
        count_total_yes = mask_invite.sum()
        count_already_invited = (~mask_not_invited & mask_invite).sum() if invited_col in df.columns else 0
        
        with st.expander("Filter Details", expanded=True):
            st.info(f"""
            **Filter Breakdown:**
            - Marked 'Add to Invite List?': **{count_total_yes}**
            - Already Marked 'Invited': **{count_already_invited}**
            - **Available to Generate: {len(df_final)}**
            """)
        
        # Select All Logic using Session State callback
        def toggle_select_all():
            if st.session_state.select_all_cb:
                st.session_state.selected_guests_list = valid_names
            else:
                st.session_state.selected_guests_list = []

        # Checkbox to drive the select all
        st.checkbox("Select All Guests", key="select_all_cb", on_change=toggle_select_all)
        
        # Multiselect bound to session state
        selected_guests = st.multiselect(
            "Choose guests to generate invites for:",
            options=valid_names,
            key="selected_guests_list"
        )
        
        st.metric("Total Selected", len(selected_guests))

    with col2:
        st.subheader("✍️ 2. Draft Message")
        
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'r') as f:
                default_template = f.read()
        else:
            st.error(f"Prompt file '{PROMPT_FILE}' not found. Please ensure it exists in the data directory.")
            st.stop()

        template = st.text_area(
            "Edit Message Template ({name} will be replaced)",
            value=default_template,
            height=400
        )
        
        st.markdown("---")
        st.subheader("Image Attachment")
        if os.path.exists(INVITE_IMAGE_FILE):
            st.image(INVITE_IMAGE_FILE, width=300)

            # Copy-to-clipboard is macOS-only (uses osascript); hide it elsewhere.
            if IS_DESKTOP:
                if st.button(f"📷 Copy Image to Clipboard", key="copy_img_global", use_container_width=True):
                    img_path = os.path.abspath(INVITE_IMAGE_FILE)
                    if copy_image_to_clipboard(img_path):
                        st.success("Image copied! You can now Paste it into WhatsApp.")
                    else:
                        st.error("Failed to copy image.")

            # Download works everywhere — save the image and attach it manually
            # in WhatsApp (wa.me links cannot carry an image).
            with open(INVITE_IMAGE_FILE, "rb") as imgf:
                st.download_button(
                    "⬇️ Download Image", data=imgf.read(),
                    file_name=os.path.basename(INVITE_IMAGE_FILE),
                    mime="image/png", use_container_width=True,
                )
        else:
            st.warning(f"Image '{INVITE_IMAGE_FILE}' not found.")

    with col3:
        st.subheader("📤 3. Review & Send")
        
        # Generate Button
        if st.button("Generate Messages", type="primary"):
            st.session_state.generated = True
        
        # Only show content if generated is True
        if st.session_state.generated:
            if not selected_guests:
                st.warning("Please select at least one guest.")
            else:
                st.write(f"Generating {len(selected_guests)} messages...")
                
                output_text = ""
                
                for guest in selected_guests:
                    # Generate individual message
                    try:
                        final_msg = template.format(name=guest)
                        
                        # Container for each message
                        with st.container(border=True):
                            st.markdown(f"**Message for: {guest}**")
                            
                            # Preview the rendered markdown (so they can see bolding etc)
                            # We add double spaces for markdown line breaks so single newlines render properly
                            preview_msg = final_msg.replace("\n", "  \n")
                            st.caption("Preview (Rendered):")
                            st.info(preview_msg)    
                            
                            # WhatsApp-formatted text (** -> * for bold). st.code
                            # below renders a browser-native copy button that works
                            # on the cloud, replacing the desktop-only pyperclip copy.
                            whatsapp_msg = final_msg.replace("**", "*")

                            # Action Buttons (Side by Side)
                            bc1, bc2, bc3 = st.columns([1, 1, 1])

                            with bc1:
                                # Image copy is macOS-only (osascript); on the cloud
                                # use the global "Download Image" button instead.
                                if IS_DESKTOP and os.path.exists(INVITE_IMAGE_FILE):
                                    if st.button(f"📷 Copy Image", key=f"img_local_{guest}", use_container_width=True):
                                        img_path = os.path.abspath(INVITE_IMAGE_FILE)
                                        if copy_image_to_clipboard(img_path):
                                            st.toast("Image copied!", icon="📷")
                                        else:
                                            st.error("Failed to copy image.")

                            with bc2:
                                # WhatsApp Link
                                guest_row = df_final[df_final['Addressable Names'] == guest]
                                if not guest_row.empty and phone_col in df_final.columns:
                                    raw_phone = str(guest_row.iloc[0][phone_col])
                                    # Basic cleaning: remove non-digit characters except +
                                    clean_phone = re.sub(r'[^\d+]', '', raw_phone)

                                    if clean_phone:
                                        encoded_msg = urllib.parse.quote(whatsapp_msg)
                                        wa_link = f"https://wa.me/{clean_phone}?text={encoded_msg}"
                                        st.link_button(f"💬 WhatsApp", wa_link, use_container_width=True)
                                    else:
                                        st.caption("No phone #")
                                else:
                                    st.caption("No phone #")

                            with bc3:
                                # Mark as Sent
                                if guest in st.session_state.sent_guests:
                                    st.button("✅ Sent", key=f"sent_{guest}", use_container_width=True, disabled=True)
                                elif st.button(f"✅ Mark Sent", key=f"sent_{guest}", use_container_width=True):
                                    if update_excel_status(guest, "Yes"):
                                        st.toast(f"Marked {guest} as sent!", icon="✅")

                            # Copy-ready text (browser-native copy button on the icon)
                            st.caption("Copy text (WhatsApp formatting):")
                            st.code(whatsapp_msg, language=None)
                        
                        output_text += f"--- MESSAGE FOR: {guest} ---\n{final_msg}\n{'-'*40}\n\n"
                        
                    except KeyError:
                        st.error(f"Error: Placeholder {{name}} missing in template.")
                
                st.download_button(
                    label="Download All (.txt)",
                    data=output_text,
                    file_name="generated_invites.txt",
                    mime="text/plain"
                )

        # Updated guest list with "Mark as Sent" changes. This is the persistent
        # path on the cloud, where on-disk write-back would be lost on restart.
        if st.session_state.sent_guests:
            st.markdown("---")
            st.caption(f"{len(st.session_state.sent_guests)} guest(s) marked as sent this session.")
            st.download_button(
                label="⬇️ Download updated guest list (.xlsx)",
                data=st.session_state.workbook_bytes,
                file_name="guest_list_updated.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

else:
    st.info("Please upload a guest list (.xlsx) to get started.")
