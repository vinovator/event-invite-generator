// Checks for convert.js. Run with: node tests/convert.test.js (no dependencies).
const path = require("path");
const {
  markupToHtml,
  deltaToMarkup,
  looksLikeMarkup,
  whatsappPreviewHtml,
  renderMessage,
  templateIssues,
  emptyFields,
} = require(path.join(__dirname, "..", "convert.js"));

let failures = 0;
function check(label, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) failures++;
  console.log(
    (ok ? "PASS " : "FAIL ") + label +
    (ok ? "" : `\n   got:  ${JSON.stringify(got)}\n   want: ${JSON.stringify(want)}`)
  );
}

const B = { bold: true }, I = { italic: true }, BI = { bold: true, italic: true };
const d = (...ops) => ({ ops });

// --- Editor contents (Quill Delta) -> WhatsApp text
check("bold line", deltaToMarkup(d({ insert: "Subject: Party 🎉", attributes: B }, { insert: "\n" })), "*Subject: Party 🎉*");
check("bold label", deltaToMarkup(d({ insert: "Date:", attributes: B }, { insert: " [Date]\n" })), "*Date:* [Date]");
check("selected trailing space moves out", deltaToMarkup(d({ insert: "Date: ", attributes: B }, { insert: "2 Nov\n" })), "*Date:* 2 Nov");
check("mid-word bold dropped", deltaToMarkup(d({ insert: "Diw", attributes: B }, { insert: "ali\n" })), "Diwali");
check("italic nested in bold", deltaToMarkup(d(
  { insert: "Please join us with ", attributes: B }, { insert: "your family", attributes: BI },
  { insert: ".", attributes: B }, { insert: "\n" })), "*Please join us with _your family_.*");
check("crossing formats split", deltaToMarkup(d(
  { insert: "abc ", attributes: B }, { insert: "def", attributes: BI }, { insert: " ghi", attributes: I }, { insert: "\n" })),
  "*abc _def_* _ghi_");
check("same text bold+italic", deltaToMarkup(d({ insert: "both", attributes: BI }, { insert: "\n" })), "*_both_*");
check("lists", deltaToMarkup(d(
  { insert: "Food" }, { insert: "\n", attributes: { list: "bullet" } },
  { insert: "Music" }, { insert: "\n", attributes: { list: "bullet" } },
  { insert: "Step one" }, { insert: "\n", attributes: { list: "ordered" } },
  { insert: "Step two" }, { insert: "\n", attributes: { list: "ordered" } })), "- Food\n- Music\n1. Step one\n2. Step two");
check("quote", deltaToMarkup(d({ insert: "Dress code" }, { insert: "\n", attributes: { blockquote: true } })), "> Dress code");
check("monospace", deltaToMarkup(d({ insert: "Code: " }, { insert: "1234", attributes: { code: true } }, { insert: "\n" })), "Code: ```1234```");
check("no bold inside monospace", deltaToMarkup(d({ insert: "x", attributes: { code: true, bold: true } }, { insert: "\n" })), "```x```");
check("blank lines kept", deltaToMarkup(d({ insert: "A\n\nB\n" })), "A\n\nB");
check("bold over two lines", deltaToMarkup(d({ insert: "one", attributes: B }, { insert: "\n" }, { insert: "two", attributes: B }, { insert: "\n" })), "*one*\n*two*");
check("punctuation junction", deltaToMarkup(d({ insert: "Hi,", attributes: B }, { insert: "(you)", attributes: I }, { insert: "\n" })), "*Hi,*_(you)_");
check("whitespace-only bold ignored", deltaToMarkup(d({ insert: "a" }, { insert: "  ", attributes: B }, { insert: "b\n" })), "a  b");
check("tamil bold", deltaToMarkup(d({ insert: "வணக்கம்", attributes: B }, { insert: "\n" })), "*வணக்கம்*");
check("images ignored", deltaToMarkup(d({ insert: "a" }, { insert: { image: "x.png" } }, { insert: "b\n" })), "ab");

// --- WhatsApp text -> editor HTML
check("html bold label", markupToHtml("*Date:* [Date]"), "<p><strong>Date:</strong> [Date]</p>");
check("html lists", markupToHtml("- a\n* b\n1. c"), "<ul><li>a</li><li>b</li></ul><ol><li>c</li></ol>");
check("html quote", markupToHtml("> q *b*"), "<blockquote>q <strong>b</strong></blockquote>");
check("html escapes", markupToHtml("<script>&"), "<p>&lt;script&gt;&amp;</p>");
check("html mid-word literal", markupToHtml("a*b*c and 5 * 3"), "<p>a*b*c and 5 * 3</p>");
check("html code + placeholder", markupToHtml("```x``` `y` {name}"), "<p><code>x</code> <code>y</code> {name}</p>");
check("html nested", markupToHtml("*_both_* _*x*_"), "<p><strong><em>both</em></strong> <em><strong>x</strong></em></p>");
check("html blank line", markupToHtml("A\n\nB"), "<p>A</p><p><br></p><p>B</p>");

// --- Paste detection
check("detect bold", looksLikeMarkup("Hello *there*"), true);
check("detect monospace", looksLikeMarkup("code ```x```"), true);
check("plain maths", looksLikeMarkup("5 * 3 = 15"), false);
check("snake_case", looksLikeMarkup("file_name.txt"), false);

// --- Round trip through a stand-in for Quill's HTML import
function htmlToDelta(html) {
  const ops = [], fmt = { bold: 0, italic: 0, strike: 0, code: 0 };
  const tags = { strong: "bold", em: "italic", s: "strike", code: "code" };
  let list = null;
  for (const t of html.match(/<[^>]+>|[^<]+/g) || []) {
    const m = t.match(/^<(\/?)(\w+)>$/);
    if (m) {
      const [, close, tag] = m;
      if (tags[tag]) fmt[tags[tag]] += close ? -1 : 1;
      else if (tag === "ul" || tag === "ol") list = close ? null : (tag === "ul" ? "bullet" : "ordered");
      else if (close && tag === "li") ops.push({ insert: "\n", attributes: { list } });
      else if (close && tag === "blockquote") ops.push({ insert: "\n", attributes: { blockquote: true } });
      else if (close && tag === "p") ops.push({ insert: "\n" });
      continue;
    }
    const attrs = {};
    for (const k in fmt) if (fmt[k] > 0) attrs[k] = true;
    const text = t.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
    ops.push(Object.keys(attrs).length ? { insert: text, attributes: attrs } : { insert: text });
  }
  return { ops };
}
// The sample message in index.html (DEFAULT_TEMPLATE).
const sample = [
  "*Subject: Invitation to [Event Name] 🎉*",
  "",
  "Dear {name},",
  "",
  "We are excited to invite you to [Event Name]! It would mean a lot to us to have *you and your family* with us to celebrate this special milestone.",
  "",
  "Please join us for [Activity/Meal].",
  "",
  "*Date:* [Date]",
  "*Time:* [Time]",
  "*Address:* [Address]",
  "",
  "We really hope to see you there!",
  "",
  "Warm regards,",
  "",
  "*[Host Name]*",
  "",
].join("\n");
check("sample template round-trips", deltaToMarkup(htmlToDelta(markupToHtml(sample))), sample);
const tricky = "*Invitation to our Diwali party 🎉*\n\nDear {name},\nPlease join us with _your family_ & friends <3.\n" +
  "> *Dress:* ethnic\n- Food\n- Music\n1. Arrive\n2. Enjoy\nCode ```A1``` ~old~ new";
check("tricky text round-trips", deltaToMarkup(htmlToDelta(markupToHtml(tricky))), tricky);

// --- Preview bubble
const inner = (html) => html.slice(html.indexOf(">") + 1, -"</div>".length);
check("preview bold + escape", inner(whatsappPreviewHtml("*Hi* <b> & _you_", false)), "<b>Hi</b> &lt;b&gt; &amp; <i>you</i>");
check("preview keeps lines and dashes", inner(whatsappPreviewHtml("- a\n- b", false)), "- a\n- b");
check("preview quote bar", inner(whatsappPreviewHtml("> note", false)).startsWith("<span style=\"border-left"), true);
check("preview multi-line monospace", inner(whatsappPreviewHtml("```a\n*b*```", false)).includes(">a\n*b*</code>"), true);
check("preview dark bubble", whatsappPreviewHtml("x", true).includes("background:#005c4b"), true);

// --- Filling in a guest's message
const guest = { name: "Guest-1 & family", fields: { name: "Guest-1", adults: "2", kids: "", category: "Family" } };
check("{name} is the greeting", renderMessage("Dear {name},", guest), "Dear Guest-1 & family,");
check("{Column} is case-insensitive", renderMessage("{Adults} adults, {CATEGORY}", guest), "2 adults, Family");
check("{Name} is the Name column", renderMessage("Contact: {Name}", guest), "Contact: Guest-1");
check("unknown placeholder stays", renderMessage("{Table} {x", guest), "{Table} {x");
check("legacy ** becomes *", renderMessage("**Date:** {name}", { name: "A**B", fields: {} }), "*Date:* A**B");

// --- Warnings
check("template issues", templateIssues("Hi {name} at [Venue], [Venue] and {Table} {adults}", ["name", "adults"]),
  { brackets: ["[Venue]"], unknown: ["{Table}"], missingName: false });
check("missing {name}", templateIssues("Hello all", []).missingName, true);
check("empty fields for a guest", emptyFields("{name}: {Adults} adults, {Kids} kids, {Table}", guest), ["{Kids}"]);

// --- Event details: [blanks] filled once for every guest
const {
  fillBlanks, templateBlanks, formatEventDate, formatClock, mapLink, calendarLink,
} = require(path.join(__dirname, "..", "convert.js"));
check("event date", formatEventDate("2026-11-14"), "Saturday 14 November 2026");
check("bad event date", formatEventDate("14/11/2026"), "");
check("clock pm", formatClock("18:30"), "6:30 pm");
check("clock midnight", formatClock("00:05"), "12:05 am");
check("clock noon", formatClock("12:00"), "12:00 pm");

const party = {
  name: "Guest-1's 1st Birthday", date: "2026-11-14", start: "18:30", end: "22:00",
  address: "Venue Hall, 1 High Street, Town", host: "Host-1 & family",
  other: { "activity meal": "dinner" }, timeZone: "Europe/London",
};
check("fills the sample template's blanks", fillBlanks(sample, party).split("\n").filter((l) => /Date|Time|Address|Host|join|Subject/.test(l)), [
  "*Subject: Invitation to Guest-1's 1st Birthday 🎉*",
  "Please join us for dinner.",
  "*Date:* Saturday 14 November 2026",
  "*Time:* 6:30 pm to 10:00 pm",
  "*Address:* Venue Hall, 1 High Street, Town",
  "*Host-1 & family*",
]);
check("host blank in bold", fillBlanks("*[Host Name]*", party), "*Host-1 & family*");
check("synonyms and spacing", fillBlanks("[venue] / [ Start Time ] / [EVENT]", party),
  "Venue Hall, 1 High Street, Town / 6:30 pm to 10:00 pm / Guest-1's 1st Birthday");
check("unknown or empty blanks stay", fillBlanks("[Dress code] [Date]", { other: {} }), "[Dress code] [Date]");
check("no event leaves text alone", fillBlanks("[Date]", null), "[Date]");
check("map link", mapLink(party), "https://www.google.com/maps/search/?api=1&query=Venue%20Hall%2C%201%20High%20Street%2C%20Town");
check("map link needs an address", mapLink({}), "");
const cal = new URL(calendarLink(party));
check("calendar link", [cal.origin + cal.pathname, cal.searchParams.get("action"), cal.searchParams.get("text"),
  cal.searchParams.get("dates"), cal.searchParams.get("location"), cal.searchParams.get("ctz")],
  ["https://calendar.google.com/calendar/render", "TEMPLATE", "Guest-1's 1st Birthday", "20261114T183000/20261114T220000",
    "Venue Hall, 1 High Street, Town", "Europe/London"]);
check("calendar: no end time = 3 hours", new URL(calendarLink({ date: "2026-11-14", start: "18:30" })).searchParams.get("dates"),
  "20261114T183000/20261114T213000");
check("calendar: ends after midnight", new URL(calendarLink({ date: "2026-12-31", start: "20:00", end: "01:00" })).searchParams.get("dates"),
  "20261231T200000/20270101T010000");
check("calendar: all-day without a time", new URL(calendarLink({ date: "2026-11-14" })).searchParams.get("dates"), "20261114/20261115");
check("calendar needs a date", calendarLink({ name: "x" }), "");
check("links fill their blanks", fillBlanks("Map: [Map link]\nAdd: [Calendar link]", party).startsWith(
  "Map: https://www.google.com/maps/search/?api=1&query="), true);
check("template blanks", templateBlanks(sample).map((b) => `${b.text}=${b.field}`),
  ["[Event Name]=name", "[Activity/Meal]=null", "[Date]=date", "[Time]=time", "[Address]=address", "[Host Name]=host"]);

console.log(`\nFAILURES: ${failures}`);
process.exitCode = failures ? 1 : 0;
