/* Word-like editor for the invitation template: a Streamlit custom component
 * without a build step. This file implements the small postMessage protocol
 * that streamlit-component-lib normally provides.
 *
 * Args from Python: value (WhatsApp text) and version (bumped whenever Python
 * replaces the text, e.g. a template file was loaded).
 * Returns {text, version}: the edited WhatsApp text and the version it is based on.
 */
(function () {
  "use strict";

  const { markupToHtml, deltaToMarkup, looksLikeMarkup } = window.WaConvert;

  function send(type, data) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
  }

  let lastHeight = 0;
  function updateHeight() {
    const height = Math.ceil(document.body.getBoundingClientRect().height) + 2;
    if (height !== lastHeight) {
      lastHeight = height;
      send("streamlit:setFrameHeight", { height });
    }
  }

  // Streamlit sometimes re-creates this frame (seen once per session, on the
  // first edit). Keep the latest edit and the cursor on the parent page (gone
  // on a page reload), so a new frame carries on where the user left off.
  const memory = (function () {
    try {
      return (window.parent.waEditorMemory = window.parent.waEditorMemory || {});
    } catch (e) {
      return {};
    }
  })();

  let quill = null;
  let plain = null; // fallback <textarea> when Quill can't load (e.g. offline)
  let version = null; // version of the text currently loaded
  let lastSent = null;
  let timer = null;

  function currentText() {
    return quill ? deltaToMarkup(quill.getContents()) : plain.value;
  }

  function flush() {
    clearTimeout(timer);
    timer = null;
    if (version === null) return;
    const text = currentText();
    if (text === lastSent) return;
    lastSent = text;
    send("streamlit:setComponentValue", { value: { text, version }, dataType: "json" });
  }

  function scheduleFlush() {
    clearTimeout(timer);
    timer = setTimeout(flush, 500);
  }

  function load(text) {
    if (quill) {
      quill.setContents(quill.clipboard.convert({ html: markupToHtml(text) }), "silent");
      quill.history.clear();
      lastSent = deltaToMarkup(quill.getContents());
    } else {
      plain.value = text;
      lastSent = text;
    }
  }

  function insertName() {
    if (quill) {
      const range = quill.getSelection(true);
      quill.insertText(range.index, "{name}", "user");
      quill.setSelection(range.index + "{name}".length, 0, "user");
    } else {
      plain.setRangeText("{name}", plain.selectionStart, plain.selectionEnd, "end");
      plain.focus();
      scheduleFlush();
    }
  }

  function setupQuill() {
    const Delta = Quill.import("delta");
    quill = new Quill("#editor", {
      theme: "snow",
      // Only what WhatsApp can show - anything else is dropped, also when pasting.
      formats: ["bold", "italic", "strike", "code", "list", "blockquote"],
      placeholder: "Write the invitation here. Use + {name} for the guest's name.",
      modules: {
        toolbar: "#toolbar",
        keyboard: {
          bindings: {
            strike: {
              key: ["x", "X"],
              shortKey: true,
              shiftKey: true,
              handler(range, context) {
                this.quill.format("strike", !context.format.strike, "user");
              },
            },
          },
        },
      },
    });

    // WhatsApp has no links: keep a pasted link's address as visible text.
    quill.clipboard.addMatcher("A", (node, delta) => {
      const href = node.getAttribute("href") || "";
      if (/^https?:\/\//i.test(href) && !node.textContent.includes(href)) {
        return delta.concat(new Delta().insert(` (${href})`));
      }
      return delta;
    });

    // Plain text that already uses WhatsApp formatting (e.g. copied from a chat
    // or an old template) is pasted as formatted text, not as asterisks.
    quill.root.addEventListener(
      "paste",
      (event) => {
        const data = event.clipboardData;
        if (!data || Array.from(data.types).includes("text/html")) return;
        const text = data.getData("text/plain");
        if (!looksLikeMarkup(text)) return;
        event.preventDefault();
        event.stopPropagation();
        const range = quill.getSelection(true);
        const pasted = quill.clipboard.convert({ html: markupToHtml(text) });
        quill.updateContents(new Delta().retain(range.index).delete(range.length).concat(pasted), "user");
        quill.setSelection(range.index + pasted.length(), 0, "silent");
      },
      true
    );

    quill.on("text-change", (delta, oldDelta, source) => {
      if (source !== "user") return;
      memory.draft = { text: currentText(), version };
      scheduleFlush();
    });
    quill.on("selection-change", (range) => {
      memory.cursor = range; // null once the user leaves the editor
    });
    quill.root.addEventListener("blur", flush);
  }

  function setupPlain() {
    plain = document.getElementById("plain");
    plain.hidden = false;
    document.getElementById("editor").hidden = true;
    for (const group of document.querySelectorAll("#toolbar .format-buttons")) group.hidden = true;
    const note = document.getElementById("note");
    note.hidden = false;
    note.textContent =
      "The formatting editor couldn't load (are you offline?). Edit the WhatsApp text directly: " +
      "*bold*, _italic_, ~strikethrough~.";
    plain.addEventListener("input", () => {
      memory.draft = { text: currentText(), version };
      scheduleFlush();
    });
    plain.addEventListener("blur", flush);
  }

  function applyTheme(theme) {
    if (!theme) return;
    const style = document.documentElement.style;
    style.setProperty("--text", theme.textColor);
    style.setProperty("--background", theme.backgroundColor);
    style.setProperty("--secondary-background", theme.secondaryBackgroundColor);
    style.setProperty("--primary", theme.primaryColor);
    if (theme.font) style.setProperty("--font", theme.font);
  }

  document.getElementById("insert-name").addEventListener("click", insertName);
  if (window.Quill) setupQuill();
  else setupPlain();

  window.addEventListener("message", (event) => {
    const msg = event.data;
    if (!msg || msg.type !== "streamlit:render") return;
    applyTheme(msg.theme);
    const args = msg.args || {};
    if (args.version !== version) {
      const newFrame = version === null;
      version = args.version;
      const draft = memory.draft;
      if (newFrame && draft && draft.version === version && draft.text !== args.value) {
        // A re-created frame: restore the edit that hadn't reached Python yet.
        load(draft.text);
        lastSent = null;
        flush();
      } else {
        load(args.value || "");
      }
      memory.draft = { text: currentText(), version };
      if (newFrame && quill && memory.cursor) {
        quill.setSelection(memory.cursor.index, memory.cursor.length, "silent");
      }
    }
    updateHeight();
  });

  new ResizeObserver(updateHeight).observe(document.body);
  send("streamlit:componentReady", { apiVersion: 1 });
})();
