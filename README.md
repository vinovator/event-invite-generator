# Event Invitation Generator

A single web page for sending personalised event invitations on WhatsApp, one guest at a time, from an Excel guest list. It prepares and copies each guest's message (and the invite image) for you to paste into WhatsApp. It never sends anything itself.

Everything runs in your browser: your guest list, message and progress never leave your device. There is nothing to install.

## How to open it

- **On your computer:** double-click `index.html` (Chrome or Edge recommended).
- **Online (free):** on GitHub, go to *Settings → Pages*, choose *Deploy from a branch → main → / (root)*, then open `https://<your-user>.github.io/event-invite-generator/`. That URL also works on a phone.

The editor and Excel libraries load from the jsDelivr CDN, so the first visit needs an internet connection.

## What it does

- **Guest list:** **⬆️ Upload guest list (.xlsx)**, or start from **⬇️ Download blank guest list template (.xlsx)**. **🧪 Try with a sample guest list** loads a demo list when the page is served online.
- **Pick guests:** filter by **Category**, search, *Select all shown* / *Clear selection*. Headcount totals (Estimated Count, Adults, Kids…) are added up for the selected and the sent guests.
- **Write the message** in a Word-like editor (bold, italic, strikethrough, monospace, lists, quotes). Pasting from Word, Google Docs or email keeps the formatting.
- **Personalise** with `{name}` and any column, e.g. `{Adults}` or `{Table}`: use **+ Insert a guest detail**.
- **Warnings** for blanks left in the text (`[Event Name]`, `[Date]`…), unknown `{placeholders}`, and columns that are empty for a guest.
- **Send, one guest at a time:** 🔍 **Copy contact name** (to find the chat in WhatsApp's search) → 📷 **Copy invite image** → paste & send → 📋 **Copy message text** → paste & send → ✅ **Mark as sent & go to next guest** (with ↩️ **Undo: mark as not sent**).
- **Tracking:** *Mark as sent* fills in `Invited?` = Yes and `Invited On` (date and time) in the workbook.
- **Saving:** **⬇️ Download updated guest list (.xlsx)** at any time. In Chrome/Edge, after **⬆️ Upload guest list**, tick *Also save changes straight into …* to write straight back into your Excel file. **⬇️ Download original guest list (backup)** gives you the file as you uploaded it.
- **Picks up where you left off:** progress, message and image are kept in the browser. After a refresh, click **▶ Resume where I left off**. **🧹 Clear data saved in this browser** (top right) removes it all, e.g. on a shared computer.
- **Light or dark:** the *Theme* switch at the top picks ☀️ Light, 🌙 Dark or 🖥️ System (follows your device; the default).
- **Back to the site:** *← Back to all apps* returns to https://vinothhaldorai.com/apps/.

## Guest list format

Headers go on **row 2** of the **first sheet** (row 1 is free for notes or totals); guests start on row 3.

| Column | Required | Used for |
|---|---|---|
| `Addressable Names` | ✅ | The greeting, e.g. "Ravi & Priya": `{name}` in the message |
| `Add to Invite List?` | ✅ | `Yes` to include (`Y`, `TRUE`, `✓` also work) |
| `Name` | | The contact's name as saved in WhatsApp, copied by 🔍 *Copy contact name* |
| `Category` | | The category filter (Family, Friends, Work…) |
| `Estimated Count`, `Adults`, `Kids…` | | Headcount totals |
| `Invited?`, `Invited On` | | Filled in by *Mark as sent* (added if missing); guests already marked `Yes` are skipped |
| anything else | | Available as `{Column name}` in the message |

## Formatting

Select text and use the toolbar, or press **⌘B / Ctrl+B** (bold), **⌘I / Ctrl+I** (italic), **⌘⇧X / Ctrl+Shift+X** (strikethrough). The green preview shows exactly what the guest will see.

Behind the scenes the message is kept in WhatsApp's own formatting. That's what gets copied and what *⬇️ Download this message (.txt)* saves: `*bold*`, `_italic_`, `~strike~`, ```` ```monospace``` ````, `- list`, `> quote`. WhatsApp has no underline, colours or font sizes, and can't format part of a word, so those are dropped. A link pasted from a web page keeps its address as text.

## Can the image and text be copied together?

No. The clipboard holds one item at a time, so they're copied (and pasted) one after the other. Tip: send the image once to your own *Message yourself* chat and forward it to up to 5 chats at a time, then use the app just for the personal text.

## Limitations

- No automatic sending and no WhatsApp API: you press Send.
- Saving the workbook rewrites it with ExcelJS: formulas, styles and dropdowns are kept, but charts, pictures and pivot tables inside the workbook are dropped (use *Download original guest list* if you need them).
- Saving straight into the Excel file needs Chrome or Edge on a computer; other browsers download an updated copy instead.

## For developers

No build step: `index.html` (page, styles and app script) + `convert.js` (WhatsApp-text conversions, also loadable in Node). Run the checks with:

```bash
node tests/convert.test.js
```
