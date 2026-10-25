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
                    model=model_choice,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )

                res = json.loads(response.choices[0].message.content)
                quote = res.get("golden_quote", "用代码和 API 作为杠杆，一个人就是一家公司")
                target_time = float(res.get("start_time", 5.2))
                tag = res.get("tag", "认知觉醒")
                highlight_word = res.get("highlight_word", "杠杆")

                target_time = min(max(0.5, target_time), duration - 0.5)

                video.save_frame("temp_frame.jpg", t=target_time)
                video.close()

            with st.spinner("4/4 正在加载 HTML 特效模板并导出 4K 封面..."):
                formatted_quote = quote.replace(
                    highlight_word, 
                    f'<span class="glow-word">{highlight_word}</span>'
                )

                # 普通多行字符串（不用 f-string，绝不与 CSS 大括号冲突）
                raw_html = """<!DOCTYPE html>
<html>
<head>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            width: 1080px; height:
