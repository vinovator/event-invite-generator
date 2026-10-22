/* Conversions between WhatsApp text formatting and the rich-text editor (Quill).
 *
 * The template is stored as WhatsApp text (*bold* _italic_ ~strike~ ```mono```),
 * so it is copied, previewed and saved exactly as WhatsApp needs it; the editor
 * only displays it as rich text. Used by editor.js in the browser and loadable
 * from Node for quick checks.
 */
(function (root) {
  "use strict";

  const WORD = /[\p{L}\p{N}]/u;

  function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Same rules as invite_helpers._style_pattern: WhatsApp only formats when the
  // markers hug the text, stay on one line and aren't glued to letters/digits.
  function stylePattern(marker, flags) {
    const m = marker === "*" ? "\\*" : marker;
    return new RegExp(
      `(?<![\\p{L}\\p{N}${m}])${m}(?=[^\\s${m}])([^${m}\\n]*?[^\\s${m}])${m}(?![\\p{L}\\p{N}${m}])`,
      flags
    );
  }

  // --- WhatsApp text -> HTML that Quill can load ------------------------------

  const INLINE_TAGS = [["*", "strong"], ["_", "em"], ["~", "s"]];

  function inlineToHtml(text) {
    // Park monospace first so its contents are not formatted.
    const stash = [];
    const park = (_, code) => {
      stash.push(`<code>${code}</code>`);
      return `\u0000${stash.length - 1}\u0000`;
    };
    let html = escapeHtml(text).replace(/```(.+?)```/g, park).replace(/`([^`]+)`/g, park);
    for (const [marker, tag] of INLINE_TAGS) {
      html = html.replace(stylePattern(marker, "gu"), `<${tag}>$1</${tag}>`);
    }
    return html.replace(/\u0000(\d+)\u0000/g, (_, i) => stash[Number(i)]);
  }

  function markupToHtml(text) {
    const lines = String(text || "").replace(/\r\n?/g, "\n").split("\n");
    const out = [];
    let list = null;
    const closeList = () => {
      if (list) out.push(`</${list}>`);
      list = null;
    };
    for (const line of lines) {
      // WhatsApp lists: "- item" / "* item" and "1. item"
      const item = line.match(/^(?:([-*•])|\d+[.)]) (.*)$/);
      if (item) {
        const kind = item[1] ? "ul" : "ol";
        if (list !== kind) {
          closeList();
          out.push(`<${kind}>`);
          list = kind;
        }
        out.push(`<li>${inlineToHtml(item[2]) || "<br>"}</li>`);
        continue;
      }
      closeList();
      if (line.startsWith("> ")) {
        out.push(`<blockquote>${inlineToHtml(line.slice(2))}</blockquote>`);
      } else {
        out.push(`<p>${inlineToHtml(line) || "<br>"}</p>`);
      }
    }
    closeList();
    return out.join("");
  }

  const DETECT = ["*", "_", "~"].map((marker) => stylePattern(marker, "u")).concat([/```.+?```/]);

  function looksLikeMarkup(text) {
    return DETECT.some((pattern) => pattern.test(text));
  }

  // --- Quill contents (Delta) -> WhatsApp text --------------------------------

  // Outer to inner when two formats cover exactly the same text.
  const FORMATS = [["bold", "*"], ["italic", "_"], ["strike", "~"], ["code", "```"]];

  function trimRun(run, isSpace) {
    let { start, end } = run;
    while (start < end && isSpace(start)) start++;
    while (end > start && isSpace(end - 1)) end--;
    return start < end ? [{ ...run, start, end }] : [];
  }

  function lineToMarkup(chars) {
    const n = chars.length;
    const isWord = (i) => i >= 0 && i < n && WORD.test(chars[i].ch);
    const isSpace = (i) => /\s/.test(chars[i].ch);

    // 1. Runs of each format, with edge spaces moved outside the markers.
    let runs = [];
    FORMATS.forEach(([name, marker], rank) => {
      for (let i = 0; i < n; ) {
        if (!chars[i].attrs[name]) {
          i++;
          continue;
        }
        let end = i;
        while (end < n && chars[end].attrs[name]) end++;
        runs.push(...trimRun({ name, marker, rank, start: i, end }, isSpace));
        i = end;
      }
    });

    // 2. Split runs that cross another run, so the markers nest properly.
    for (let changed = true; changed; ) {
      changed = false;
      for (const a of runs) {
        const b = runs.find((r) => a.start < r.start && r.start < a.end && a.end < r.end);
        if (b) {
          runs.splice(
            runs.indexOf(b), 1,
            ...trimRun({ ...b, end: a.end }, isSpace),
            ...trimRun({ ...b, start: a.end }, isSpace)
          );
          changed = true;
          break;
        }
      }
    }

    // 3. Drop what WhatsApp can't show: formatting glued to letters/digits
    //    (part of a word) and formatting inside monospace.
    const codeRuns = runs.filter((r) => r.name === "code");
    runs = runs.filter(
      (r) =>
        !isWord(r.start - 1) &&
        !isWord(r.end) &&
        (r.name === "code" || !codeRuns.some((c) => c.start <= r.start && r.end <= c.end))
    );

    // 4. Emit: outer runs open first and close last.
    runs.sort((a, b) => a.start - b.start || b.end - a.end || a.rank - b.rank);
    runs.forEach((r, i) => {
      r.order = i;
    });
    let out = "";
    for (let i = 0; i <= n; i++) {
      for (const r of runs.filter((r) => r.end === i).sort((a, b) => b.order - a.order)) out += r.marker;
      for (const r of runs.filter((r) => r.start === i)) out += r.marker;
      if (i < n) out += chars[i].ch;
    }
    return out;
  }

  function deltaToMarkup(delta) {
    // Split the ops into lines; a line's block format (list, quote) sits on its "\n".
    const lines = [];
    let chars = [];
    for (const op of (delta && delta.ops) || []) {
      if (typeof op.insert !== "string") continue; // embeds (e.g. images) aren't supported
      const attrs = op.attributes || {};
      const parts = op.insert.split("\n");
      parts.forEach((part, i) => {
        for (const ch of part) chars.push({ ch, attrs });
        if (i < parts.length - 1) {
          lines.push({ chars, block: attrs });
          chars = [];
        }
      });
    }
    if (chars.length) lines.push({ chars, block: {} });

    let number = 0;
    return lines
      .map(({ chars, block }) => {
        let prefix = "";
        if (block.list === "ordered") {
          prefix = `${++number}. `;
        } else {
          number = 0;
          if (block.list) prefix = "- ";
          else if (block.blockquote) prefix = "> ";
        }
        return prefix + lineToMarkup(chars);
      })
      .join("\n");
  }

  const api = { markupToHtml, deltaToMarkup, looksLikeMarkup };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.WaConvert = api;
})(typeof window !== "undefined" ? window : globalThis);
