# Event Invitation Generator

This project is a tool to generate personalized event invitations in bulk for WhatsApp or other messaging platforms. It reads a guest list from an Excel file and generates formatted messages with placeholders filled in.

## Features (What it DOES)
- **Bulk Message Generation**: Generates personalized messages for a list of guests defined in an Excel sheet.
- **Copy & Send, one guest at a time**: For each guest, one-click **📷 Copy image** and **📋 Copy text** buttons, then **✅ Mark sent & next** (with **↩️ Undo**). Works in any modern browser, locally and on Streamlit Cloud.
- **Image attachment**: Upload the invite image (PNG/JPG/WEBP) in the app, or fall back to the image configured in `config.json`. Untick *Attach this image* for text-only invites.
- **Message templates**: Edit the template in a Word-like editor, **load** one from a `.txt`/`.md` file, and **save** it with *Download template (.txt)*. When running locally, *Save as default template* writes it to `data/invitation_prompt.md`.
- **Word-like formatting**: Bold, italic, strikethrough, monospace, lists and quotes from a toolbar (or ⌘B / ⌘I), and pasting from Word, Google Docs or email keeps the formatting. It's converted to WhatsApp's formatting automatically; the preview shows exactly what the guest will see.
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
Edit the message like in Word or Google Docs: select text and use the toolbar — **B**old, *I*talic, ~~S~~trikethrough, monospace, bulleted / numbered lists, quote, clear formatting — or press **⌘B / Ctrl+B** (bold), **⌘I / Ctrl+I** (italic), **⌘⇧X / Ctrl+Shift+X** (strikethrough). **+ {name}** inserts the guest's name at the cursor.

- **Pasting** from Word, Google Docs, a web page or an email keeps bold, italic and strikethrough. A link keeps its address as text, e.g. `Venue map (https://…)`. Text that already uses WhatsApp formatting (`*bold*`, `_italic_`) is shown formatted.
- **Dropped automatically**: WhatsApp has no underline, colours, fonts or font sizes, and it can't format part of a word (e.g. bold "Diw" in "Diwali"). The green preview always shows exactly what the guest will see.
- **Behind the scenes** the template is kept in WhatsApp's own formatting, which is what gets copied and what *Download template (.txt)* saves:

| In the editor | Saved / copied as |
|---|---|
| **Date:** | `*Date:*` |
| *you and your family* | `_you and your family_` |
| ~~old time~~ | `~old time~` |
| `Code 1234` (monospace) | `` ```Code 1234``` `` |
| bulleted list / quote | `- item` / `> note` |

`{name}` is replaced by each guest's `Addressable Names`. Other `{`/`}` are left as they are. Markdown-style `**bold**` from older templates is converted to WhatsApp's `*bold*` automatically.

The editor uses [Quill](https://quilljs.com) (loaded from the jsDelivr CDN). Without an internet connection the app falls back to a plain text box where you type WhatsApp's formatting yourself (`*bold*`, `_italic_`, `~strike~`).

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
