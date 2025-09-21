function applyTemplate(kind) {
  // Pre-fills fields based on selected template
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
  switch (kind) {
    case "festival":
      set("type", "caption");
      set("platform", "Instagram");
      set("tone", "Festive");
      set("product_attributes", "limited edition, handcrafted, vibrant motifs");
      set("audience", "festival shoppers, gift seekers");
      break;
    case "seasonal":
      set("type", "description");
      set("platform", "Generic");
      set("tone", "Elegant");
      set("product_attributes", "lightweight, breathable, summer palette");
      set("audience", "style-conscious, seasonal refresh");
      break;
    case "eco":
      set("type", "story");
      set("platform", "Etsy");
      set("tone", "Minimal");
      set("materials", "organic cotton, natural dyes, upcycled materials");
      set("audience", "eco-conscious buyers");
      break;
    case "gifts":
      set("type", "ad_copy");
      set("platform", "Instagram");
      set("tone", "Warm");
      set("product_attributes", "gift-ready packaging, thoughtful, personalized");
      set("audience", "last-minute gift shoppers");
      break;
    case "local_fair":
      set("type", "caption");
      set("platform", "Instagram");
      set("tone", "Bold");
      set("region", "Local pop-up fair");
      set("product_attributes", "meet the maker, limited stock, community event");
      break;
  }
}

async function generate() {
  const payload = {
    artisan_name: document.getElementById("artisan_name").value,
    craft_type: document.getElementById("craft_type").value,
    region: document.getElementById("region").value,
    materials: document.getElementById("materials").value,
    product_name: document.getElementById("product_name").value,
    product_attributes: document.getElementById("product_attributes").value,
    audience: document.getElementById("audience").value,
    tone: document.getElementById("tone").value,
    lang: document.getElementById("lang").value,
    type: document.getElementById("type").value,
    platform: document.getElementById("platform").value,
  };

  const output = document.getElementById("output");
  output.textContent = "Generating…";

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (data.ok) {
      output.textContent = data.result;
    } else {
      output.textContent = "Error: " + (data.error || "Unknown error");
    }
  } catch (err) {
    output.textContent = "Network error: " + err.message;
  }
}

async function analyzeImage() {
  const output = document.getElementById("output");
  const fileInput = document.getElementById("image");
  const file = fileInput.files[0];
  if (!file) {
    output.textContent = "Please choose an image (PNG/JPG/WEBP).";
    return;
  }

  const form = new FormData();
  form.append("image", file);
  form.append("artisan_name", document.getElementById("artisan_name").value);
  form.append("craft_type", document.getElementById("craft_type").value);
  form.append("region", document.getElementById("region").value);
  form.append("materials", document.getElementById("materials").value);
  form.append("product_name", document.getElementById("product_name").value);
  form.append("product_attributes", document.getElementById("product_attributes").value);
  form.append("audience", document.getElementById("audience").value);
  form.append("tone", document.getElementById("tone").value);
  form.append("lang", document.getElementById("lang").value);
  form.append("platform", document.getElementById("platform").value);

  output.textContent = "Analyzing image…";

  try {
    const res = await fetch("/api/analyze-image", {
      method: "POST",
      body: form,
    });

    const data = await res.json();
    if (data.ok) {
      output.textContent = data.result;
    } else {
      output.textContent = "Error: " + (data.error || "Unknown error");
    }
  } catch (err) {
    output.textContent = "Network error: " + err.message;
  }
}

function copyOutput() {
  const output = document.getElementById("output").textContent;
  if (!output) return;
  navigator.clipboard.writeText(output).then(() => {
    // Simple feedback
  });
}

function downloadOutput() {
  const text = document.getElementById("output").textContent || "";
  if (!text.trim()) return;
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "artisan-output.txt";
  a.click();
  URL.revokeObjectURL(url);
}

async function generateVideo() {
  const output = document.getElementById("output");
  const imagesInput = document.getElementById("images");
  const audioInput = document.getElementById("audio");
  const captionsEl = document.getElementById("captions");
  const durationEl = document.getElementById("duration");
  const sizeEl = document.getElementById("size");
  const fitEl = document.getElementById("fit");
  const fontSizeEl = document.getElementById("font_size");

  const files = imagesInput?.files || [];
  if (!files.length) {
    output.textContent = "Please select at least one image.";
    return;
  }

  const form = new FormData();
  for (const f of files) form.append("images", f);
  if (audioInput?.files?.[0]) form.append("audio", audioInput.files[0]);
  form.append("captions", captionsEl?.value || "");
  form.append("duration", durationEl?.value || "2.5");
  form.append("size", sizeEl?.value || "720x720");
  form.append("fit", fitEl?.value || "cover");
  form.append("font_size", fontSizeEl?.value || "36");

  const logoInput = document.getElementById("logo");
  const logoSizeEl = document.getElementById("logo_size");
  const logoPosEl = document.getElementById("logo_pos");
  if (logoInput?.files?.[0]) form.append("logo", logoInput.files[0]);
  if (logoSizeEl?.value) form.append("logo_size", logoSizeEl.value);
  if (logoPosEl?.value) form.append("logo_pos", logoPosEl.value);

  output.textContent = "Generating video… this may take a moment.";

  try {
    const res = await fetch("/api/generate-video", { method: "POST", body: form });

    const ct = res.headers.get("content-type") || "";
    if (!res.ok) {
      if (ct.includes("application/json")) {
        const j = await res.json();
        output.textContent = "Error: " + (j.error || res.statusText);
      } else {
        output.textContent = "Error generating video.";
      }
      return;
    }

    if (ct.includes("application/json")) {
      const j = await res.json();
      output.textContent = j.ok ? "Video generated." : ("Error: " + (j.error || "Unknown error"));
      return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "artisan-reel.mp4";
    a.click();
    URL.revokeObjectURL(url);
    output.textContent = "Downloaded: artisan-reel.mp4";
  } catch (err) {
    output.textContent = "Network error: " + err.message;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const templateSel = document.getElementById("template");
  if (templateSel) {
    templateSel.addEventListener("change", (e) => applyTemplate(e.target.value));
  }
  const genBtn = document.getElementById("generate_btn");
  const analyzeBtn = document.getElementById("analyze_btn");
  const copyBtn = document.getElementById("copy_btn");
  const dl = document.getElementById("download_btn");
  const vb = document.getElementById("video_btn");

  if (genBtn) genBtn.addEventListener("click", async () => {
    genBtn.disabled = true; genBtn.textContent = "Generating…";
    try { await generate(); } finally { genBtn.disabled = false; genBtn.textContent = "Generate"; }
  });

  if (analyzeBtn) analyzeBtn.addEventListener("click", async () => {
    analyzeBtn.disabled = true; analyzeBtn.textContent = "Analyzing…";
    try { await analyzeImage(); } finally { analyzeBtn.disabled = false; analyzeBtn.textContent = "Analyze Image & Suggest Captions"; }
  });

  if (copyBtn) copyBtn.addEventListener("click", copyOutput);
  if (dl) dl.addEventListener("click", downloadOutput);
  if (vb) vb.addEventListener("click", async () => {
    vb.disabled = true; vb.textContent = "Generating…";
    try { await generateVideo(); } finally { vb.disabled = false; vb.textContent = "Generate Video"; }
  });
});