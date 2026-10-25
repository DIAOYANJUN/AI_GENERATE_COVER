import streamlit as st
import os
import json
import subprocess
import time
import random
from moviepy import VideoFileClip
from openai import OpenAI
from rembg import remove
from PIL import Image, ImageEnhance, ImageFilter

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

@st.cache_resource
def setup_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pass
    subprocess.run(["playwright", "install", "chromium"])

setup_playwright()
from playwright.sync_api import sync_playwright

st.title("✨ AI 视频金句时间戳同步 & 智能商业封面生成器 (Pro版)")

is_vip = st.session_state.user_role == "vip"
role_badge = "👑 VIP 尊享会员" if is_vip else "👤 普通免费用户"
st.sidebar.markdown(f"**当前登录**：`{st.session_state.get('username')}` ({role_badge})")

if not is_vip:
    with st.sidebar.expander("💳 **升级 VIP 专属权益（微信扫码）**", expanded=True):
        st.write("🔥 **VIP 专享特权**：")
        st.write("• 解锁 **Sweetie Fox 专属真人图库渲染**")
        st.markdown("---")
        st.markdown("##### 🟢 微信扫码支付 ￥19.9 开通")
        if os.path.exists("pay_qr.png"):
            st.image("pay_qr.png", caption="请使用微信扫码支付", use_container_width=True)
        else:
            st.image("https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=WeChatPay", caption="微信支付", use_container_width=True)
        
        if st.button("🔄 检查是否已扫码支付"):
            if st.session_state.payment_status == "SUCCESS":
                st.session_state.user_role = "vip"
                st.success("🎉 VIP 权限已自动开通！")
                st.rerun()
            else:
                st.warning("⏳ 尚未检测到付款。")
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

st.sidebar.header("🎨 模板库与视觉设计")

template_style = st.sidebar.selectbox(
    "基础视觉色彩风格",
    ["黑金高奢 (Luxury)", "赛博霓虹 (Cyber)", "小红书爆款 (High-CTR Yellow)", "时尚杂志 (Editorial)"],
    index=0
)

st.sidebar.markdown("---")
if st.sidebar.button("🎲【随机切换版式 & 切换 Sweetie Fox 造型】", use_container_width=True):
    st.session_state.layout_index = random.randint(0, 2)
    st.session_state.bubble_seed = random.randint(1000, 99999)
    st.session_state.beauty_seed = random.randint(1, 100)
    st.toast("✨ 已随机切换版式并更换 Sweetie Fox 造型！")

if "layout_index" not in st.session_state:
    st.session_state.layout_index = 0
if "bubble_seed" not in st.session_state:
    st.session_state.bubble_seed = 42
if "beauty_seed" not in st.session_state:
    st.session_state.beauty_seed = 1

if not is_vip:
    ai_upscale = st.sidebar.checkbox("🚀 开启 4K Retina 超高清修复 (VIP专享)", value=False, disabled=True)
    ai_retouch = st.sidebar.checkbox("✨ 电影级极限锐化与色彩调优 (VIP专享)", value=False, disabled=True)
    enable_3d_depth = st.sidebar.checkbox("开启 3D 人像遮挡效果 (VIP专享)", value=False, disabled=True)
    enable_partner = st.sidebar.checkbox("🦊 开启 Sweetie Fox 真人陪伴 (VIP专享)", value=False, disabled=True)
    enable_bubbles = st.sidebar.checkbox("🎈 开启智能气泡图案叠加 (VIP专享)", value=False, disabled=True)
else:
    ai_upscale = st.sidebar.checkbox("🚀 开启 4K Retina 超高清修复", value=True)
    ai_retouch = st.sidebar.checkbox("✨ 电影级极限锐化与色彩调优", value=True)
    enable_3d_depth = st.sidebar.checkbox("开启 3D 人像遮挡效果", value=True)
    enable_partner = st.sidebar.checkbox("🦊 开启 Sweetie Fox 真人陪伴", value=True) # 默认开启
    enable_bubbles = st.sidebar.checkbox("🎈 开启智能气泡图案叠加", value=True)

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

selected_model = st.sidebar.selectbox("Select Groq Model", available_models, index=0)
uploaded_file = st.file_uploader("上传短视频文件 (MP4 / MOV)", type=["mp4", "mov"])

# ---------------- 3. 核心处理与高清渲染 ----------------
if uploaded_file is not None and api_key:
    if "analyzed_data" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        with open("temp_video.mp4", "wb") as f:
            f.write(uploaded_file.read())
        st.session_state.last_file = uploaded_file.name

        client = OpenAI(api_key=api_key, base_url=base_url)
        
        with st.spinner("1/4 正在剥离视频音频..."):
            video = VideoFileClip("temp_video.mp4")
            duration = video.duration
            video.audio.write_audiofile("temp_audio.mp3", logger=None)

        with st.spinner("2/4 提取语音时间戳..."):
            with open("temp_audio.mp3", "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=("temp_audio.mp3", audio_file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            raw_segments = getattr(transcription, "segments", [])
            real_segments = [{"start": round(seg.get("start", 0), 2), "text": seg.get("text", "").strip()} for seg in raw_segments]
            if not real_segments:
                real_segments = [{"start": 0.5, "text": "Pro Quality Video Content"}]

        with st.spinner("3/4 大模型智能提炼金句..."):
            prompt = (
                "分析以下字幕，挑选出最震撼的【唯一金句】及开始秒数。\n"
                + f"字幕：{json.dumps(real_segments, ensure_ascii=False)}\n\n"
                + "严格只返回 JSON:\n"
                + '{"golden_quote": "金句", "start_time": 秒数(float), "highlight_word": "高亮词", "explanation": "理由"}'
            )

            response = client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "system", "content": "You output strict raw JSON."}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                seed=42,
                max_tokens=1000
            )

            res = json.loads(response.choices[0].message.content)
            quote = res.get("golden_quote", real_segments[0]["text"])
            target_time = float(res.get("start_time", real_segments[0]["start"]))
            highlight_word = res.get("highlight_word", quote.split()[0])
            ai_explanation = res.get("explanation", "高能吸睛瞬间。")
            target_time = min(max(0.5, target_time), duration - 0.5)

            video.save_frame("temp_frame_raw.jpg", t=target_time)
            video.close()

        with st.spinner("4/4 AI 极智高清修复与预处理..."):
            base_img = Image.open("temp_frame_raw.jpg")
            if ai_retouch and is_vip:
                base_img = ImageEnhance.Color(base_img).enhance(1.3)
                base_img = ImageEnhance.Contrast(base_img).enhance(1.2)
                base_img = base_img.filter(ImageFilter.SHARPEN)
            if ai_upscale and is_vip:
                w, h = base_img.size
                base_img = base_img.resize((w * 3, h * 3), Image.Resampling.LANCZOS)
            base_img.save("temp_frame.jpg")
            remove(base_img).save("temp_fg.png")

        st.session_state.analyzed_data = {
            "quote": quote,
            "highlight_word": highlight_word,
            "target_time": target_time,
            "ai_explanation": ai_explanation
        }
        st.success("🎉 高清分析就绪！")

    if "analyzed_data" in st.session_state:
        data = st.session_state.analyzed_data
        quote = data["quote"]
        highlight_word = data["highlight_word"]
        target_time = data["target_time"]
        ai_explanation = data["ai_explanation"]

        if "VIP" in template_style and not is_vip:
            st.error("🔒 该模板为 VIP 独享！请先扫码开通。")
            st.stop()

        try:
            formatted_quote = quote.replace(highlight_word, f'<span class="glow-word">{highlight_word}</span>')
            fg_layer_html = '<div class="fg-layer"></div>' if (enable_3d_depth and is_vip) else ''

            # 🦊 核心锁定：专属于 Sweetie Fox 的高颜值 Cosplay 经典真人造型图源库
            partner_html = ""
            if enable_partner and is_vip:
                sweetie_fox_urls = [
                    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=900&q=85", # 经典高定氛围
                    "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=900&q=85", # 动漫游戏风
                    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=85"  # 标志性惊艳神颜
                ]
                chosen_fox_url = sweetie_fox_urls[st.session_state.beauty_seed % len(sweetie_fox_urls)]
                partner_html = f"""
                <div style="
                    position: absolute; right: 10px; bottom: 0px; width: 500px; height: 980px;
                    background: url('{chosen_fox_url}') center/cover no-repeat;
                    z-index: 80; pointer-events: none;
                    mask-image: linear-gradient(to bottom, black 85%, transparent 100%);
                    -webkit-mask-image: linear-gradient(to bottom, black 85%, transparent 100%);
                "></div>
                """

            bubbles_html = ""
            if enable_bubbles and is_vip:
                random.seed(st.session_state.bubble_seed)
                bubble_count = random.randint(12, 20)
                for _ in range(bubble_count):
                    bx = random.choice([random.randint(40, 280), random.randint(780, 1020), random.randint(100, 950)])
                    by = random.choice([random.randint(80, 450), random.randint(950, 1380)])
                    bsize = random.randint(40, 110)
                    bopacity = round(random.uniform(0.35, 0.7), 2)
                    bcolor = random.choice(["rgba(255,255,255,", "rgba(0,255,255,", "rgba(255,230,0,", "rgba(255,100,200,"])
                    final_color = f"{bcolor}{bopacity})"
                    
                    bubbles_html += f"""
                    <div style="
                        position: absolute; left: {bx}px; top: {by}px; width: {bsize}px; height: {bsize}px;
                        background: radial-gradient(circle at 35% 35%, rgba(255,255,255,0.95), {final_color});
                        border-radius: 50%; box-shadow: 0 0 30px {final_color}; z-index: 10; pointer-events: none;
                    "></div>
                    """

            if "Cyber" in template_style:
                glow_color = "#00FFFF"
                badge_bg = "linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%)"
                card_bg = "rgba(10, 25, 47, 0.65)"
                border_color = "rgba(0, 255, 255, 0.4)"
            elif "Yellow" in template_style or "VIP" in template_style:
                glow_color = "#FFE600"
                badge_bg = "#FFE600"
                card_bg = "rgba(0, 0, 0, 0.75)"
                border_color = "rgba(255, 230, 0, 0.6)"
            elif "Magazine" in template_style:
                glow_color = "#E6C200"
                badge_bg = "#FFFFFF"
                card_bg = "rgba(255, 255, 255, 0.15)"
                border_color = "rgba(255, 255, 255, 0.5)"
            else:
                glow_color = "#FFE600"
                badge_bg = "linear-gradient(90deg, #FFE600 0%, #FF9900 100%)"
                card_bg = "rgba(18, 18, 18, 0.6)"
                border_color = "rgba(255, 255, 255, 0.3)"

            current_layout = st.session_state.layout_index

            if current_layout == 0:
                html_template = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                        body {{
                            width: 1080px; height: 1440px;
                            background: url('temp_frame.jpg') center/cover no-repeat;
                            font-family: 'Montserrat', sans-serif;
                            display: flex; flex-direction: column; justify-content: center; align-items: center;
                            padding: 80px; position: relative; overflow: hidden;
                        }}
                        .overlay {{ position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.55); backdrop-filter: blur(5px); z-index: 1; }}
                        {bubbles_html}
                        {partner_html}
                        .content-box {{ position: relative; z-index: 20; text-align: center; max-width: 900px; }}
                        .tag {{ display: inline-block; background: {badge_bg}; color: #000; font-size: 32px; font-weight: 900; padding: 12px 30px; border-radius: 12px; margin-bottom: 40px; }}
                        .quote-text {{ color: #FFFFFF; font-size: 82px; font-weight: 900; line-height: 1.2; text-shadow: 0 10px 30px rgba(0,0,0,0.9); }}
                        .glow-word {{ color: {glow_color}; text-shadow: 0 0 30px {glow_color}; }}
                        .fg-layer {{ position: absolute; top:0; left:0; width:100%; height:100%; background: url('temp_fg.png') center/cover no-repeat; z-index: 50; pointer-events: none; }}
                    </style>
                </head>
                <body>
                    <div class="overlay"></div>
                    {bubbles_html}
                    {partner_html}
                    <div class="content-box">
                        <div class="tag">🔥 SWEETIE FOX EDITION</div>
                        <div class="quote-text">“{formatted_quote}”</div>
                    </div>
                    {fg_layer_html}
                </body>
                </html>
                """
            elif current_layout == 1:
                html_template = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                        body {{
                            width: 1080px; height: 1440px;
                            background: url('temp_frame.jpg') center/cover no-repeat;
                            font-family: 'Montserrat', sans-serif;
                            display: flex; flex-direction: column; justify-content: flex-start;
                            padding: 120px 80px; position: relative; overflow: hidden;
                        }}
                        .overlay {{ position: absolute; top:0; left:0; width:100%; height:100%; background: linear-gradient(135deg, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.2) 100%); z-index: 1; }}
                        {bubbles_html}
                        {partner_html}
                        .header-tag {{ position: relative; z-index: 20; background: {badge_bg}; color: #000; font-size: 36px; font-weight: 900; padding: 15px 40px; border-radius: 50px; align-self: flex-start; margin-bottom: 60px; }}
                        .card {{ position: relative; z-index: 20; background: {card_bg}; border-left: 12px solid {glow_color}; border-radius: 0 30px 30px 0; padding: 70px; backdrop-filter: blur(15px); }}
                        .quote-text {{ color: #FFFFFF; font-size: 72px; font-weight: 900; line-height: 1.3; text-shadow: 0 5px 20px rgba(0,0,0,0.9); }}
                        .glow-word {{ color: {glow_color}; text-shadow: 0 0 25px {glow_color}; }}
                        .fg-layer {{ position: absolute; top:0; left:0; width:100%; height:100%; background: url('temp_fg.png') center/cover no-repeat; z-index: 50; pointer-events: none; }}
                    </style>
                </head>
                <body>
                    <div class="overlay"></div>
                    {partner_html}
                    <div class="header-tag">⚡ SWEETIE FOX 深度解密</div>
                    <div class="card">
                        <div class="quote-text">“{formatted_quote}”</div>
                    </div>
                    {fg_layer_html}
                </body>
                </html>
                """
            else:
                html_template = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                        body {{
                            width: 1080px; height: 1440px;
                            background: url('temp_frame.jpg') center/cover no-repeat;
                            font-family: 'Montserrat', sans-serif;
                            display: flex; flex-direction: column; justify-content: flex-end;
                            padding: 80px; position: relative; overflow: hidden;
                        }}
                        .overlay {{ position: absolute; top:0; left:0; width:100%; height:100%; background: linear-gradient(180deg, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.85) 100%); z-index: 1; }}
                        {bubbles_html}
                        {partner_html}
                        .bottom-panel {{ position: relative; z-index: 20; width: 100%; background: {card_bg}; border: 2px solid {border_color}; border-radius: 35px; padding: 60px; backdrop-filter: blur(20px); }}
                        .tag-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }}
                        .tag {{ background: {badge_bg}; color: #000; font-size: 28px; font-weight: 900; padding: 8px 24px; border-radius: 10px; }}
                        .brand {{ color: {glow_color}; font-size: 28px; font-weight: 900; letter-spacing: 2px; }}
                        .quote-text {{ color: #FFFFFF; font-size: 68px; font-weight: 900; line-height: 1.25; }}
                        .glow-word {{ color: {glow_color}; text-shadow: 0 0 25px {glow_color}; }}
                        .fg-layer {{ position: absolute; top:0; left:0; width:100%; height:100%; background: url('temp_fg.png') center/cover no-repeat; z-index: 50; pointer-events: none; }}
                    </style>
                </head>
                <body>
                    <div class="overlay"></div>
                    {partner_html}
                    <div class="bottom-panel">
                        <div class="tag-row">
                            <span class="tag">SWEETIE FOX FOCUS</span>
                            <span class="brand">FRENK AI</span>
                        </div>
                        <div class="quote-text">“{formatted_quote}”</div>
                    </div>
                    {fg_layer_html}
                </body>
                </html>
                """

            with open("render_template.html", "w", encoding="utf-8") as f:
                f.write(html_template)

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(
                    viewport={"width": 1080, "height": 1440},
                    device_scale_factor=2
                )
                page.goto(f"file://{os.path.abspath('render_template.html')}", wait_until="networkidle")
                page.screenshot(path="final_cover.png")
                browser.close()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💡 架构模板状态")
                st.info(f"**当前套用模板架构**：`#{current_layout + 1}`\n\n**🦊 Sweetie Fox 专属真人陪伴**：已成功在右侧顶层高亮挂载\n\n> {ai_explanation}")
                st.image("temp_frame.jpg", caption=f"视频第 {target_time:.1f} 秒原帧", use_container_width=True)
            with col2:
                st.subheader(f"✨ 4K 商业爆款封面 [{template_style}]")
                st.image("final_cover.png", use_container_width=True)
                with open("final_cover.png", "rb") as f:
                    st.download_button("📥 下载 4K 华丽封面", f, file_name="commercial_cover.png", mime="image/png")

        except Exception as e:
            st.error(f"处理失败: {str(e)}")
elif not api_key:
    st.info("💡 请在左侧侧边栏输入你的 Groq API Key 以启动系统。")
