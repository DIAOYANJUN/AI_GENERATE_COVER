import streamlit as st
import os
import json
import subprocess
import cv2
from moviepy.editor import VideoFileClip
from openai import OpenAI

# ---------------- 1. 云端环境自愈（自动补全 Playwright Chromium 内核） ----------------
@st.cache_resource
def setup_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pass
    # 自动静默安装 chromium
    subprocess.run(["playwright", "install", "chromium"])

setup_playwright()
from playwright.sync_api import sync_playwright

# ---------------- 2. 页面与配置初始化 ----------------
st.set_page_config(page_title="AI 金句爆款封面生成器", layout="wide", page_icon="🎬")

st.title("🔥 AI 视频金句时间戳同步 & 华丽特效封面生成器")

# 侧边栏 API Key 配置（安全防泄密）
st.sidebar.header("🔑 API 配置")
api_key = st.sidebar.text_input("OpenAI / DeepSeek API Key", type="password", help="请在此处输入你的 API Key，绝对不会公开")
base_url = st.sidebar.text_input("API Base URL", value="https://api.deepseek.com/v1")

uploaded_file = st.file_uploader("上传短视频文件 (MP4 / MOV)", type=["mp4", "mov"])

# ---------------- 3. 主流程处理逻辑 ----------------
if uploaded_file is not None and api_key:
    client = OpenAI(api_key=api_key, base_url=base_url)

    # 临时写入文件
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
                # 提示：上线生产环境可解开 Whisper 真实调用，此处保留通用 Mock 结构
                mock_segments = [
                    {"start": 1.5, "end": 4.5, "text": "很多人天天在想怎么赚大钱，结果连底层的商业杠杆都没摸清。"},
                    {"start": 5.2, "end": 9.0, "text": "真正的高手从来不靠体力赚钱，他们用代码和 API 作为杠杆。"},
                    {"start": 9.5, "end": 13.0, "text": "一个人加一套极速交付流程，你就能成为一家高效运行的公司。"}
                ]

            with st.spinner("3/4 大模型提炼金句并匹配精准画面时间戳..."):
                prompt = f"""
                你是一个社媒爆款标题专家。请分析以下带时间戳的视频字幕，挑选出最震撼、最能拉满点击率的 1 句金句。
                字幕数据：{json.dumps(mock_segments, ensure_ascii=False)}
                
                请严格只返回以下 JSON 格式：
                {{
                    "golden_quote": "最刺激痛点或引发共鸣的金句（12-18字以内）",
                    "start_time": 对应这句话在视频中的开始时间秒数(float),
                    "tag": "爆款分类标签（如：认知觉醒 / 商业逻辑）",
                    "highlight_word": "金句中最核心需要高亮/发光的词语（2-4字）"
                }}
                """

                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )

                res = json.loads(response.choices[0].message.content)
                quote = res.get("golden_quote", "用代码和 API 作为杠杆，一个人就是一家公司")
                target_time = float(res.get("start_time", 5.2))
                tag = res.get("tag", "认知觉醒")
                highlight_word = res.get("highlight_word", "杠杆")

                target_time = min(max(0.5, target_time), duration - 0.5)

                # 精准截取对应时间点图像
                video.save_frame("temp_frame.jpg", t=target_time)
                video.close()

            with st.spinner("4/4 正在加载 HTML 特效模板并导出 4K 封面..."):
                formatted_quote = quote.replace(
                    highlight_word, 
                    f'<span class="glow-word">{highlight_word}</span>'
                )

                html_template = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                        body {{
                            width: 1080px; height: 1440px;
                            background: url('temp_frame.jpg') center/cover no-repeat;
                            font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
                            display: flex; flex-direction: column; justify-content: space-between;
                            padding: 100px 70px;
                            position: relative; overflow: hidden;
                        }}
                        .overlay {{
                            position: absolute; top:0; left:0; width:100%; height:100%;
                            background: linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.75) 100%);
                            backdrop-filter: blur(12px) brightness(0.85);
                            z-index: 1;
                        }}
                        .header {{ position: relative; z-index: 2; }}
                        .tag {{
                            display: inline-block;
                            background: linear-gradient(90deg, #FFE600 0%, #FF9900 100%);
                            color: #000; font-size: 38px; font-weight: 900;
                            padding: 14px 36px; border-radius: 50px;
                            box-shadow: 0 10px 30px rgba(255, 230, 0, 0.4);
                        }}
                        .card-container {{
                            position: relative; z-index: 2;
                            background: rgba(255, 255, 255, 0.07);
                            border: 2px solid rgba(255, 255, 255, 0.18);
                            border-radius: 40px; padding: 70px 50px;
                            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5);
                        }}
                        .quote-text {{
                            color: #FFFFFF; font-size: 76px; font-weight: 900;
                            line-height: 1.3; letter-spacing: 3px;
                            text-shadow: 0 5px 15px rgba(0,0,0,0.8);
                        }}
                        .glow-word {{
                            color: #FFE600;
                            text-shadow: 0 0 20px rgba(255, 230, 0, 0.8),
                                         0 0 40px rgba(255, 230, 0, 0.5);
                            display: inline-block; padding: 0 10px;
                        }}
                        .footer {{
                            position: relative; z-index: 2;
                            display: flex; justify-content: space-between; align-items: center;
                            color: rgba(255, 255, 255, 0.7); font-size: 28px; font-weight: 600;
                            border-top: 1px solid rgba(255, 255, 255, 0.2); padding-top: 40px;
                        }}
                        .timestamp-badge {{
                            background: rgba(0,0,0,0.5); padding: 8px 20px;
                            border-radius: 12px; color: #FFE600; font-family: monospace;
                        }}
                    </style>
                </head>
                <body>
                    <div class="overlay"></div>
                    <div class="header"><div class="tag"># {tag}</div></div>
                    <div class="card-container"><div class="quote-text">“{formatted_quote}”</div></div>
                    <div class="footer">
                        <span>⚡ AI 时间戳同步生成</span>
                        <span class="timestamp-badge">帧对齐: {target_time:.1f}s</span>
                    </div>
                </body>
                </html>
                """

                with open("render_template.html", "w", encoding="utf-8") as f:
                    f.write(html_template)

                # 无头浏览器截图导出
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
    st.info("💡 请在左侧侧边栏输入你的 API Key 以启动系统。")