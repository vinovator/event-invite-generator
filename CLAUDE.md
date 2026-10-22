# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A browser-only page for preparing personalised WhatsApp invitations from an Excel guest list. It only drafts and copies messages and never sends them; the user opens each WhatsApp chat themselves (phone numbers are deliberately not used). There is no server, no build step and no package manager: open `index.html` directly or host the repo on GitHub Pages.

## Files

- **`index.html`**: the whole app: markup, CSS and the app script (an IIFE at the bottom). Loads Quill 2.0.3 and ExcelJS 4.4.0 from jsDelivr (pinned), then `convert.js`.
- **`convert.js`**: pure helpers on `window.WaConvert` (or `module.exports` in Node): WhatsApp text ↔ Quill (`markupToHtml`, `deltaToMarkup`, `looksLikeMarkup`), the preview bubble (`whatsappPreviewHtml`), and a guest's message (`renderMessage`, `templateIssues`, `emptyFields`).
- **`tests/convert.test.js`**: `node tests/convert.test.js`, no dependencies. Run it after touching `convert.js`.
- **`data/`**: sample guest list, image and template, used by "🧪 Try with a sample guest list" (only when served over http(s); `fetch` is blocked on `file://`).

## Conventions (easy to break)

- **Excel layout:** headers on **row 2** of the **first sheet** (`HEADER_ROW`), guests from row 3. Columns are matched case-insensitively by header text. Required: `Addressable Names`, `Add to Invite List?`. Optional: `Name` (WhatsApp contact name for 🔍 Copy contact name), `Category`, `Invited?`/`Invited`, `Invited On`, count columns (headers starting with "estimated count", "adults", "kids", "children", "headcount", "pax").
- **Guests are identified by their Excel row number** (from ExcelJS `eachRow`), so duplicate names and blank rows are safe. Yes/No cells accept yes / y / true / 1 / ✓ / ✔.
- **Available guests** = marked to invite, not already `Invited?` = yes, with a non-empty name. Rows marked sent *this session* stay in the list (their `Invited?` now says Yes).
- **Mark as sent** writes `Invited?` = "Yes" and `Invited On` = local time stored as UTC "wall time" (`excelNow()`; read back with `timeZone: "UTC"`), creating either header in the next free column. **Undo** restores the previous cell values (`state.prev`).
- **Templates are stored as WhatsApp text** (`*bold*`, `_italic_`, `~strike~`, ```` ```mono``` ````, `- `/`1. ` lists, `> ` quotes); that's what is copied and downloaded; the editor only displays it as rich text. `renderMessage` turns legacy `**` into `*`, `{name}` into `Addressable Names`, and `{Any Column}` into that row's value (case-insensitive); unknown placeholders are left as typed.
- **WhatsApp marker rules** (markers hug the text, stay on one line, aren't glued to letters/digits) live in `convert.js` `stylePattern`; the editor conversion and the preview share them. Formatting WhatsApp can't show (mid-word, inside monospace) is dropped when converting from the editor.
- **Layout:** column 2 starts with the compact invite-image bar (the image is sent first), then the editor (shows up to 25 lines, then scrolls). The top bar links back to https://vinothhaldorai.com/apps/ (the site this app is listed on).
- **UI text:** button labels say what they do and to what (verb + object, e.g. "⬆️ Upload guest list (.xlsx)", "📋 Copy message text"); no em dashes anywhere on screen.
- **Never insert guest data as HTML:** use `textContent`; the preview goes through `whatsappPreviewHtml`, which escapes everything.

## State and persistence

All state is in the `state` object inside the IIFE. localStorage keys:
- `invite.template`: the template (WhatsApp text), saved on every edit.
- `invite.image`: `{name, type, dataUrl}`; skipped if larger than ~3.5 MB.
- `invite.theme`: `"light"` or `"dark"` from the Theme switch; absent means follow the device. A tiny script in `<head>` sets `<html data-theme>` before the page is drawn; the CSS uses dark colours for `[data-theme="dark"]`, or for `prefers-color-scheme: dark` unless `[data-theme="light"]`. `isDark()` follows the same rule for the WhatsApp preview bubbles.
- `invite.session`: file name, workbook bytes (base64), original bytes (if small), selection, current guest, sent rows, previous values, category, `changed`, `savedAt`. Offered back via the "Resume where I left off" banner on load.

"Also save changes straight into <file>" uses the File System Access API (`showOpenFilePicker` + `createWritable`, Chrome/Edge desktop only), opt-in per session; writes go through the serialized `saving` promise chain. Other browsers use "Download updated guest list".

## Copying

`navigator.clipboard.writeText` (with an `execCommand` fallback) and `navigator.clipboard.write([new ClipboardItem({"image/png": blob})])`. Browsers only put PNG on the clipboard, so uploaded images are converted once via canvas (`toPng`, max 2048 px). The ClipboardItem is built synchronously in the click handler (Safari requirement). `flushEdit()` applies pending editor changes before copying.
