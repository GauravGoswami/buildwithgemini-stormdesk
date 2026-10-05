const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const recordingsDir = path.join(__dirname, "recordings");
  if (!fs.existsSync(recordingsDir)) {
    fs.mkdirSync(recordingsDir, { recursive: true });
  }

  console.log("Launching browser...");
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"]
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: {
      dir: recordingsDir,
      size: { width: 1280, height: 800 }
    }
  });

  const page = await context.newPage();
  console.log("Navigating to http://localhost:8080...");
  await page.goto("http://localhost:8080", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // --- Scenario 1: Why is CLM-1042 flagged? ---
  console.log('Scenario 1: Asking "Why is CLM-1042 flagged?"...');
  await page.fill("#input", "Why is CLM-1042 flagged?");
  await page.click('button[type="submit"]');

  // Wait for the agent response bubble to appear and finish loading
  await page.waitForFunction(() => {
    const agents = document.querySelectorAll(".msg.agent .bubble");
    if (!agents.length) return false;
    const last = agents[agents.length - 1];
    return last.textContent && last.textContent !== "…";
  }, null, { timeout: 120000 });

  console.log("Scenario 1 loaded. Pausing to showcase A2UI card...");
  await page.waitForTimeout(10000);

  // --- Scenario 2: Approve CLM-1003 & generate notice + video ---
  console.log('Scenario 2: Asking "Approve CLM-1003, generate the customer notice graphic, and generate an explainer video for the next steps."...');
  await page.fill("#input", "Approve CLM-1003, generate the customer notice graphic, and generate an explainer video for the next steps.");
  await page.click('button[type="submit"]');

  // Wait for second agent response
  await page.waitForFunction(() => {
    const agents = document.querySelectorAll(".msg.agent .bubble");
    if (agents.length < 2) return false;
    const last = agents[agents.length - 1];
    return last.textContent && last.textContent !== "…";
  }, null, { timeout: 120000 });

  // Wait for video element to be attached and ready
  await page.waitForSelector("video.a2video", { timeout: 120000 });
  await page.waitForSelector("img.a2img", { timeout: 120000 });

  console.log("Scenario 2 loaded. Pausing for video playback in browser...");
  await page.waitForTimeout(18000);

  console.log("Closing browser and saving recording...");
  const videoPath = await page.video().path();
  await page.close();
  await context.close();
  await browser.close();

  console.log("Raw video recorded to:", videoPath);
  const targetWebm = path.join(__dirname, "agent_demo.webm");
  fs.copyFileSync(videoPath, targetWebm);
  console.log("Copied raw video to:", targetWebm);
})();
