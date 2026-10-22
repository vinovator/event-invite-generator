# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A browser-only page for preparing personalised WhatsApp invitations from an Excel guest list. It only drafts and copies messages and never sends them; the user opens each WhatsApp chat themselves (phone numbers are deliberately not used). There is no server, no build step and no package manager.

- **Live:** https://vinovator.github.io/event-invite-generator/ (GitHub Pages, `main` branch, root folder). Pushing to `main` deploys within a minute or two.
- The app is listed on https://vinothhaldorai.com/apps/; the top bar's "Back to all apps" link points there.
- **Locally:** open `index.html`, or run `python3 -m http.server` in the repo to get the sample-data button.

## Files

- **`index.html`**: the whole app: markup, an inline Lucide icon sprite (ISC licence), CSS and the app script (an IIFE at the bottom). Loads Quill 2.0.3 and ExcelJS 4.4.0 from jsDelivr (pinned), then `convert.js`.
- **`convert.js`**: pure helpers on `window.WaConvert` (or `module.exports` in Node):
  - editor conversions: `markupToHtml`, `deltaToMarkup`, `looksLikeMarkup`;
  - the preview bubble: `whatsappPreviewHtml`;
  - a guest's message: `renderMessage`, `templateIssues`, `emptyFields`;
  - event blanks and links: `fillBlanks`, `templateBlanks`, `formatEventDate`, `formatClock`, `mapLink`, `calendarLink`.
- **`tests/convert.test.js`**: `node tests/convert.test.js`, no dependencies. Run it after touching `convert.js`.
- **`data/`**: sample guest list, image and template, used by "Try with a sample guest list" (only over http(s); `fetch` is blocked on `file://`).

## Conventions (easy to break)

- **Excel layout:** headers on **row 2** of the **first sheet** (`HEADER_ROW`), guests from row 3. Columns are matched case-insensitively by header text.
  - Required: `Addressable Names`, `Add to Invite List?`.
  - Optional: `Name` (WhatsApp contact name for "Copy contact name"), `Category`, `Invited?`/`Invited`, `Invited On`, and count columns (headers starting with "estimated count", "adults", "kids", "children", "headcount", "pax").
- **Guests are identified by their Excel row number** (from ExcelJS `eachRow`), so duplicate names and blank rows are safe. Yes/No cells accept yes / y / true / 1 / ✓ / ✔.
- **Available guests** = marked to invite, not already `Invited?` = yes, with a non-empty name. Rows marked sent *this session* stay in the list (their `Invited?` now says Yes).
- **Mark as sent** writes `Invited?` = "Yes" and `Invited On` = local time stored as UTC "wall time" (`excelNow()`; read back with `timeZone: "UTC"`). It creates either header in the next free column. **Undo** restores the previous cell values (`state.prev`).
- **Templates are stored as WhatsApp text** (`*bold*`, `_italic_`, `~strike~`, ```` ```mono``` ````, `- `/`1. ` lists, `> ` quotes); that's what is copied and downloaded, and the editor only displays it as rich text.
- **Two kinds of fill-ins:**
  - **`{placeholders}` are per guest** (`renderMessage`): `{name}` is `Addressable Names`, and `{Any Column}` is that row's value (case-insensitive). Legacy `**` becomes `*`.
  - **`[blanks]` are per event** (`fillBlanks`, from the Event details panel): `EVENT_FIELDS` maps blank names such as `[Date]`, `[Venue]`, `[Host Name]`, `[Map link]` and `[Calendar link]` to the event fields. Any other blank is stored in `event.other` under its normalised key.
  - Unknown placeholders and empty blanks are left as typed.
  - A guest's message is `messageFor(guest)` = `renderMessage(fillBlanks(template, event), guest)`. Use it everywhere text is shown or copied.
- **Event formatting is done by hand** (browser locale data differs): "Saturday 14 November 2026", "6:30 pm to 10:00 pm". Calendar links use wall-clock times plus the browser's time zone (`ctz`); no end time means 3 hours, and no start time means all day.
- **WhatsApp marker rules** (markers hug the text, stay on one line, aren't glued to letters or digits) live in `convert.js` `stylePattern`; the editor conversion and the preview share them. Formatting WhatsApp can't show (mid-word, inside monospace) is dropped when converting from the editor.
- **Warnings:** message-wide ones (unfilled `[blanks]`, unknown `{placeholders}`, no `{name}`) appear once, above the editor in column 2. The send card only shows guest-specific ones (columns empty for that guest).
- **Layout:**
  - Column 2 runs: invite-image bar, Event details, warnings, then the editor (shows 25 lines, then scrolls). The preview and the upload/download message panels are folded underneath.
  - The send card has numbered steps (1 Copy contact name, 2 Copy invite image, 3 Copy message text, 4 Mark as sent); the image step drops out when no image is attached.
  - "What should my Excel guest list look like?" is open until a list is loaded.
- **UI text:** button labels say what they do and to what (verb + object); no em dashes anywhere on screen. Icons come from the sprite (`<svg class="icon"><use href="#i-name"/></svg>` in markup, `iconEl(name)` in the script), not emoji. Emoji inside message content are fine.
- **Never insert guest data as HTML:** use `textContent`; the preview goes through `whatsappPreviewHtml`, which escapes everything.

## State and persistence

All state is in the `state` object inside the IIFE. localStorage keys:
- `invite.template`: the template (WhatsApp text), saved on every edit.
- `invite.event`: Event details (`name`, `date`, `start`, `end`, `address`, `host`, `other`).
- `invite.image`: `{name, type, dataUrl}`; skipped if larger than about 3.5 MB.
- `invite.theme`: `"light"` or `"dark"`, only while it differs from the device setting.
- `invite.session`: file name, workbook bytes (base64), original bytes (if small), selection, current guest, sent rows, previous values, category, `changed`, `savedAt`. Offered back by the "Resume where I left off" banner on load.

**Theme:** a script in `<head>` sets `<html data-theme>` before the page is drawn. The sun/moon toggle switches between light and dark; choosing what the device already uses clears the saved choice, so the page follows the device again. `isDark()` follows the same rule for the WhatsApp preview bubbles.

**Saving into the opened file:** "Also save changes straight into <file>" uses the File System Access API (`showOpenFilePicker` + `createWritable`, Chrome/Edge desktop only). It's opt-in per session, and writes go through the serialized `saving` promise chain. Other browsers use "Download updated guest list".

## Copying

- **Text:** `navigator.clipboard.writeText`, with an `execCommand` fallback.
- **Image:** `navigator.clipboard.write([new ClipboardItem({"image/png": blob})])`. Browsers only put PNG on the clipboard, so uploaded images are converted once via canvas (`toPng`, max 2048 px). The ClipboardItem is built synchronously in the click handler (a Safari requirement).
- `flushEdit()` applies pending editor changes before copying.
