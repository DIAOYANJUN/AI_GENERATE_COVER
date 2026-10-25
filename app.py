import streamlit as st
import os
import json
import subprocess
import cv2
from moviepy import VideoFileClip
from openai import OpenAI
from rembg import remove
from PIL import Image

# ---------------- 1. 云端环境自愈 ----------------
@st.cache_resource
def setup_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pass
    subprocess.run(["playwright", "install", "chromium"])

setup_playwright()
from playwright.sync_api import sync_playwright

# ---------------- 2. 页面与配置初始化 ----------------
st.set_page_config(page_title="AI 商业级爆款封面生成器", layout="wide", page_icon="🎬")

st.title("✨ AI 视频金句时间戳同步 & 多风格商业封面生成器")

# 侧边栏 API 配置
st.sidebar.header("🔑 API 配置")
api_key = st.sidebar.text_input("Groq API Key", type="password")
base_url = st.sidebar.text_input("API Base URL", value="https://api.groq.com/openai/v1")

# ---------------- 侧边栏新增：封面风格选择 ----------------
st.sidebar.header("🎨 封面视觉设计")

template_style = st.sidebar.selectbox(
    "选择封面视觉风格",
    [
        "黑金高奢 (Luxury Glass)", 
        "赛博霓虹 (Cyber Glow)", 
        "小红书爆款 (High-CTR Yellow)", 
        "时尚杂志 (Editorial Magazine)"
    ],
    index=0
)

enable_3d_depth = st.sidebar.checkbox("开启 3D 人像遮挡/文字后置效果", value=True, help="使用 AI 抠图将文字穿插在人物身后，大幅提升立体感")

# 动态获取对话模型
available_models = []
if api_key:
    try:
        temp_client = OpenAI(api_key=api_key, base_url=base_url)
        models_res = temp_client.models.list()
        banned_keywords = ["whisper", "safetensors", "guard", "embedding", "moderation", "canopylabs", "orpheus", "tts"]
        available_models = [m.id for m in models_res.data if not any(k in m.id.lower() for k in banned_keywords)]
        available_models.sort(key=lambda x: 0 if "llama" in x.lower() else 1)
    except Exception:
        pass

if not available_models:
    available_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

selected_model = st.sidebar.selectbox("选择 Groq AI 对话模型", available_models, index=0)

uploaded_file = st.file_uploader("上传短视频文件 (MP4 / MOV)", type=["mp4", "mov"])

# ---------------- 3. 主流程处理逻辑 ----------------
if uploaded_file is not None and api_key:
    client = OpenAI(api_key=api_key, base_url=base_url)

    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.read())

    st.video("temp_video.mp4")

    if st.button("🚀 一键生成所选风格封面"):
        try:
            with st.spinner("1/5 正在剥离视频音频..."):
                video = VideoFileClip("temp_video.mp4")
                duration = video.duration
                video.audio.write_audiofile("temp_audio.mp3", logger=None)

            with st.spinner("2/5 使用 Groq Whisper 提取真实语音时间戳..."):
                with open("temp_audio.mp3", "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        file=("temp_audio.mp3", audio_file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json",
                        timestamp_granularities=["segment"]
                    )
                
                raw_segments = getattr(transcription, "segments", [])
                real_segments = []
                for seg in raw_segments:
                    text_val = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                    start_val = seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0)
                    real_segments.append({"start": round(start_val, 2), "text": text_val.strip()})

                if not real_segments:
                    real_segments = [{"start": 0.5, "text": "Pro Quality Video Content"}]

            with st.spinner("3/5 大模型分析提炼震撼金句..."):
                prompt = (
                    "分析字幕挑选最拉满点击率的 1 句金句。\n"
                    + f"字幕：{json.dumps(real_segments, ensure_ascii=False)}\n\n"
                    + "严格只返回 JSON:\n"
                    + '{"golden_quote": "金句原文", "start_time": 秒数(float), "highlight_word": "高亮词"}'
                )

                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "You are a professional social media title designer that outputs raw JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                res = json.loads(response.choices[0].message.content)
                quote = res.get("golden_quote", real_segments[0]["text"])
                target_time = float(res.get("start_time", real_segments[0]["start"]))
                highlight_word = res.get("highlight_word", quote.split()[0] if quote.split() else quote)

                target_time = min(max(0.5, target_time), duration - 0.5)

                video.save_frame("temp_frame.jpg", t=target_time)
                video.close()

            # 抠图处理逻辑 (AI 生成前景蒙版)
            fg_layer_html = ""
            if enable_3d_depth:
                with st.spinner("4/5 正在进行 AI 人像扣图，合成 3D 景深穿插图层..."):
                    input_img = Image.open("temp_frame.jpg")
                    output_img = remove(input_img)
                    output_img.save("temp_fg.png")
                    fg_layer_html = '<div class="fg-layer"></div>'
            else:
                with st.spinner("4/5 跳过抠图，准备普通渲染..."):
                    pass

            with st.spinner(f"5/5 渲染 [{template_style}] 风格 4K 商业网页封面..."):
                formatted_quote = quote.replace(
                    highlight_word, 
                    f'<span class="glow-word">{highlight_word}</span>'
                )

                # ---------------- 根据所选风格配置 CSS 样式 ----------------
                if "Cyber" in template_style:
                    # 赛博霓虹
                    font_import = "@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@800;900&family=Noto+Sans+SC:wght@900&display=swap');"
                    font_family = "'Orbitron', 'Noto Sans SC', sans-serif"
                    glow_color = "#00FFFF"
                    badge_bg = "linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%)"
                    card_bg = "rgba(10, 25, 47, 0.55)"
                    border_color = "rgba(0, 255, 255, 0.4)"
                    badge_text_color = "#000"
                elif "Yellow" in template_style:
                    # 小红书爆款
                    font_import = "@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@900&family=Noto+Sans+SC:wght@900&display=swap');"
                    font_family = "'Montserrat', 'Noto Sans SC', sans-serif"
                    glow_color = "#FFE600"
                    badge_bg = "#FFE600"
                    card_bg = "rgba(0, 0, 0, 0.65)"
                    border_color = "rgba(255, 230, 0, 0.5)"
                    badge_text_color = "#000"
                elif "Magazine" in template_style:
                    # 时尚杂志
                    font_import = "@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@800;900&family=Noto+Serif+SC:wght@900&display=swap');"
                    font_family = "'Cinzel', 'Noto Serif SC', serif"
                    glow_color = "#E6C200"
                    badge_bg = "#FFFFFF"
                    card_bg = "rgba(255, 255, 255, 0.12)"
                    border_color = "rgba(255, 255, 255, 0.4)"
                    badge_text_color = "#000"
                else:
                    # 黑金高奢 (默认)
                    font_import = "@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@900&family=Noto+Sans+SC:wght@900&display=swap');"
                    font_family = "'Montserrat', 'Noto Sans SC', sans-serif"
                    glow_color = "#FFE600"
                    badge_bg = "linear-gradient(90deg, #FFE600 0%, #FF9900 100%)"
                    card_bg = "rgba(18, 18, 18, 0.45)"
                    border_color = "rgba(255, 255, 255, 0.25)"
                    badge_text_color = "#000"

                html_template = (
                    "<!DOCTYPE html>\n"
                    "<html>\n"
                    "<head>\n"
                    "    <style>\n"
                    "        " + font_import + "\n"
                    "        * { box-sizing: border-box; margin: 0; padding: 0; }\n"
                    "        body {\n"
                    "            width: 1080px; height: 1440px;\n"
                    "            background: url('temp_frame.jpg') center/cover no-repeat;\n"
                    "            font-family: " + font_family + ";\n"
                    "            display: flex; flex-direction: column; justify-content: space-between;\n"
                    "            padding: 100px 70px;\n"
                    "            position: relative; overflow: hidden;\n"
                    "        }\n"
                    "        .overlay {\n"
                    "            position: absolute; top:0; left:0; width:100%; height:100%;\n"
                    "            background: linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.75) 100%);\n"
                    "            backdrop-filter: blur(4px);\n"
                    "            z-index: 1;\n"
                    "        }\n"
                    "        .header { position: relative; z-index: 2; }\n"
                    "        .tag {\n"
                    "            display: inline-block;\n"
                    "            background: " + badge_bg + ";\n"
                    "            color: " + badge_text_color + "; font-size: 36px; font-weight: 900;\n"
                    "            padding: 14px 36px; border-radius: 50px;\n"
                    "            box-shadow: 0 10px 25px rgba(0,0,0,0.4);\n"
                    "        }\n"
                    "        .card-container {\n"
                    "            position: relative; z-index: 2;\n"
                    "            background: " + card_bg + ";\n"
                    "            border: 2px solid " + border_color + ";\n"
                    "            border-radius: 40px; padding: 65px 50px;\n"
                    "            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.6);\n"
                    "            backdrop-filter: blur(14px);\n"
                    "        }\n"
                    "        .quote-text {\n"
                    "            color: #FFFFFF; font-size: 76px; font-weight: 900;\n"
                    "            line-height: 1.25; letter-spacing: -1px;\n"
                    "            text-shadow: 0 5px 20px rgba(0,0,0,0.9);\n"
                    "        }\n"
                    "        .glow-word {\n"
                    "            color: " + glow_color + ";\n"
                    "            text-shadow: 0 0 25px " + glow_color + ";\n"
                    "            display: inline-block; padding: 0 8px;\n"
                    "        }\n"
                    "        .fg-layer {\n"
                    "            position: absolute; top:0; left:0; width:100%; height:100%;\n"
                    "            background: url('temp_fg.png') center/cover no-repeat;\n"
                    "            z-index: 3;\n"
                    "            pointer-events: none;\n"
                    "        }\n"
                    "        .footer {\n"
                    "            position: relative; z-index: 4;\n"
                    "            display: flex; justify-content: flex-end; align-items: center;\n"
                    "            border-top: 1px solid rgba(255, 255, 255, 0.2); padding-top: 35px;\n"
                    "        }\n"
                    "        .badge {\n"
                    "            background: rgba(0,0,0,0.65); padding: 10px 28px;\n"
                    "            border-radius: 14px; color: " + glow_color + "; font-size: 32px; font-weight: 900;\n"
                    "            border: 1px solid rgba(255,255,255,0.2);\n"
                    "        }\n"
                    "    </style>\n"
                    "</head>\n"
                    "<body>\n"
                    '    <div class="overlay"></div>\n'
                    '    <div class="header"><div class="tag">How can we</div></div>\n'
                    '    <div class="card-container"><div class="quote-text">“' + str(formatted_quote) + '”</div></div>\n'
                    + fg_layer_html + "\n"
                    '    <div class="footer"><span class="badge">NICE</span></div>\n'
                    "</body>\n"
                    "</html>"
                )

                with open("render_template.html", "w", encoding="utf-8") as f:
                    f.write(html_template)

                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(viewport={"width": 1080, "height": 1440})
                    page.goto(f"file://{os.path.abspath('render_template.html')}", wait_until="networkidle")
                    page.screenshot(path="final_cover.png")
                    browser.close()

            st.success(f"🎯 [{template_style}] 风格封面导出成功！")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💡 诊断与原帧")
                st.info(f"**提炼金句**：{quote}\n\n**高亮发光词**：`{highlight_word}`")
                st.image("temp_frame.jpg", caption=f"视频第 {target_time:.1f} 秒截图", use_container_width=True)
            with col2:
                st.subheader("✨ 商业爆款封面")
                st.image("final_cover.png", use_container_width=True)
                with open("final_cover.png", "rb") as f:
                    st.download_button("📥 下载 4K 华丽封面", f, file_name="commercial_cover.png", mime="image/png")

        except Exception as e:
            st.error(f"处理失败: {str(e)}")
elif not api_key:
    st.info("💡 请在左侧侧边栏输入你的 Groq API Key 以启动系统。")
