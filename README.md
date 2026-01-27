# Event Invitation Generator

This project is a tool to generate personalized event invitations in bulk for WhatsApp or other messaging platforms. It reads a guest list from an Excel file and generates formatted messages with placeholders filled in.

## Features (What it DOES)
- **Bulk Message Generation**: Generates personalized messages for a list of guests defined in an Excel sheet.
- **WhatsApp Click-to-Chat**: One-click button to open WhatsApp with the message pre-filled for each guest (requires `Phone Number` column).
- **Write-Back Status**: "Mark as Sent" button that updates the `Invited` column in your Excel file to "Yes" to track progress.
- **Customizable Templates**: Uses a Markdown template (`data/invitation_prompt.md`) to define the message structure. Supports placeholders like `{name}`.
- **Web Interface**: Includes a Streamlit app (`app.py`) for an easy-to-use graphical interface.
- **Script Mode**: Includes a CLI script (`Invite_draft.py`) to generate all drafts into a single Markdown file.
- **Image Attachment**: Supports attaching an invite image (`data/WhatsApp Invite.png`).

## Limitations (What it DOES NOT do)
- **No Automatic Sending**: This tool DOES NOT send messages broadly. You must click "Send" in WhatsApp yourself.
- **No API Integration**: It does not connect to WhatsApp Business API.

## Requirements
Your Excel file (`data/WhatsApp Invite List dummy.xlsx`) should have the following columns (headers on row 2):
1.  `Addressable Names` (Required): Name to use in the message.
2.  `Add to Invite List?` (Required): Set to "Yes" to include.
3.  `Phone Number` (Optional): For WhatsApp links. Format: `1234567890` or `+1234567890`.
4.  `Invited` (Optional): To track status. The app updates this column when you click "Mark as Sent".

## Setup & Usage

1.  **Configuration**: Edit `config.json` to point to your data files if they are named differently.
2.  **Data**: Place your guest list (`WhatsApp Invite List dummy.xlsx`), invite image (`WhatsApp Invite.png`), and prompt (`invitation_prompt.md`) in the `data/` folder.
3.  **Run App**:
    ```bash
    streamlit run app.py
    ```
4.  **Run Script**:
    ```bash
    python Invite_draft.py
    ```
    Output will be saved to `output/Invite_Drafts.md`.
