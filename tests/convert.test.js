// Checks for convert.js. Run with: node tests/convert.test.js (no dependencies).
const fs = require("fs");
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
const sample = fs.readFileSync(path.join(__dirname, "..", "data", "invitation_prompt.md"), "utf8");
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
const ravi = { name: "Ravi & Priya", fields: { name: "Ravi Kumar", adults: "2", kids: "", category: "Family" } };
check("{name} is the greeting", renderMessage("Dear {name},", ravi), "Dear Ravi & Priya,");
check("{Column} is case-insensitive", renderMessage("{Adults} adults, {CATEGORY}", ravi), "2 adults, Family");
check("{Name} is the Name column", renderMessage("Contact: {Name}", ravi), "Contact: Ravi Kumar");
check("unknown placeholder stays", renderMessage("{Table} {x", ravi), "{Table} {x");
check("legacy ** becomes *", renderMessage("**Date:** {name}", { name: "A**B", fields: {} }), "*Date:* A**B");

// --- Warnings
check("template issues", templateIssues("Hi {name} at [Venue], [Venue] and {Table} {adults}", ["name", "adults"]),
  { brackets: ["[Venue]"], unknown: ["{Table}"], missingName: false });
check("missing {name}", templateIssues("Hello all", []).missingName, true);
check("empty fields for a guest", emptyFields("{name}: {Adults} adults, {Kids} kids, {Table}", ravi), ["{Kids}"]);

console.log(`\nFAILURES: ${failures}`);
process.exitCode = failures ? 1 : 0;
