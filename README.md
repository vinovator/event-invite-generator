# Event Invitation Generator

This project is a tool to generate personalized event invitations in bulk for WhatsApp or other messaging platforms. It reads a guest list from an Excel file and generates formatted messages with placeholders filled in.

## Features (What it DOES)
- **Bulk Message Generation**: Generates personalized messages for a list of guests defined in an Excel sheet.
- **Copy & Send, one guest at a time**: For each guest, one-click **📷 Copy image** and **📋 Copy text** buttons, then **✅ Mark sent & next** (with **↩️ Undo**). Works in any modern browser, locally and on Streamlit Cloud.
- **Image attachment**: Upload the invite image (PNG/JPG/WEBP) in the app, or fall back to the image configured in `config.json`. Untick *Attach this image* for text-only invites.
- **Message templates**: Edit the template in the app, **load** one from a `.txt`/`.md` file, and **save** it with *Download template (.txt)*. When running locally, *Save as default template* writes it to `data/invitation_prompt.md`.
- **WhatsApp formatting with a live preview**: Write formatting the way WhatsApp does (see below); the preview shows exactly what the guest will see.
- **Excel template**: *Download blank template (.xlsx)* gives an empty guest list in the expected layout (Yes/No dropdowns, instructions sheet) — fill it in and upload it.
- **Upload or local file**: Upload a guest list (`.xlsx`) at runtime, or fall back to the file configured in `config.json` for local use.
- **Write-Back Status**: "Mark sent" sets the `Invited?` column to "Yes" (the column is added if missing); download the updated `.xlsx` to keep the change. On local macOS it also writes back to the file on disk, keeping a `(backup)` copy of the original first.
- **Script Mode**: Includes a CLI script (`Invite_draft.py`) to generate all drafts into a single Markdown file.

## Limitations (What it DOES NOT do)
- **No Automatic Sending**: You open each guest's chat in WhatsApp yourself, paste and press Send.
- **No API Integration**: It does not connect to WhatsApp Business API.
- **Phone numbers are not used**: Any `Phone Number` column in your sheet is simply ignored.

## Requirements
Your Excel file (`data/WhatsApp Invite List dummy.xlsx`) should have the following columns (headers on row 2):
1.  `Addressable Names` (Required): Name to use in the message (replaces `{name}`).
2.  `Add to Invite List?` (Required): Set to "Yes" to include.
3.  `Invited?` (Optional): To track status. The app updates this column when you click "Mark sent".

Other columns are ignored. The easiest start is the app's **Download blank template (.xlsx)** button.

## Formatting messages (bold, italics, …)
Write the template in **WhatsApp's own formatting** — what you type is exactly what gets pasted, and the preview shows how WhatsApp will display it:

| You type | WhatsApp shows |
|---|---|
| `*Date:*` | **Date:** |
| `_you and your family_` | *you and your family* |
| `~old time~` | ~~old time~~ |
| ` ```Code 1234``` ` | `Code 1234` (monospace) |
| `> note` | quoted line |

`{name}` is replaced by each guest's `Addressable Names`. Other `{`/`}` are left as they are. Markdown-style `**bold**` from older templates is converted to WhatsApp's `*bold*` automatically.

## Sending: image first, then text
With the guest's chat open in WhatsApp (app or web):
1. **📷 Copy image** → paste (⌘V / Ctrl+V) into the chat → send.
2. **📋 Copy text** → paste → send.
3. **✅ Mark sent & next** moves on to the next guest.

**Can the image and text be copied together?** No — the clipboard holds one item at a time, and WhatsApp pastes either the image or the text, so they are copied (and pasted) one after the other. Tip: clipboard history (Windows `Win+V`, or macOS Spotlight's clipboard history) lets you copy both first and pick each one when pasting.

## Setup & Usage

1.  **Install**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configuration**: Edit `config.json` to point to your data files if they are named differently.
3.  **Data**: Place your guest list (`WhatsApp Invite List dummy.xlsx`), invite image (`WhatsApp Invite.png`), and prompt (`invitation_prompt.md`) in the `data/` folder — or upload them in the app.
4.  **Run App**:
    ```bash
    streamlit run app.py
    ```
5.  **Run Script**:
    ```bash
    python Invite_draft.py
    ```
    Output will be saved to `output/Invite_Drafts.md`.

## Deploying to Streamlit Community Cloud

The app runs on [Streamlit Community Cloud](https://share.streamlit.io) with graceful degradation — it detects it is not on a local macOS desktop and adjusts:

- **Upload your own guest list** (and image/template) at runtime; **do not commit real guest data** (names/phone numbers) to a public repo. Only the dummy file is tracked.
- **Copy buttons work in the cloud** (they use the browser clipboard).
- **"Mark sent" is in-memory** (the cloud filesystem resets on restart). Use **Download updated guest list (.xlsx)** to persist your progress, and **Download template (.txt)** to keep your message.

**Deploy:** push this repo (with `requirements.txt`, the dummy `.xlsx`, and the invite image — no real data) to GitHub, then point share.streamlit.io at `app.py`.
