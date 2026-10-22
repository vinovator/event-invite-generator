# Event Invitation Generator

**Open the app: https://vinovator.github.io/event-invite-generator/** (also listed on [vinothhaldorai.com/apps](https://vinothhaldorai.com/apps/)).

A web page for sending personalised event invitations on WhatsApp, one guest at a time, from an Excel guest list. It prepares and copies each guest's invite image and message for you to paste into WhatsApp. It never sends anything itself.

Everything runs in your browser: your guest list, message and progress never leave your device. There is nothing to install, and it works on a phone too.

## How it works

1. **Guest list:** click **Upload guest list (.xlsx)**, or start from **Download blank guest list template (.xlsx)**. Unsure about the layout? Open **What should my Excel guest list look like?** **Try with a sample guest list** loads a demo.
2. **Pick guests:** filter by **Category**, search, then **Select all shown** or tick guests one by one. Headcount totals (Estimated Count, Adults, Kids…) are added up for the selected and the sent guests.
3. **Invite image & message:**
   - **Invite image:** upload it once. It's sent as its own post, before the text.
   - **Event details:** enter the event name, date, start and end time, address and host once. They fill the message's `[blanks]`, such as `[Date]` and `[Address]`, for every guest. **Insert map link** and **Insert "Add to calendar" link** add a Google Maps link and a Google Calendar link.
   - **Message:** write it in the Word-like editor (bold, italic, strikethrough, monospace, lists, quotes). **+ Insert a guest detail** adds `{name}` or any column, e.g. `{Adults}`. A warning above the editor lists anything still to fill in.
4. **Copy & send, one guest at a time,** following the numbered steps on the card:
   1. **Copy contact name**, then paste it into WhatsApp's search to open the chat;
   2. **Copy invite image**, paste it and send;
   3. **Copy message text**, paste it and send;
   4. **Mark as sent & go to next guest** (with **Undo: mark as not sent**).

Marking a guest as sent fills in `Invited?` = Yes and `Invited On` (date and time) in the workbook. Use **Download updated guest list (.xlsx)** at any time; in Chrome or Edge you can tick *Also save changes straight into …* to write straight back into your Excel file. **Download original guest list (backup)** gives you the file as you uploaded it.

Progress, message, event details and image are kept in the browser: after a refresh, click **Resume where I left off**. **Clear data saved in this browser** (top right) removes it all, e.g. on a shared computer. The sun/moon button at the top switches between light and dark; until you choose, it follows your device.

## Guest list format

Headers go on **row 2** of the **first sheet** (row 1 is free for notes or totals); guests start on row 3.

| Column | Required | Used for |
|---|---|---|
| `Addressable Names` | ✅ | The greeting, e.g. "Ravi & Priya": `{name}` in the message |
| `Add to Invite List?` | ✅ | `Yes` to include (`Y`, `TRUE`, `✓` also work) |
| `Name` | | The contact's name as saved in WhatsApp, copied by *Copy contact name* |
| `Category` | | The category filter (Family, Friends, Work…) |
| `Estimated Count`, `Adults`, `Kids…` | | Headcount totals |
| `Invited?`, `Invited On` | | Filled in by *Mark as sent* (added if missing); guests already marked `Yes` are skipped |
| anything else | | Available as `{Column name}` in the message |

## Two kinds of fill-ins

| In the message | Filled from | |
|---|---|---|
| `{name}`, `{Adults}`, `{any column}` | that guest's row in the Excel | different for each guest |
| `[Event Name]`, `[Date]`, `[Time]`, `[Address]`, `[Host Name]`, `[Map link]`, `[Calendar link]` | Event details | the same for everyone |

`[Venue]` and `[Location]` also take the address, and `[Host]` the host name. Any other blank, such as `[Activity/Meal]`, gets its own box in Event details. Dates read like "Saturday 14 November 2026" and times like "6:30 pm to 10:00 pm".

## Formatting

Select text and use the toolbar, or press **⌘B / Ctrl+B** (bold), **⌘I / Ctrl+I** (italic), **⌘⇧X / Ctrl+Shift+X** (strikethrough). **Preview: how WhatsApp will show it** shows exactly what the guest will see.

Behind the scenes the message is kept in WhatsApp's own formatting. That's what gets copied and what *Download this message (.txt)* saves: `*bold*`, `_italic_`, `~strike~`, ```` ```monospace``` ````, `- list`, `> quote`. WhatsApp has no underline, colours or font sizes, and can't format part of a word, so those are dropped. A link pasted from a web page keeps its address as text.

## Can the image and text be copied together?

No. The clipboard holds one item at a time, so they're copied (and pasted) one after the other. Tip: send the image once to your own *Message yourself* chat and forward it to up to 5 chats at a time, then use the app just for the personal text.

## Limitations

- No automatic sending and no WhatsApp API: you press Send.
- Saving the workbook rewrites it with ExcelJS: formulas, styles and dropdowns are kept, but charts, pictures and pivot tables inside the workbook are dropped (use *Download original guest list* if you need them).
- Saving straight into the Excel file needs Chrome or Edge on a computer; other browsers download an updated copy instead.
- The "Add to calendar" link opens Google Calendar.

## Running it on your own computer

Download the repository (*Code → Download ZIP*), unzip it and double-click `index.html` (Chrome or Edge recommended). The editor and Excel libraries load from the jsDelivr CDN, so the first visit needs an internet connection. *Try with a sample guest list* only appears when the page is served over the web.

## For developers

- No build step: `index.html` (page, styles, icon sprite and app script) and `convert.js` (WhatsApp text conversions, event blanks and links; also loadable in Node).
- Tests: `node tests/convert.test.js`
- Hosting: GitHub Pages serves the `main` branch (root folder), so pushing to `main` updates the live site within a minute or two.
- Icons: [Lucide](https://lucide.dev) (ISC licence), inlined as an SVG sprite.
