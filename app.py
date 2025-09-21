import os
import io
import tempfile

from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import google.generativeai as genai

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, afx
import textwrap

load_dotenv()

app = Flask(__name__)
# Increase upload limit to accommodate multiple images and optional audio (64 MB)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB upload limit

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Lazy initialize the Gemini model so the UI can load even if the key is missing
_model = None

def get_model() -> genai.GenerativeModel:
    global _model
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Put it in .env or environment variables.")
    if _model is None:
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(MODEL_NAME)
    return _model


def _platform_guidance(platform: str, content_type: str) -> str:
    platform = (platform or "").lower()
    if platform == "instagram":
        if content_type == "caption":
            return "Focus on a strong first hook, keep it under 25 words, minimal emojis, include soft CTA (e.g., Discover more)."
        return "Style for Instagram: concise, emotive, and scannable."
    if platform == "etsy":
        return (
            "Style for Etsy: include materials, dimensions if available, care instructions, and handmade authenticity. Use friendly tone."
        )
    if platform == "amazon":
        return (
            "Style for Amazon: clear value proposition, bullet-like clarity (but keep as text), features/benefits first, then care and warranty if any."
        )
    return "Style for general web: clear, authentic, and audience-aligned."


def build_prompt(payload: dict) -> str:
    content_type = payload.get("type", "story")
    artisan_name = payload.get("artisan_name", "").strip()
    craft_type = payload.get("craft_type", "").strip()
    region = payload.get("region", "").strip()
    materials = payload.get("materials", "").strip()
    product_name = payload.get("product_name", "").strip()
    product_attributes = payload.get("product_attributes", "").strip()
    audience = payload.get("audience", "").strip()
    tone = payload.get("tone", "Warm").strip()
    lang = payload.get("lang", "English").strip()
    platform = payload.get("platform", "Generic").strip()

    base_context = f"""
You are helping a local Indian artisan communicate their craft to digital audiences.
- Artisan: {artisan_name or "N/A"}
- Craft: {craft_type or "N/A"}
- Region: {region or "N/A"}
- Materials/Techniques: {materials or "N/A"}
- Product: {product_name or "N/A"}
- Key attributes: {product_attributes or "N/A"}
- Target audience: {audience or "General digital audience"}
- Preferred tone: {tone}
- Language: {lang}
- Platform: {platform}
Provide clear, culturally respectful, high-converting content.
Additional platform guidance: {_platform_guidance(platform, content_type)}
"""

    if content_type == "story":
        return base_context + """
Task: Write a compelling artisan story (120–180 words) that explains heritage, process, and cultural significance, with a gentle call-to-action.
Avoid exaggeration; keep it authentic and human.
"""
    elif content_type == "description":
        return base_context + """
Task: Write an e-commerce product description (70–120 words) focusing on benefits, materials, craftsmanship, care, and ideal usage. Include a 1-line headline first.
"""
    elif content_type == "caption":
        return base_context + """
Task: Create 3 short social captions (each ≤ 25 words) optimized for Instagram/Facebook. Vary hooks, keep it authentic, and avoid salesy language.
Return as a numbered list.
"""
    elif content_type == "hashtags":
        return base_context + """
Task: Suggest 10 discoverable hashtags mixing niche craft terms and broader categories. Return as space-separated hashtags on one line.
"""
    elif content_type == "ad_copy":
        return base_context + """
Task: Create 2 concise ad copies (≤ 20 words each) for a performance ad. Include value prop and a clear CTA, no clickbait.
Return as a numbered list.
"""
    else:
        return base_context + "Task: Provide a clear 2-paragraph narrative combining story and product pitch."


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate_text():
    try:
        data = request.get_json(force=True)
        prompt = build_prompt(data)

        generation_config = {
            "temperature": 0.9 if data.get("type") == "story" else 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 512,
        }

        resp = get_model().generate_content(
            prompt,
            generation_config=generation_config,
        )

        text = resp.text.strip() if hasattr(resp, "text") and resp.text else "No content generated."
        return jsonify({"ok": True, "result": text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    try:
        # Expect multipart/form-data with fields + file under key 'image'
        img = request.files.get("image")
        if not img or img.filename == "":
            return jsonify({"ok": False, "error": "No image uploaded."}), 400

        allowed = {"image/jpeg", "image/png", "image/webp"}
        mime = img.mimetype or ""
        if mime not in allowed:
            return jsonify({"ok": False, "error": "Unsupported image type. Use PNG, JPG, or WEBP."}), 400

        image_bytes = img.read()
        if not image_bytes:
            return jsonify({"ok": False, "error": "Empty image file."}), 400

        # Collect optional text fields
        payload = {
            "artisan_name": request.form.get("artisan_name", ""),
            "craft_type": request.form.get("craft_type", ""),
            "region": request.form.get("region", ""),
            "materials": request.form.get("materials", ""),
            "product_name": request.form.get("product_name", ""),
            "product_attributes": request.form.get("product_attributes", ""),
            "audience": request.form.get("audience", ""),
            "tone": request.form.get("tone", "Warm"),
            "lang": request.form.get("lang", "English"),
            "platform": request.form.get("platform", "Generic"),
        }

        prompt = (
            build_prompt({**payload, "type": "caption"})
            + "\nNow first extract key visual attributes (colors, patterns, motifs, materials) from the image,"
              " then propose 3 caption ideas (≤ 20 words each). Return in two sections: Attributes: ... and Captions: ..."
        )

        image_part = {"mime_type": mime, "data": image_bytes}
        resp = get_model().generate_content([prompt, image_part])
        text = resp.text.strip() if hasattr(resp, "text") and resp.text else "No content generated."
        return jsonify({"ok": True, "result": text})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _parse_size(size_str: str, default=(720, 720)):
    try:
        if not size_str:
            return default
        parts = str(size_str).lower().replace(" ", "").split("x")
        if len(parts) != 2:
            return default
        w = int(parts[0]); h = int(parts[1])
        return (max(64, w), max(64, h))
    except Exception:
        return default


def _resize_image(img: Image.Image, size: tuple[int, int], fit: str = "cover") -> Image.Image:
    # Ensure RGB
    img = img.convert("RGB")
    target_w, target_h = size
    iw, ih = img.size
    if fit == "contain":
        # Fit inside, pad with black
        scale = min(target_w / iw, target_h / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        resized = img.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        x = (target_w - nw) // 2
        y = (target_h - nh) // 2
        canvas.paste(resized, (x, y))
        return canvas
    else:
        # cover: scale up and crop center
        scale = max(target_w / iw, target_h / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        resized = img.resize((nw, nh), Image.LANCZOS)
        x = max(0, (nw - target_w) // 2)
        y = max(0, (nh - target_h) // 2)
        return resized.crop((x, y, x + target_w, y + target_h))


def _overlay_logo(frame: Image.Image, logo_img: Image.Image, size_pct: int = 15, position: str = "bottom-right") -> Image.Image:
    """Overlay a logo onto the frame.
    - size_pct: logo width as % of video width
    - position: one of top-left/top-right/bottom-left/bottom-right
    """
    frame = frame.convert("RGBA")
    logo = logo_img.convert("RGBA")
    W, H = frame.size
    # Clamp size
    size_pct = max(5, min(40, int(size_pct or 15)))
    target_w = max(16, int(W * (size_pct / 100.0)))
    # keep aspect ratio
    lw, lh = logo.size
    scale = target_w / lw
    target_h = max(16, int(lh * scale))
    logo_resized = logo.resize((target_w, target_h), Image.LANCZOS)

    # small padding margin
    pad = max(8, int(min(W, H) * 0.02))
    pos = (W - target_w - pad, H - target_h - pad)  # default bottom-right
    p = (position or "bottom-right").lower()
    if p == "top-left":
        pos = (pad, pad)
    elif p == "top-right":
        pos = (W - target_w - pad, pad)
    elif p == "bottom-left":
        pos = (pad, H - target_h - pad)

    frame.alpha_composite(logo_resized, dest=pos)
    return frame.convert("RGB")


def _draw_caption(img: Image.Image, text: str, font_size: int = 36) -> Image.Image:
    if not text.strip():
        return img
    img = img.copy()
    draw = ImageDraw.Draw(img, 'RGBA')
    W, H = img.size
    # Try to load truetype; fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
        # Adjust font_size heuristic for default font scale
        font_size = 16
    # Wrap text to fit width
    max_chars = max(10, int(W / (font_size * 0.6)))
    wrapped = []
    for line in text.splitlines():
        wrapped.extend(textwrap.wrap(line, width=max_chars) or [""])
    display_text = "\n".join(wrapped)
    # Measure text box
    bbox = draw.multiline_textbbox((0, 0), display_text, font=font, spacing=6)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    padding = 20
    rect_w = min(W - 20, tw + padding * 2)
    rect_h = th + padding * 2
    rect_x = (W - rect_w) // 2
    rect_y = H - rect_h - 40
    # Background rectangle with transparency
    draw.rectangle((rect_x, rect_y, rect_x + rect_w, rect_y + rect_h), fill=(0, 0, 0, 160))
    # Center text
    tx = rect_x + (rect_w - tw) // 2
    ty = rect_y + padding
    draw.multiline_text((tx, ty), display_text, fill=(255, 255, 255, 255), font=font, spacing=6, align='center')
    return img


@app.route("/api/generate-video", methods=["POST"])
def generate_video():
    try:
        images = request.files.getlist("images")
        if not images:
            return jsonify({"ok": False, "error": "Please upload at least one image."}), 400
        # Optional audio
        audio_file = request.files.get("audio")
        captions_text = request.form.get("captions", "")
        captions = [c.strip() for c in captions_text.splitlines()] if captions_text else []
        # Clamp duration to sensible bounds
        duration = max(0.5, min(10.0, float(request.form.get("duration", 2.5))))
        size = _parse_size(request.form.get("size", "720x720"))
        fit = (request.form.get("fit", "cover") or "cover").lower()
        font_size = int(request.form.get("font_size", 36))
        # Optional logo watermark controls
        logo_file = request.files.get("logo")
        logo_size = int(request.form.get("logo_size", 15) or 15)
        logo_pos = request.form.get("logo_pos", "bottom-right")

        allowed_img = {"image/jpeg", "image/png", "image/webp"}
        for f in images:
            if (f.mimetype or "") not in allowed_img:
                return jsonify({"ok": False, "error": f"Unsupported image type: {f.mimetype}"}), 400

        with tempfile.TemporaryDirectory() as td:
            clips = []
            try:
                # Build video clips from images
                for idx, f in enumerate(images):
                    img_bytes = f.read()
                    if not img_bytes:
                        continue
                    img = Image.open(io.BytesIO(img_bytes))
                    frame = _resize_image(img, size, fit=fit)
                    cap = captions[idx] if idx < len(captions) else ""
                    framed = _draw_caption(frame, cap, font_size=font_size)
                    # Optional logo overlay
                    if logo_file and (logo_file.filename or "").strip():
                        try:
                            logo_bytes = logo_file.read()
                            logo_img = Image.open(io.BytesIO(logo_bytes))
                            framed = _overlay_logo(framed, logo_img, size_pct=logo_size, position=logo_pos)
                            logo_file.stream.seek(0)  # reset for potential re-reads
                        except Exception:
                            pass
                    arr = np.array(framed.convert("RGB"))
                    clip = ImageClip(arr, duration=max(0.5, duration))
                    clips.append(clip)

                if not clips:
                    return jsonify({"ok": False, "error": "No valid images provided."}), 400

                final = concatenate_videoclips(clips, method="compose")

                # Handle audio if provided
                bgm = None
                audio_path = None
                if audio_file and (audio_file.filename or "").strip():
                    ext = os.path.splitext(audio_file.filename)[1] or ".mp3"
                    audio_path = os.path.join(td, f"music{ext}")
                    audio_file.save(audio_path)
                    try:
                        bgm = AudioFileClip(audio_path).volumex(0.8)
                        # Loop or cut audio to match duration
                        if bgm.duration < final.duration:
                            bgm = afx.audio_loop(bgm, duration=final.duration)
                        else:
                            bgm = bgm.subclip(0, final.duration)
                        final = final.set_audio(bgm)
                    except Exception:
                        # Ignore audio errors and proceed without audio
                        pass


                out_path = os.path.join(td, "artisan-reel.mp4")
                final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="2000k", logger=None)
                # Read the file into memory before cleaning up, to avoid Windows file lock issues
                with open(out_path, "rb") as f:
                    video_bytes = f.read()
            finally:
                # Close clips to release resources on Windows
                for c in clips:
                    try:
                        c.close()
                    except Exception:
                        pass
                try:
                    final.close()  # type: ignore
                except Exception:
                    pass

            # Return file from memory (BytesIO)
            return send_file(io.BytesIO(video_bytes), mimetype="video/mp4", as_attachment=True, download_name="artisan-reel.mp4")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Local dev server
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)