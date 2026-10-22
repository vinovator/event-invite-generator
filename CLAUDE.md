# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A browser-only page for preparing personalised WhatsApp invitations from an Excel guest list. It only drafts and copies messages and never sends them; the user opens each WhatsApp chat themselves (phone numbers are deliberately not used). There is no server, no build step and no package manager.

- **Live:** https://vinovator.github.io/event-invite-generator/ (GitHub Pages, `main` branch, root folder). Pushing to `main` deploys within a minute or two.
- The app is listed on https://vinothhaldorai.com/apps/; the "Back to all apps" breadcrumb in the app bar points there.
- **Locally:** open `index.html` (or run `python3 -m http.server` in the repo). The editor and Excel libraries come from the CDN, so it needs an internet connection.

## Files

- **`index.html`**: the whole app: markup, an inline Lucide icon sprite (ISC licence), CSS and the app script (an IIFE at the bottom). Loads Quill 2.0.3 and ExcelJS 4.4.0 from jsDelivr (pinned), then `convert.js`.
- **`convert.js`**: pure helpers on `window.WaConvert` (or `module.exports` in Node):
  - editor conversions: `markupToHtml`, `deltaToMarkup`, `looksLikeMarkup`;
  - the preview bubble: `whatsappPreviewHtml`;
  - a guest's message: `renderMessage`, `templateIssues`, `emptyFields`;
  - event blanks and links: `fillBlanks`, `templateBlanks`, `formatEventDate`, `formatClock`, `mapLink`, `calendarLink`.
- **`tests/convert.test.js`**: `node tests/convert.test.js`, no dependencies. Run it after touching `convert.js`.
- **`manifest.webmanifest`** and **`icons/`** (192, 512, maskable 512 and the 180 px Apple touch icon): install as an app, opening in its own window. The More menu's "Install this app" uses Chrome/Edge's `beforeinstallprompt` (shown only when the browser offers it); on an iPhone or iPad it explains Share, then Add to Home Screen. The two `<meta name="theme-color">` tags are kept in step with the theme by `renderThemeToggle`, so the installed window's title bar matches the app bar. No service worker: nothing is cached, so a deploy shows up straight away.
- **The sample** ("Try with a sample guest list") is built in the script, not loaded from files, so it also works from `file://`: `guestListWorkbook(SAMPLE_GUESTS)` (the same builder as the blank template) and `sampleImage()` (a placeholder drawn on a canvas). Sample guests are numbered (Guest-1, Guest-2…), not made-up names. `state.sample` stops it from being saved, so it never replaces a real session waiting to be resumed, and its image isn't kept.

## Screens

Three views (`<section id="view-…">`), chosen by `state.view`:
- **`start`**: no guest list yet. A drop zone ("Drop your Excel guest list here") with **Upload guest list**, plus "Try with a sample guest list", "Download blank guest list template" and the format help as small links. The "Resume where I left off" banner appears here.
- **`setup`**: everything to prepare, on one page: **1 Choose guests**, **2 Write the invitation** (invite image, then the message with Edit / WhatsApp preview tabs) and **Event details**, marked optional (it only fills the message's `[blanks]`; typing the details into the message works too). A bar floats at the bottom (`.action-bar`): the selection and headcount, a "Fill in N blanks" / "Fix N issues" button when the message needs it, and **Start sending**.
- **`send`**: one guest at a time. Wider than 900 px, two columns (`.send-layout`): the guest card and the steps on the left (`.send-side`, sticky), the WhatsApp preview on the right (`.send-preview`). Narrower, one column: guest, preview, then the steps floating at the bottom of the screen (`.send-side` is `display: contents` and `.send-actions` sticky). A one-row header (`.send-head`: back, progress bar, count, and the download link once there are changes). On a laptop the preview image is capped at 120 px and the preview text is 14 px, so a typical message fits beside the buttons without scrolling. Once every selected guest is marked as sent, a summary card appears at the top of this screen (headcount, Download updated guest list, Invite more guests).

Navigation goes through `go(view)`: it renders the view (`renderView`, which also falls back to a valid one: no list means `start`, nothing selected means `setup`) and then `showView` adds a browser history entry, scrolls to the top and focuses the first visible `h2[tabindex="-1"]`. The browser's Back/Forward buttons move between set-up and sending (`popstate`; `history.scrollRestoration` is manual). Content is rendered whenever state changes (`renderAll`, `renderMessages`…), for every view, so switching views only toggles what's visible.

**Keyboard in send mode:** the step numbers (1, 2, 3…) press the numbered buttons, Enter marks as sent and moves on (or moves on if already sent), ←/→ change guest. Ignored while typing in a field, with a dialog or the menu open, or with a modifier key; Enter on any other button keeps its normal meaning.

**Drag and drop:** an .xlsx on the start screen or the set-up page opens it (in Chrome/Edge `getAsFileSystemHandle` also gives a handle, so "save straight into" works); an image on the set-up page becomes the invite image. Drops while sending are ignored.

**More menu** (app bar): the rarer actions: upload a different guest list, download updated / original guest list, download all messages, blank template, the format help (a `<dialog>`), and "Clear data saved in this browser" (asks for a second click).

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
- **Warnings:** shown once, above the message (`renderTemplateWarnings`): unfilled `[blanks]` (with a "Fill in event details" button), unknown `{placeholders}`, no `{name}`, and `{columns}` that are empty for some selected guests. The bar's button counts the message problems (not the empty columns). The send card only shows guest-specific ones.
- **Layout:**
  - Set-up page (`.setup`, grid areas): three columns from 1200 px (guests, invitation, event details); two from 901 px (event details under the invitation); one below that (guests, invitation, event details). Event details never sit above the message. The guests card is sticky on screens at least 760 px tall, its list filling the room above the bar. The editor shows 25 lines, then scrolls. The page is up to 1400 px wide; the send screen stays at 1120 px.
  - The send card has numbered steps (1 Copy contact name, 2 Copy invite image, 3 Copy message text, 4 Mark as sent); the image step drops out when no image is attached, and a step shows a tick once done for that guest (`state.copied`).
  - Previews use `renderChat(prefix, message)`: an image bubble (when attached) and the text bubble on a WhatsApp chat background, under a label chip (`.chat-chip`, like WhatsApp's date labels). The bubble's text size comes from `.chat` in the CSS (15 px; 14 px in the laptop send preview), not from `whatsappPreviewHtml`.
- **Look:** colours are CSS variables (`--bg` soft grey page, `--surface` white cards with `--shadow`, `--accent` WhatsApp green), redefined for dark mode. Three button tiers: `.btn.primary` (filled, one per screen), `.btn` (soft tint, the default) and `.btn.tertiary` (text only); `.btn.ghost` for the app bar icons. Spacing is on an 8 px grid; touch screens get 44 px targets and 16 px inputs (no iOS zoom).
- **UI text:** button labels say what they do and to what (verb + object); no em dashes anywhere on screen. Icons come from the sprite (`<svg class="icon"><use href="#i-name"/></svg>` in markup, `iconEl(name)` in the script), not emoji. Emoji inside message content are fine.
- **Never insert guest data as HTML:** use `textContent`; the preview goes through `whatsappPreviewHtml`, which escapes everything.

## State and persistence

All state is in the `state` object inside the IIFE. localStorage keys:
- `invite.template`: the template (WhatsApp text), saved on every edit.
- `invite.event`: Event details (`name`, `date`, `start`, `end`, `address`, `host`, `other`).
- `invite.image`: `{name, type, dataUrl}`; skipped if larger than about 3.5 MB.
- `invite.theme`: `"light"` or `"dark"`, only while it differs from the device setting.
- `invite.session`: file name, workbook bytes (base64), original bytes (if small), selection, current guest, sent rows, previous values, category, `changed`, `view`, `savedAt`. Offered back by the "Resume where I left off" banner on load, which reopens the same screen. Not written for the sample.

**Theme:** a script in `<head>` sets `<html data-theme>` before the page is drawn. The sun/moon toggle switches between light and dark; choosing what the device already uses clears the saved choice, so the page follows the device again. `isDark()` follows the same rule for the WhatsApp preview bubbles.

**Saving into the opened file:** "Also save changes straight into <file>" (under the guest list) uses the File System Access API (`showOpenFilePicker` + `createWritable`, Chrome/Edge desktop only). It's opt-in per session, and writes go through the serialized `saving` promise chain. Other browsers use "Download updated guest list (.xlsx)".

## Copying

- **Text:** `navigator.clipboard.writeText`, with an `execCommand` fallback.
- **Image:** `navigator.clipboard.write([new ClipboardItem({"image/png": blob})])`. Browsers only put PNG on the clipboard, so uploaded images are converted once via canvas (`toPng`, max 2048 px). The ClipboardItem is built synchronously in the click handler (a Safari requirement).
- `flushEdit()` applies pending editor changes before copying.
