// Retakes the README screenshots in docs/screenshots/ from the built-in sample guest list.
//
//   npm install --no-save puppeteer-core@23.11.1
//   node tools/screenshots.js
//
// Uses your installed Chrome (set CHROME to its path if it isn't in the usual macOS place).
// Needs an internet connection, like the app (Quill and ExcelJS load from the CDN).
const path = require("path");
const puppeteer = require("puppeteer-core");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(ROOT, "docs", "screenshots");
const URL = "file://" + path.join(ROOT, "index.html");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Pixel ratios chosen so the files come out 1600 px (desktop) and 450 px (phone) wide.
const DESKTOP = { width: 1440, height: 900, deviceScaleFactor: 1600 / 1440 };
const PHONE = { width: 390, height: 844, deviceScaleFactor: 450 / 390, isMobile: true, hasTouch: true };

async function open(theme, viewport) {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage();
  await page.setViewport(viewport);
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: theme }]);
  await page.goto(URL, { waitUntil: "networkidle0" });
  await page.evaluate(() => localStorage.clear()); // no "Resume where I left off" banner
  await page.reload({ waitUntil: "networkidle0" });
  return { browser, page };
}

// The sample guest list, every guest selected, event details filled in.
async function loadSample(page) {
  await page.click("#try-sample");
  await sleep(1500);
  await page.click("#sample-note-close");
  await page.evaluate(() => {
    const set = (el, v) => {
      el.value = v;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const fields = {
      "ev-name": "Housewarming",
      "ev-date": "2026-11-14",
      "ev-start": "18:30",
      "ev-end": "22:00",
      "ev-address": "12 Example Street, Chennai",
      "ev-host": "The Host Family",
    };
    for (const [id, v] of Object.entries(fields)) set(document.getElementById(id), v);
    document.querySelectorAll("#other-blanks input").forEach((el) => set(el, "dinner"));
  });
  await page.click("#select-visible");
  await sleep(500);
}

const shot = (page, name, height) =>
  page.screenshot({ path: path.join(OUT, name), ...(height && { clip: { x: 0, y: 0, width: 1440, height } }) });

(async () => {
  let { browser, page } = await open("light", DESKTOP);
  await shot(page, "start.png", 660);
  await loadSample(page);
  await shot(page, "setup.png");
  await page.click("#start-sending");
  await sleep(800);
  await shot(page, "send.png", 760);
  while (await page.evaluate(() => document.getElementById("summary").hidden)) {
    await page.click("#mark-sent");
    await sleep(250);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(4000); // let the "Marked … as sent" toast fade
  await shot(page, "summary.png", 405);
  await browser.close();

  ({ browser, page } = await open("dark", PHONE));
  await loadSample(page);
  await page.click("#start-sending");
  await sleep(800);
  await shot(page, "phone-send-dark.png");
  await browser.close();
  console.log("Saved to " + path.relative(process.cwd(), OUT));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
