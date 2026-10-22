import pandas as pd
import os
import json

# Load configuration
def load_config():
    config_path = 'config.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    print("Warning: config.json not found, using defaults.")
    return {
        "guest_list_file": "data/WhatsApp Invite List dummy.xlsx",
        "invite_image_file": "data/WhatsApp Invite.png",
        "prompt_file": "data/invitation_prompt.md",
        "output_file": "output/Invite_Drafts.md"
    }

config = load_config()
GUEST_LIST_FILE = config.get("guest_list_file", "WhatsApp Invite List.xlsx")
PROMPT_FILE = config.get("prompt_file", "invitation_prompt.md")
OUTPUT_FILE = config.get("output_file", "Invite_Drafts.md")

# 1. Load the data
# header=1 skips the first row (index 0) and uses the second row as the column headers
try:
    df = pd.read_excel(GUEST_LIST_FILE, header=1)
except FileNotFoundError:
    print(f"Error: '{GUEST_LIST_FILE}' not found.")
    exit()

# 2. Filter: Keep only rows where 'Add to Invite list?' is 'Yes'
# We use str.strip() to remove accidental spaces and lower() to handle "YES"/"yes"
# Check if column exists
if 'Add to Invite List?' in df.columns:
    df_filtered = df[df['Add to Invite List?'].astype(str).str.strip().str.lower() == 'yes']
else:
    print("Column 'Add to Invite List?' not found. Using all rows.")
    df_filtered = df

if 'Addressable Names' not in df.columns:
    print("Error: Column 'Addressable Names' not found in Excel file.")
    exit()

# 3. Define the Message Template
try:
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        message_template = f.read()
except FileNotFoundError:
    print(f"Error: '{PROMPT_FILE}' not found.")
    exit()

# 4. Generate Messages and Save to Markdown
total_messages = len(df_filtered)
output_filename = OUTPUT_FILE

print(f"--- GENERATING {total_messages} MESSAGES ---\n")

# Ensure output directory exists
output_dir = os.path.dirname(output_filename)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)

with open(output_filename, 'w', encoding='utf-8') as f:
    f.write(f"# Event Invitation Drafts\n\n")
    f.write(f"**Total Generated:** {total_messages}\n\n")
    f.write("---\n\n")

    count = 0
    for index, row in df_filtered.iterrows():
        guest_name = row['Addressable Names']
        
        # Check if name is valid (not empty or NaN)
        if pd.notna(guest_name):
            count += 1
            # Same rules as app.py: str.replace (stray braces are safe) and
            # legacy Markdown bold (**x**) -> WhatsApp bold (*x*).
            final_message = message_template.replace("**", "*").replace("{name}", str(guest_name))
            
            header = f"--- MESSAGE {count} of {total_messages} FOR: {guest_name} ---"
            
            # Print to console
            print(header)
            print(final_message)
            print("-" * 40)
            print("\n")
            
            # Write to Markdown file
            f.write(f"## {header}\n\n")
            f.write(final_message)
            f.write("\n\n" + "-" * 40 + "\n\n")

print(f"--- DONE ---")
print(f"--- SAVED OUTPUT TO: {output_filename} ---")