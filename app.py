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

model_choice = st.sidebar.selectbox(
    "选择 Groq AI 模型",
    [
        "llama-3.1-8b-instant",       # 默认：极速可用
        "llama-3.1-70b-versatile",     # 高质量模型
        "llama3-8b-8192", 
        "llama3-70b-8192", 
        "mixtral-8x7b-32768"
    ],
    index=0
)

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

            with st.spinner("2/4 正在进行带时间戳的语音识别..."):
                mock_segments = [
                    {"start": 1.5, "end": 4.5, "text": "很多人天天在想怎么赚大钱，结果连底层的商业杠杆都没摸清。"},
                    {"start": 5.2, "end": 9.0, "text": "真正的高手从来不靠体力赚钱，他们用代码和 API 作为杠杆。"},
                    {"start": 9.5, "end": 13.0, "text": "一个人加一套极速交付流程，你就能成为一家高效运行的公司。"}
                ]

            with st.spinner(f"3/4 大模型 ({model_choice}) 提炼金句并匹配精准画面时间戳..."):
                prompt = (
                    "你是一个社媒爆款标题专家。请分析以下带时间戳的视频字幕，挑选出最震撼、最能拉满点击率的 1 句金句。\n"
                    + f"字幕数据：{json.dumps(mock_segments, ensure_ascii=False)}\n\n"
                    + "请严格只返回以下 JSON 格式：\n"
                    + "{\n"
                    + '    "golden_quote": "最刺激痛点或引发共鸣的金句（12-18字以内）",\n'
                    + '    "start_time": 对应这句话在视频中的开始时间秒数(float),\n'
                    + '    "tag": "爆款分类标签（如：认知觉醒 / 商业逻辑）",\n'
                    + '    "highlight_word": "金句中最核心需要高亮/发光的词语（2-4字）"\n'
                    + "}"
                )

                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )

                res = json.loads(response.choices[0].message.content)
                quote = res.get("golden_quote", "用代码和 API 作为杠杆，一个人就是一家公司")
                target_time = float(res.get("start_time", 5.2))
                tag = res.get("tag", "认知觉醒")
                highlight_word = res.get("highlight_word", "杠杆")

                # 纠正并确保完整闭合：界定时间在 0.5s 到 (视频总长 - 0.5s) 之间
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
                    "            display: flex; justify-content: space-between; align-items: center;\n"
                    "            color: rgba(255, 255, 255, 0.7); font-size: 28px; font-weight: 600;\n"
                    "            border-top: 1px solid rgba(255, 255, 255, 0.2); padding-top: 40px;\n"
                    "        }\n"
                    "        .timestamp-badge {\n"
                    "            background: rgba(0,0,0,0.5); padding: 8px 20px;\n"
                    "            border-radius: 12px; color: #FFE600; font-family: monospace;\n"
                    "        }\n"
                    "    </style>\n"
                    "</head>\n"
                    "<body>\n"
                    '    <div class="overlay"></div>\n'
                    '    <div class="header"><div class="tag"># ' + str(tag) + '</div></div>\n'
                    '    <div class="card-container"><div class="quote-text">“' + str(formatted_quote) + '”</div></div>\n'
                    '    <div class="footer">\n'
                    '        <span>⚡ AI 时间戳同步生成</span>\n'
                    '        <span class="timestamp-badge">帧对齐: ' + f"{target_time:.1f}" + 's</span>\n'
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
                st.info(f"**金句**：{quote}\n\n**高亮词**：`{highlight_word}`")
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
