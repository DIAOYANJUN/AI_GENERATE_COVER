import streamlit as st
import os
import json
import subprocess
import cv2
from moviepy import VideoFileClip
from openai import OpenAI

# ---------------- 1. 云端环境自愈（自动补全 Playwright Chromium 内核） ----------------
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
st.set_page_config(page_title="AI 金句爆款封面生成器", layout="wide", page_icon="🎬")

st.title("🔥 AI 视频金句时间戳同步 & 华丽特效封面生成器")

# 侧边栏 API 配置
st.sidebar.header("🔑 API 配置")
api_key = st.sidebar.text_input("Groq API Key", type="password", help="请在此处输入你的 Groq API Key")
base_url = st.sidebar.text_input("API Base URL", value="https://api.groq.com/openai/v1")

# 动态获取 Groq 账号可用的生成式对话模型（自动过滤需协议授权的第三方/分类/语音模型）
available_models = []
if api_key:
    try:
        temp_client = OpenAI(api_key=api_key, base_url=base_url)
        models_res = temp_client.models.list()
        
        # 扩展黑名单：过滤非对话类、需特殊协议及安全分类模型
        banned_keywords = ["whisper", "safetensors", "guard", "embedding", "moderation", "canopylabs", "orpheus", "tts"]
        
        available_models = [
            m.id for m in models_res.data 
            if not any(k in m.id.lower() for k in banned_keywords)
        ]
        # 优先将官方推荐的 llama 模型排在前面
        available_models.sort(key=lambda x: 0 if "llama" in x.lower() else 1)
    except Exception:
        pass

if not available_models:
    available_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.2-3b-preview",
        "gemma2-9b-it"
    ]

selected_model = st.sidebar.selectbox("选择 Groq AI 对话模型", available_models, index=0)
custom_model = st.sidebar.text_input("或手动填写模型 ID（留空使用上方选择）", value="")
final_model = custom_model.strip() if custom_model.strip() else selected_model

uploaded_file = st.file_uploader("上传短视频文件 (MP4 / MOV)", type=["mp4", "mov"])

# ---------------- 3. 主流程处理逻辑 ----------------
if uploaded_file is not None and api_key:
    client = OpenAI(api_key=api_key, base_url=base_url)

    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.read())

    st.video("temp_video.mp4")

    if st.button("🚀 开始分析并一键生成爆款封面"):
        try:
            with st.spinner("1/4 正在剥离音频并预处理..."):
                video = VideoFileClip("temp_video.mp4")
                duration = video.duration
                video.audio.write_audiofile("temp_audio.mp3", logger=None)

            with st.spinner("2/4 正在使用 Groq Whisper 提取真实视频语音与时间戳..."):
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
                    if isinstance(seg, dict):
                        real_segments.append({"start": round(seg.get("start", 0), 2), "end": round(seg.get("end", 0), 2), "text": seg.get("text", "").strip()})
                    else:
                        real_segments.append({"start": round(getattr(seg, "start", 0), 2), "end": round(getattr(seg, "end", 0), 2), "text": getattr(seg, "text", "").strip()})

                if not real_segments:
                    real_segments = [{"start": 0.5, "end": min(5.0, duration), "text": "未能成功提取出文本内容"}]

            with st.spinner(f"3/4 大模型 ({final_model}) 提炼真实金句并匹配精准画面时间戳..."):
                prompt = (
                    "你是一个社媒爆款标题专家。请分析以下真实视频提取的带时间戳字幕，挑选出最震撼、最能拉满点击率的 1 句金句。\n"
                    + f"真实字幕数据：{json.dumps(real_segments, ensure_ascii=False)}\n\n"
                    + "请严格只返回以下 JSON 格式：\n"
                    + "{\n"
                    + '    "golden_quote": "最刺激痛点或引发共鸣的金句（必须出自字幕原文，12-18字以内）",\n'
                    + '    "start_time": 对应这句话在视频中的开始时间秒数(float),\n'
                    + '    "highlight_word": "金句中最核心需要高亮/发光的词语（2-4字）"\n'
                    + "}"
                )

                response = client.chat.completions.create(
                    model=final_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs raw JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                res = json.loads(response.choices[0].message.content)
                quote = res.get("golden_quote", real_segments[0]["text"])
                target_time = float(res.get("start_time", real_segments[0]["start"]))
                highlight_word = res.get("highlight_word", quote[:2] if len(quote)>=2 else quote)

                target_time = min(max(0.5, target_time), duration - 0.5)

                video.save_frame("temp_frame.jpg", t=target_time)
                video.close()

            with st.spinner("4/4 正在加载 HTML 特效模板并导出 4K 封面..."):
                formatted_quote = quote.replace(
                    highlight_word, 
                    f'<span class="glow-word">{highlight_word}</span>'
                )

                html_template = (
                    "<!DOCTYPE html>\n"
                    "<html>\n"
                    "<head>\n"
                    "    <style>\n"
                    "        * { box-sizing: border-box; margin: 0; padding: 0; }\n"
                    "        body {\n"
                    "            width: 1080px; height: 1440px;\n"
                    "            background: url('temp_frame.jpg') center/cover no-repeat;\n"
                    "            font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;\n"
                    "            display: flex; flex-direction: column; justify-content: space-between;\n"
                    "            padding: 100px 70px;\n"
                    "            position: relative; overflow: hidden;\n"
                    "        }\n"
                    "        .overlay {\n"
                    "            position: absolute; top:0; left:0; width:100%; height:100%;\n"
                    "            background: linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.75) 100%);\n"
                    "            backdrop-filter: blur(12px) brightness(0.85);\n"
                    "            z-index: 1;\n"
                    "        }\n"
                    "        .header { position: relative; z-index: 2; }\n"
                    "        .tag {\n"
                    "            display: inline-block;\n"
                    "            background: linear-gradient(90deg, #FFE600 0%, #FF9900 100%);\n"
                    "            color: #000; font-size: 38px; font-weight: 900;\n"
                    "            padding: 14px 36px; border-radius: 50px;\n"
                    "            box-shadow: 0 10px 30px rgba(255, 230, 0, 0.4);\n"
                    "        }\n"
                    "        .card-container {\n"
                    "            position: relative; z-index: 2;\n"
                    "            background: rgba(255, 255, 255, 0.07);\n"
                    "            border: 2px solid rgba(255, 255, 255, 0.18);\n"
                    "            border-radius: 40px; padding: 70px 50px;\n"
                    "            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5);\n"
                    "        }\n"
                    "        .quote-text {\n"
                    "            color: #FFFFFF; font-size: 76px; font-weight: 900;\n"
                    "            line-height: 1.3; letter-spacing: 3px;\n"
                    "            text-shadow: 0 5px 15px rgba(0,0,0,0.8);\n"
                    "        }\n"
                    "        .glow-word {\n"
                    "            color: #FFE600;\n"
                    "            text-shadow: 0 0 20px rgba(255, 230, 0, 0.8),\n"
                    "                         0 0 40px rgba(255, 230, 0, 0.5);\n"
                    "            display: inline-block; padding: 0 10px;\n"
                    "        }\n"
                    "        .footer {\n"
                    "            position: relative; z-index: 2;\n"
                    "            display: flex; justify-content: flex-end; align-items: center;\n"
                    "            color: rgba(255, 255, 255, 0.7); font-size: 28px; font-weight: 600;\n"
                    "            border-top: 1px solid rgba(255, 255, 255, 0.2); padding-top: 40px;\n"
                    "        }\n"
                    "        .timestamp-badge {\n"
                    "            background: rgba(0,0,0,0.5); padding: 8px 24px;\n"
                    "            border-radius: 12px; color: #FFE600; font-family: sans-serif;\n"
                    "            font-size: 32px; font-weight: bold;\n"
                    "        }\n"
                    "    </style>\n"
                    "</head>\n"
                    "<body>\n"
                    '    <div class="overlay"></div>\n'
                    '    <div class="header"><div class="tag">How can we</div></div>\n'
                    '    <div class="card-container"><div class="quote-text">“' + str(formatted_quote) + '”</div></div>\n'
                    '    <div class="footer">\n'
                    '        <span class="timestamp-badge">NICE</span>\n'
                    '    </div>\n'
                    "</body>\n"
                    "</html>"
                )

                with open("render_template.html", "w", encoding="utf-8") as f:
                    f.write(html_template)

                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(viewport={"width": 1080, "height": 1440})
                    page.goto(f"file://{os.path.abspath('render_template.html')}")
                    page.screenshot(path="final_cover.png")
                    browser.close()

            st.success(f"🎯 渲染完成！已自动匹配视频第 {target_time:.1f} 秒的金句画面！")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💡 诊断与原帧")
                st.info(f"**提炼金句**：{quote}\n\n**高亮发光词**：`{highlight_word}`")
                st.image("temp_frame.jpg", caption=f"视频第 {target_time:.1f} 秒截图", use_container_width=True)
            with col2:
                st.subheader("✨ 华丽爆款封面")
                st.image("final_cover.png", use_container_width=True)
                with open("final_cover.png", "rb") as f:
                    st.download_button("📥 下载 4K 华丽封面", f, file_name="luxury_cover.png", mime="image/png")

        except Exception as e:
            st.error(f"处理失败: {str(e)}")
elif not api_key:
    st.info("💡 请在左侧侧边栏输入你的 Groq API Key 以启动系统。")
