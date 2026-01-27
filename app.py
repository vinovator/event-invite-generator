import streamlit as st
import pandas as pd
import re
import subprocess
import os
import pyperclip
import urllib.parse
import openpyxl

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

# Load data function
@st.cache_data
def load_data():
    try:
        # header=1 as per previous script usage
        df = pd.read_excel(GUEST_LIST_FILE, header=1)
        # Clean up column names just in case
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading Excel file '{GUEST_LIST_FILE}': {e}")
        return None

df = load_data()

def update_excel_status(guest_name, status="Yes"):
    try:
        from openpyxl import load_workbook
        
        # Load the workbook
        wb = load_workbook(GUEST_LIST_FILE)
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
            
            if st.button(f"📷 Copy Image to Clipboard", key="copy_img_global", use_container_width=True):
                img_path = os.path.abspath(INVITE_IMAGE_FILE)
                if copy_image_to_clipboard(img_path):
                    st.success("Image copied! You can now Paste it into WhatsApp.")
                else:
                    st.error("Failed to copy image.")
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
                            
                            # Action Buttons (Side by Side)
                            bc1, bc2, bc3, bc4 = st.columns([1, 1, 1, 1])
                            
                            with bc1:
                                if os.path.exists(INVITE_IMAGE_FILE):
                                    if st.button(f"📷 Copy Image", key=f"img_local_{guest}", use_container_width=True):
                                        img_path = os.path.abspath(INVITE_IMAGE_FILE)
                                        if copy_image_to_clipboard(img_path):
                                            st.toast("Image copied!", icon="📷")
                                        else:
                                            st.error("Failed to copy image.")

                            with bc2:
                                if st.button(f"📋 Copy Text", key=f"txt_{guest}", use_container_width=True):
                                    try:
                                        # Convert Markdown bold (**) to WhatsApp bold (*)
                                        whatsapp_msg = final_msg.replace("**", "*")
                                        pyperclip.copy(whatsapp_msg)
                                        st.toast(f"Text for {guest} copied!", icon="📋")
                                    except Exception as e:
                                        st.error(f"Could not copy text: {e}")
                            
                            with bc3:
                                # WhatsApp Link
                                guest_row = df_final[df_final['Addressable Names'] == guest]
                                if not guest_row.empty and phone_col in df_final.columns:
                                    raw_phone = str(guest_row.iloc[0][phone_col])
                                    # Basic cleaning: remove non-digit characters except +
                                    clean_phone = re.sub(r'[^\d+]', '', raw_phone)
                                    
                                    if clean_phone:
                                        encoded_msg = urllib.parse.quote(final_msg.replace("**", "*"))
                                        wa_link = f"https://wa.me/{clean_phone}?text={encoded_msg}"
                                        st.link_button(f"💬 WhatsApp", wa_link, use_container_width=True)
                                    else:
                                        st.caption("No phone #")
                                else:
                                    st.caption("No phone #")
                            
                            with bc4:
                                # Mark as Sent
                                if st.button(f"✅ Mark Sent", key=f"sent_{guest}", use_container_width=True):
                                    if update_excel_status(guest, "Yes"):
                                        st.toast(f"Marked {guest} as sent!", icon="✅")
                                        # Clear cache so the filter updates on next reload
                                        st.cache_data.clear()
                                        # Optional: force rerun if you want immediate disappearance, 
                                        # but usually toast is enough feedback until next refresh
                                        # st.rerun() 


                            # Raw text for manual copying (fallback)
                            with st.expander("Show Raw Text"):
                                 st.code(final_msg, language=None)
                        
                        output_text += f"--- MESSAGE FOR: {guest} ---\n{final_msg}\n{'-'*40}\n\n"
                        
                    except KeyError:
                        st.error(f"Error: Placeholder {{name}} missing in template.")
                
                st.download_button(
                    label="Download All (.txt)",
                    data=output_text,
                    file_name="generated_invites.txt",
                    mime="text/plain"
                )

else:
    st.info(f"Please ensure '{GUEST_LIST_FILE}' is in the same directory.")
