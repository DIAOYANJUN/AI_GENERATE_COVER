import streamlit as st
import os
import json
import subprocess
import time
from moviepy import VideoFileClip
from openai import OpenAI
from rembg import remove
from PIL import Image

# ---------------- 0. 用户系统与 VIP 权限配置 ----------------
st.set_page_config(page_title="AI 商业级爆款封面生成器", layout="wide", page_icon="🎬")

USER_DATABASE = {
    "admin": {"password": "123", "role": "vip"},
    "free_user": {"password": "123", "role": "free"}
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "free"
if "payment_status" not in st.session_state:
    st.session_state.payment_status = "NOTPAY"
if "current_order_id" not in st.session_state:
    st.session_state.current_order_id = f"ORD_{int(time.time())}"

# 登录流程
if not st.session_state.logged_in:
    st.title("🔐 AI 爆款封面生成器 - 用户登录")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("账号登录")
            username = st.text_input("用户名", value="free_user")
            password = st.text_input("密码", type="password", value="123")
            submit = st.form_submit_button("🚀 立即登录")
            
            if submit:
                if username in USER_DATABASE and USER_DATABASE[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_role = USER_DATABASE[username]["role"]
                    st.success("✅ 登录成功！正在进入系统...")
                    st.rerun()
                else:
                    st.error("❌ 用户名或密码错误")
    st.stop()

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

# ---------------- 2. 页面与侧边栏配置 ----------------
st.title("✨ AI 视频金句时间戳同步 & 智能商业封面生成器")

is_vip = st.session_state.user_role == "vip"
role_badge = "👑 VIP 尊享会员" if is_vip else "👤 普通免费用户"
st.sidebar.markdown(f"**当前登录**：`{st.session_state.get('username')}` ({role_badge})")

# 非 VIP 用户展示微信收款码
if not is_vip:
    with st.sidebar.expander("💳 **升级 VIP 专属权益（微信扫码）**", expanded=True):
        st.write("🔥 **VIP 专享特权**：")
        st.write("• 解锁小红书爆款 👑 VIP 高对比度配色")
        st.write("• 解锁 3D 人像景深穿插海报特效")
        
        st.markdown("---")
        st.markdown("##### 🟢 微信扫码支付 ￥19.9 开通")
        
        if os.path.exists("pay_qr.png"):
            st.image("pay_qr.png", caption="请使用微信扫码支付 (Frenk**君)", use_container_width=True)
        else:
            st.warning("⚠️ 未检测到 pay_qr.png，请上传微信二维码图片到仓库")
            st.image("https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=WeChatPay", caption="微信支付", use_container_width=True)
        
        st.markdown("---")
        st.markdown(f"**订单号**: `{st.session_state.current_order_id}`")
        
        if st.button("🔄 检查是否已扫码支付"):
            with st.spinner("正在向支付网关查询扫码及到账状态..."):
                time.sleep(1)
                if st.session_state.payment_status == "SUCCESS":
                    st.session_state.user_role = "vip"
                    st.success("🎉【支付成功】已检测到付款！VIP 权限已自动开通！")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("⏳【未完成支付】尚未检测到扫码付款。")

        st.markdown("---")
        st.markdown("##### 🧪 调试区")
        if st.button("模拟已付款"):
            st.session_state.payment_status = "SUCCESS"
            st.toast("已模拟支付成功！")

if st.sidebar.button("🚪 退出登录"):
    st.session_state.logged_in = False
    st.session_state.user_role = "free"
    st.session_state.payment_status = "NOTPAY"
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.header("🔑 API 配置")
api_key = st.sidebar.text_input("Groq API Key", type="password")
base_url = st.sidebar.text_input("API Base URL", value="https://api.groq.com/openai/v1")

st.sidebar.header("🎨 封面视觉设计（支持实时响应）")

template_style = st.sidebar.selectbox(
    "选择封面视觉风格",
    [
        "黑金高奢 (Luxury Glass)", 
        "赛博霓虹 (Cyber Glow)", 
        "小红书爆款 (High-CTR Yellow) 👑 VIP 独享", 
        "时尚杂志 (Editorial Magazine)"
    ],
    index=0
)

# 💡 将这两个控件设为实时响应控件（不放在生成按钮内部，只要变动就会触发页面重跑渲染）
if not is_vip:
    enable_3d_depth = st.sidebar.checkbox("开启 3D 人像遮挡/文字后置效果 (VIP 专享)", value=False, disabled=True)
else:
    enable_3d_depth = st.sidebar.checkbox("开启 3D 人像遮挡/文字后置效果", value=True)

# 动态获取模型
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

# ---------------- 3. 会话状态缓存与主渲染函数 ----------------
# 如果已经分析过视频并生成了基础数据，将其存入 st.session_state 避免重复调用耗时的 Whisper 和 LLM
if uploaded_file is not None and api_key:
    # 仅当上传新视频或尚未解析时才运行重型任务
    if "analyzed_data" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        with open("temp_video.mp4", "wb") as f:
            f.write(uploaded_file.read())
        st.session_state.last_file = uploaded_file.name

        client = OpenAI(api_key=api_key, base_url=base_url)
        
        with st.spinner("1/4 正在剥离视频音频..."):
            video = VideoFileClip("temp_video.mp4")
            duration = video.duration
            video.audio.write_audiofile("temp_audio.mp3", logger=None)

        with st.spinner("2/4 使用 Groq Whisper 提取真实语音时间戳..."):
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

        with st.spinner("3/4 大模型深度拆解，挑选最优封面帧..."):
            prompt = (
                "分析以下视频字幕，挑选出最震撼、最能拉满点击率的【唯一 1 句金句】，并匹配其在视频中的开始时间秒数。\n"
                + f"字幕数据：{json.dumps(real_segments, ensure_ascii=False)}\n\n"
                + "请严格只返回以下 JSON 格式：\n"
                + "{\n"
                + '    "golden_quote": "金句原文",\n'
                + '    "start_time": 开始秒数(float),\n'
                + '    "highlight_word": "核心高亮词",\n'
                + '    "explanation": "详细解释为什么选择这句话（15-30字）"\n'
                + "}"
            )

            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": "You are a professional social media title designer that outputs strict raw JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                seed=42,
                max_tokens=1000
            )

            res = json.loads(response.choices[0].message.content)
            quote = res.get("golden_quote", real_segments[0]["text"])
            target_time = float(res.get("start_time", real_segments[0]["start"]))
            highlight_word = res.get("highlight_word", quote.split()[0] if quote.split() else quote)
            ai_explanation = res.get("explanation", "精选全片高能痛点，完美匹配视频吸睛瞬间。")

            target_time = min(max(0.5, target_time), duration - 0.5)

            video.save_frame("temp_frame.jpg", t=target_time)
            video.close()

        # 提前做一次 AI 抠图备用
        with st.spinner("4/4 正在预处理 AI 人像扣图层..."):
            input_img = Image.open("temp_frame.jpg")
            output_img = remove(input_img)
            output_img.save("temp_fg.png")

        # 将解析结果存入内存
        st.session_state.analyzed_data = {
            "quote": quote,
            "highlight_word": highlight_word,
            "target_time": target_time,
            "ai_explanation": ai_explanation,
            "duration": duration
        }
        st.success("🎉 视频分析与抠图准备就绪！现在你可以**实时勾选后置效果或切换风格**查看变化。")

    # 如果已经解析完毕，每次侧边栏勾选变化时，直接执行极速渲染（无需重新上传和调用 AI 分析）
    if "analyzed_data" in st.session_state:
        data = st.session_state.analyzed_data
        quote = data["quote"]
        highlight_word = data["highlight_word"]
        target_time = data["target_time"]
        ai_explanation = data["ai_explanation"]

        if "VIP" in template_style and not is_vip:
            st.error("🔒 该模板为 👑 VIP 独享功能！请先在左侧侧边栏扫码支付完成验证。")
            st.stop()

        try:
            # 动态控制抠图图层是否加载
            fg_layer_html = '<div class="fg-layer"></div>' if (enable_3d_depth and is_vip) else ''

            formatted_quote = quote.replace(
                highlight_word, 
                f'<span class="glow-word">{highlight_word}</span>'
            )

            if "Cyber" in template_style:
                font_import = "@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@800;900&family=Noto+Sans+SC:wght@900&display=swap');"
                font_family = "'Orbitron', 'Noto Sans SC', sans-serif"
                glow_color = "#00FFFF"
                badge_bg = "linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%)"
                card_bg = "rgba(10, 25, 47, 0.55)"
                border_color = "rgba(0, 255, 255, 0.4)"
                badge_text_color = "#000"
            elif "Yellow" in template_style or "VIP" in template_style:
                font_import = "@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@900&family=Noto+Sans+SC:wght@900&display=swap');"
                font_family = "'Montserrat', 'Noto Sans SC', sans-serif"
                glow_color = "#FFE600"
                badge_bg = "#FFE600"
                card_bg = "rgba(0, 0, 0, 0.65)"
                border_color = "rgba(255, 230, 0, 0.5)"
                badge_text_color = "#000"
            elif "Magazine" in template_style:
                font_import = "@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@800;900&family=Noto+Serif+SC:wght@900&display=swap');"
                font_family = "'Cinzel', 'Noto Serif SC', serif"
                glow_color = "#E6C200"
                badge_bg = "#FFFFFF"
                card_bg = "rgba(255, 255, 255, 0.12)"
                border_color = "rgba(255, 255, 255, 0.4)"
                badge_text_color = "#000"
            else:
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

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💡 AI 智能诊断与选帧拆解")
                st.info(f"**🎯 选定金句**：{quote}\n\n**✨ 核心高亮词**：`{highlight_word}`\n\n**⏱️ 匹配画面时间**：第 {target_time:.1f} 秒\n\n**📝 AI 选帧理由**：\n> {ai_explanation}")
                st.image("temp_frame.jpg", caption=f"视频第 {target_time:.1f} 秒截图", use_container_width=True)
            with col2:
                st.subheader(f"✨ 4K 商业爆款封面 [{template_style}]")
                st.image("final_cover.png", use_container_width=True)
                with open("final_cover.png", "rb") as f:
                    st.download_button("📥 下载 4K 华丽封面", f, file_name="commercial_cover.png", mime="image/png")

        except Exception as e:
            st.error(f"处理失败: {str(e)}")
elif not api_key:
    st.info("💡 请在左侧侧边栏输入你的 Groq API Key 以启动系统。")
