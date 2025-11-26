import requests
import streamlit as st
import uuid
import os
from loguru import logger
from user_agents import parse
from datetime import datetime
from pyvis.network import Network
from scenes.configs import SCENE_PRESETS, SCENE_KEYWORDS
from soul_manager import get_soul_manager
from prompt_builder import get_prompt_builder
from image_video_generator import get_image_video_generator

# 公网地址配置（用于生成的媒体文件访问）
PUBLIC_IMAGEGEN_URL = os.getenv("PUBLIC_IMAGEGEN_URL", "http://34.148.94.241:8000")

# ============================================
# 会话状态初始化（必须在任何 Streamlit UI 调用之前）
# ============================================

# 添加评估模式状态
if "assessment_mode" not in st.session_state:
    st.session_state.assessment_mode = "normal"  # normal or pocket_themes

if "pocket_assessment_status" not in st.session_state:
    st.session_state.pocket_assessment_status = None

if "personality_profile" not in st.session_state:
    st.session_state.personality_profile = None

# 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 初始化记忆和关系
if "memories" not in st.session_state:
    st.session_state["memories"] = []

if "relations" not in st.session_state:
    st.session_state["relations"] = []

# ============================================
# 现在可以安全地使用 Streamlit UI 组件
# ============================================

# set title
st.title("Chatbot with long term memory")


def get_browser_fingerprint():
    fingerprint = None
    try:
        # 获取原始请求头
        headers = st.query_params
        # 从请求头中获取用户代理信息
        user_agent = headers.get('User-Agent')
        if user_agent:
            user_agent_info = parse(user_agent)
            fingerprint = str(user_agent_info)
        return fingerprint
    except Exception as e:
        print("get browser fingerprint error: ", e)
        return None


# Scene recommendation function (based on Pocket Souls approach)
def analyze_memories_for_scene_recommendation(memories):
    """
    Analyze user memories and recommend suitable scenes based on Pocket Souls logic
    """
    if not memories:
        return [("reflection", 1.0)]  # Default when no memories
    
    # Combine memory text (like Pocket Souls does)
    memory_text = ""
    for memory in memories[:3]:  # Only first 3 memories like Pocket Souls
        memory_text += str(memory.get('memory', ''))[:100] + " "
    
    memory_text = memory_text.lower()
    
    # Simple keyword matching (Pocket Souls approach)
    scene_scores = {}
    for scene_key, keywords in SCENE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in memory_text:
                score += 1
        scene_scores[scene_key] = score
    
    # If no matches, default to reflection (like Pocket Souls)
    if max(scene_scores.values()) == 0:
        return [("reflection", 1.0)]
    
    # Sort by score and return top 3
    sorted_scenes = sorted(scene_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scenes[:3]

# 初始化 user_id（延迟到需要时再获取浏览器指纹）
if 'user_id' not in st.session_state:
    try:
        # 获取浏览器指纹
        fingerprint = get_browser_fingerprint()
        if fingerprint:
            # 根据指纹生成用户 ID
            st.session_state.user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint))
        else:
            # 如果无法获取指纹，则生成一个随机 ID
            st.session_state.user_id = str(uuid.uuid4())
    except Exception as e:
        logger.error(f"Error getting browser fingerprint: {e}")
        # 如果出错，生成一个随机 ID
        st.session_state.user_id = str(uuid.uuid4())

# 从 session_state 获取 user_id
user_id = st.session_state.user_id


# 获取最新的记忆数据（从 FastAPI 获取）
def get_memories(user_id):
    try:
        # 修复：使用路径参数而不是查询参数
        response = requests.get(f"http://34.148.51.133:8082/memories/{user_id}")  # 获取所有记忆的 API
        if response.status_code == 200:
            json_data = response.json()
            # 后端返回的格式已经分类好了
            profile = json_data.get("profile", [])
            facts = json_data.get("facts", [])
            style = json_data.get("style", [])
            commitments = json_data.get("commitments", [])
            relations = json_data.get("relations", [])

            # 合并所有记忆
            results = profile + facts + style + commitments
            return results, relations
        else:
            # 不要在这里调用 st.error，而是返回空列表并记录日志
            logger.error(f"Unable to fetch memories from backend. Status: {response.status_code}")
            return [], []
    except requests.exceptions.RequestException as e:
        # 不要在这里调用 st.error，而是返回空列表并记录日志
        logger.error(f"Error fetching memories: {e}")
        return [], []

# 初始化 mem_changed 标志，默认值为 False
mem_changed = False

# 初始化user_id
if 'user_input' not in st.session_state:
    st.session_state.user_input = user_id  # 初始默认值

# 初始化视频/图片生成标志
if 'is_generating' not in st.session_state:
    st.session_state.is_generating = False


# 显示侧边栏的输入选项
with st.sidebar:
    # user_id
    user_input = st.text_input(label='user_id', placeholder="请输入用户id")
    if not user_input:
        st.warning("请先输入用户id")
    if user_input:
        user_id = user_input
        st.session_state.user_input = user_input

    # 安全地加载记忆
    try:
        memories, relations = get_memories(user_id)
        st.session_state["memories"] = memories
        st.session_state["relations"] = relations
        logger.info(f"Loaded {len(memories)} memories for user {user_id}")
    except Exception as e:
        logger.error(f"Error loading memories: {e}")
        st.error(f"⚠️ Failed to load memories: {str(e)}")
        st.session_state["memories"] = []
        st.session_state["relations"] = []
    
    # 评估模式选择
    st.write("**Assessment Mode**")
    assessment_mode = st.radio(
        "Choose mode:",
        ["Normal Chat", "Pocket Themes Assessment"],
        index=0 if st.session_state.assessment_mode == "normal" else 1,
        help="Normal Chat: Regular conversation with memory. Pocket Themes: Deep personality assessment through 5 mystical themes."
    )
    
    if assessment_mode == "Normal Chat":
        st.session_state.assessment_mode = "normal"
    else:
        st.session_state.assessment_mode = "pocket_themes"
    
    # 模型选择（默认使用免费的 ChatGLM glm-4-flash）
    model = st.selectbox("models", ["glm-4-flash", "doubao-character", "deepseek-v3.1", "gemini"])

    # Scene selection with smart recommendation
    st.write("**Scene Selection**")
    
    # Smart recommendation button
    if st.button("🔮 Smart Recommendation", help="Recommend scenes based on your memories"):
        if 'memories' in st.session_state and st.session_state['memories']:
            recommendations = analyze_memories_for_scene_recommendation(st.session_state['memories'])
            
            st.write("**Recommended Scenes:**")
            for i, (scene_key, score) in enumerate(recommendations, 1):
                scene_name = SCENE_PRESETS[scene_key]['label']
                st.write(f"{i}. {scene_name} (Score: {score})")
            
            # Store recommendations for selection
            st.session_state['scene_recommendations'] = recommendations
        else:
            st.warning("No memories available for recommendation")
    
    # Scene selection dropdown
    scene_options = {
        "Default (No Scene)": "default",
        "Creative Breakthrough": "creative", 
        "Midnight Inspiration": "contemplative",
        "Connection Moment": "connection",
        "Growth Edge": "growth",
        "Mirror Moment": "reflection"
    }
    
    # If there are recommendations, show them as options
    if 'scene_recommendations' in st.session_state and st.session_state['scene_recommendations']:
        # Add recommended scenes to the top of the list
        recommended_options = {}
        for scene_key, score in st.session_state['scene_recommendations']:
            scene_name = SCENE_PRESETS[scene_key]['label']
            recommended_options[f"⭐ {scene_name} (Recommended)"] = scene_key
        
        # Add other scenes
        for label, key in scene_options.items():
            if key not in [rec[0] for rec in st.session_state['scene_recommendations']]:
                recommended_options[label] = key
        
        scene_label = st.selectbox("Choose Scene", list(recommended_options.keys()))
        scene = recommended_options[scene_label]
    else:
        scene_label = st.selectbox("Choose Scene", list(scene_options.keys()), index=0)
        scene = scene_options[scene_label]

    # 初始化 Soul 管理器
    soul_manager = get_soul_manager(PUBLIC_IMAGEGEN_URL)
    all_souls = soul_manager.get_all_souls()
    soul_ids = list(all_souls.keys())

    # Soul 选择下拉框
    st.markdown("### 👤 Soul")
    selected_soul_id = st.selectbox(
        "Choose a Soul",
        soul_ids,
        index=0 if "nova" in soul_ids else 0,
        key="soul_selector",
        label_visibility="collapsed"
    )

    # 显示选中 Soul 的风格信息
    if selected_soul_id:
        soul_info = soul_manager.get_soul_display_info(selected_soul_id)
        if soul_info:
            st.caption(soul_info)

    # 使用更清晰的变量名
    soul_id = selected_soul_id

    # ============================================
    # 📸 Soul Selfie Generation Panel
    # ============================================
    st.markdown("---")
    st.markdown("### 📸 Soul Selfie")
    st.caption("Generate Soul's selfie photos/videos in different cities and moods")

    # City selection
    city_options = {
        "🗼 Paris": "paris",
        "🗾 Tokyo": "tokyo",
        "🗽 New York": "newyork",
        "🏰 London": "london",
        "🏛️ Rome": "rome"
    }
    selected_city_label = st.selectbox(
        "📍 Travel Location",
        list(city_options.keys()),
        key="selfie_city_selector"
    )
    selfie_city = city_options[selected_city_label]

    # Mood selection
    mood_options = {
        "😊 Happy": "happy",
        "😢 Sad": "sad",
        "🤩 Excited": "excited",
        "😌 Calm": "calm",
        "💕 Romantic": "romantic",
        "🏃 Adventurous": "adventurous"
    }
    selected_mood_label = st.selectbox(
        "💭 Current Mood",
        list(mood_options.keys()),
        key="selfie_mood_selector"
    )
    selfie_mood = mood_options[selected_mood_label]

    # Generate buttons
    col_selfie_img, col_selfie_vid = st.columns(2)
    with col_selfie_img:
        generate_selfie_image_btn = st.button("🖼️ Generate Image", key="generate_selfie_image", use_container_width=True)
    with col_selfie_vid:
        generate_selfie_video_btn = st.button("🎬 Generate Video", key="generate_selfie_video", use_container_width=True)

    # Extract city and mood names
    city_name = selected_city_label.split()[1] if len(selected_city_label.split()) > 1 else selected_city_label.replace("🗼 ", "").replace("🗾 ", "").replace("🗽 ", "").replace("🏰 ", "").replace("🏛️ ", "")
    mood_name = selected_mood_label.split()[1] if len(selected_mood_label.split()) > 1 else selected_mood_label.replace("😊 ", "").replace("😢 ", "").replace("🤩 ", "").replace("😌 ", "").replace("💕 ", "").replace("🏃 ", "")
    st.caption(f"💡 Will generate **{soul_id}**'s **{mood_name}** selfie in **{city_name}**")

    st.markdown("---")
    # ============================================

    # 记忆抽取频率
    frequency = st.number_input("Extract Memory Frequency", min_value=1, max_value=10, step=1, value=1)

    # 总结频率
    summary_frequency = st.number_input("Summary Frequency", min_value=1, max_value=50, step=1, value=10)

# 创建布局：左侧聊天区，右侧日记栏
col_chat, col_diary = st.columns([2.5, 1], gap="medium")

# 左侧聊天区域
with col_chat:
    # 显示聊天记录
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # 检查是否包含图片链接
            if "![" in msg["content"] and "](" in msg["content"]:
                # 提取图片 URL
                import re
                match = re.search(r'!\[.*?\]\((.*?)\)', msg["content"])
                if match:
                    image_url = match.group(1)
                    # 显示文本部分
                    text_part = msg["content"].split("![")[0].strip()
                    if text_part:
                        st.write(text_part)

                    # 显示图片
                    try:
                        st.image(image_url, use_container_width=True)
                    except:
                        st.write(f"🖼️ [View Image]({image_url})")

                    # 添加下载链接（使用 Markdown 避免每次渲染都下载图片）
                    if "image_url" in msg and "image_filename" in msg:
                        st.markdown(f"[📥 Download {msg['image_filename']}]({msg['image_url']})")
                else:
                    st.write(msg["content"])
            else:
                st.write(msg["content"])

# Pocket评估模式UI
if st.session_state.assessment_mode == "pocket_themes":
    # 检查评估状态
    if st.session_state.pocket_assessment_status is None:
        # 开始评估
        if st.button("🌟 Start Mystical Personality Assessment", type="primary"):
            try:
                response = requests.post(
                    f"http://34.148.51.133:8082/start_pocket_assessment",
                    params={"user_id": user_id, "model": model}
                )
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.pocket_assessment_status = result
                    st.rerun()
                else:
                    st.error("Failed to start assessment")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        # 显示评估状态面板
        with st.container():
            st.markdown("### 🌟 Personality Assessment Status")
            
            status = st.session_state.pocket_assessment_status
            progress = status.get("progress", {})
            
            # 进度条
            progress_percentage = progress.get("percentage", 0)
            st.progress(progress_percentage / 100)
            st.write(f"Progress: {progress_percentage:.1f}%")
            
            # 主题进度
            themes_completed = progress.get("themes_completed", 0)
            total_themes = progress.get("total_themes", 5)
            st.write(f"Themes Completed: {themes_completed}/{total_themes}")
            
            # Big5状态
            big5_status = status.get("big5_status", {})
            st.write("**Big Five Traits Progress:**")
            for trait, info in big5_status.items():
                confidence = info.get("confidence", 0)
                ready = info.get("ready", False)
                status_icon = "✅" if ready else "⏳"
                st.write(f"{status_icon} {trait.title()}: {confidence}% confidence")
            
            # 当前主题
            current_theme = status.get("current_theme", "Unknown")
            st.write(f"**Current Theme:** {current_theme.replace('_', ' ').title()}")
            
            # 如果评估完成
            if status.get("status") == "completed":
                st.success("🎉 Assessment Completed! Your personality profile has been created.")
                if "personality_profile" in status:
                    profile = status["personality_profile"]
                    st.session_state.personality_profile = profile
                    
                    # 显示性格档案
                    st.markdown("### 📊 Your Personality Profile")
                    st.write(f"**Primary Traits:** {', '.join(profile.get('primary_traits', []))}")
                    st.write(f"**Emotional State:** {profile.get('emotional_state', 'Unknown')}")
                    
                    big5_scores = profile.get("big5_scores", {})
                    st.write("**Big Five Scores:**")
                    for trait, score in big5_scores.items():
                        st.write(f"- {trait.title()}: {score}%")
                
                # 返回正常聊天按钮
                if st.button("💬 Return to Normal Chat"):
                    st.session_state.assessment_mode = "normal"
                    st.session_state.pocket_assessment_status = None
                    st.rerun()
            else:
                # 显示当前问题
                if "question" in status:
                    st.markdown("### 🔮 Current Question")
                    st.markdown(status["question"])
                    
                    # 用户回答输入
                    # 初始化清空标志
                    if f"clear_response_{user_id}" not in st.session_state:
                        st.session_state[f"clear_response_{user_id}"] = False
                    
                    # 如果需要清空，重置输入框
                    if st.session_state[f"clear_response_{user_id}"]:
                        st.session_state[f"pocket_response_{user_id}"] = ""
                        st.session_state[f"clear_response_{user_id}"] = False
                    
                    # 初始化输入框状态
                    if f"pocket_response_{user_id}" not in st.session_state:
                        st.session_state[f"pocket_response_{user_id}"] = ""
                    
                    user_response = st.text_area(
                        "Your Response:",
                        placeholder="Share your thoughts...",
                        height=100,
                        value=st.session_state[f"pocket_response_{user_id}"],
                        key=f"pocket_response_{user_id}"
                    )
                    
                    if st.button("Send Response", type="primary") and user_response:
                        try:
                            # 处理回答
                            response = requests.post(
                                f"http://34.148.51.133:8082/pocket_assessment_response",
                                params={"user_id": user_id, "response": user_response, "model": model}
                            )
                            if response.status_code == 200:
                                result = response.json()

                                # 如果评估完成，显示结果
                                if result.get("status") == "completed":
                                    st.session_state.personality_profile = result.get("personality_profile")

                                # 获取完整评估状态
                                status_response = requests.get(f"http://34.148.51.133:8082/pocket_assessment_status/{user_id}")
                                if status_response.status_code == 200:
                                    st.session_state.pocket_assessment_status = status_response.json()
                                
                                # 设置清空标志
                                st.session_state[f"clear_response_{user_id}"] = True
                                
                                st.rerun()
                            else:
                                st.error("Failed to process response")
                        except Exception as e:
                            st.error(f"Error: {e}")
    
        # 在Pocket评估模式下，不显示常规聊天输入
        with col_chat:
            st.info("🌟 You are in Pocket Themes Assessment mode. Complete the assessment to return to normal chat.")
else:
    # 正常聊天模式
    # 如果已完成Pocket评估，显示性格档案
    if st.session_state.personality_profile:
        with st.expander("📊 Your Personality Profile", expanded=False):
            profile = st.session_state.personality_profile
            st.write(f"**Primary Traits:** {', '.join(profile.get('primary_traits', []))}")
            st.write(f"**Emotional State:** {profile.get('emotional_state', 'Unknown')}")
            
            big5_scores = profile.get("big5_scores", {})
            st.write("**Big Five Scores:**")
            for trait, score in big5_scores.items():
                st.write(f"- {trait.title()}: {score}%")

# 右侧栏：日记区域（与左侧sidebar对称）
with col_diary:
    if user_input:  # 确保user_id存在
        from diary.diary_ui import render_diary_sidebar
        render_diary_sidebar(user_id)
    else:
        st.info("Please enter user_id in the left sidebar to view diary")

# 聊天输入和生成按钮
col_input, col_gen_img, col_gen_vid = st.columns([3, 1, 1])

with col_input:
    prompt = st.chat_input("Type your message...")

with col_gen_img:
    generate_image_btn = st.button("🖼️ Generate Image", key="gen_img_btn")

with col_gen_vid:
    generate_video_btn = st.button("🎬 Generate Video", key="gen_vid_btn")

# 处理聊天输入
if prompt:
    # 检查是否是 /diary 命令
    if prompt.strip().lower() == "/diary":
        # 获取日记并在聊天中显示
        diary_data = get_user_diary(user_id) if user_input else None
        
        if diary_data:
            diary = diary_data.get("diary", {})
            date = diary_data.get("date", "")
            is_today = diary_data.get("is_today", False)
            
            # 构建日记消息
            title = diary.get("title", "Today's Reflection")
            body_lines = diary.get("body_lines", [])
            tags = diary.get("tags", [])
            
            diary_content = f"**📔 {'Today' if is_today else date}'s Reflection**\n\n"
            diary_content += f"### {title}\n\n"
            for line in body_lines:
                if line.strip():
                    diary_content += f"{line.strip()}\n"
            if tags:
                diary_content += f"\n**Tags:** {' '.join([f'`{tag}`' for tag in tags])}"
            
            # 添加到消息列表并显示
            st.session_state.messages.append({
                "role": "assistant",
                "content": diary_content,
                "time": datetime.now().strftime("%Y-%m-%d")
            })
            with col_chat:
                st.chat_message("assistant").write(diary_content)
        else:
            # 没有日记
            with col_chat:
                st.info("No diary available yet. Diary will be generated automatically at 21:00-22:00 daily.")
    else:
        # 普通聊天消息
        # 显示用户输入
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "time": datetime.now().strftime("%Y-%m-%d")})
        with col_chat:
            st.chat_message("user").write(prompt)

        # 发送请求，获取聊天回复
        try:
            response = requests.post(
                "http://34.148.51.133:8082/chat",  # API 地址
                json={
                    "user_id": user_id,
                    "message": prompt,
                    "model": model,
                    "soul_id": soul_id,  # 使用选中的 Soul ID
                    "frequency": frequency,
                    "summary_frequency": summary_frequency,
                    "scene": scene,
                    "assessment_mode": st.session_state.assessment_mode
                }
            )
            if response.status_code == 200:
                json_response = response.json()
                bot_reply = json_response.get("response", "No response from server.")
                new_mem = json_response.get("new_memory", '')
                graph_memory = json_response.get("graph_memory", "")
                summary = json_response.get("summary", {}).get("result", "")
                logger.info("=" * 20)
                logger.info(f"user_id: {user_id}")
                logger.info(f"input: {prompt}")
                logger.info(f"response: {bot_reply}")
                logger.info(f"memory: {new_mem}")
                logger.info(f"graph memory: {graph_memory}")
                logger.info(f"summary: {summary}")

                if new_mem:
                    mem_changed = True
                    # bot_reply = bot_reply + "\n\n" + "[记忆已更新]"

                    # 如果记忆更新，重新获取最新的记忆
                    new_memories, relations = get_memories(user_id)
                    print(f"new_memories: {new_memories}")

                    if new_memories != st.session_state["memories"]:
                        st.session_state["memories"] = new_memories
                        # 只在记忆变化时更新侧边栏
                        profile = []
                        facts = []
                        style = []
                        commitments = []
                        for mem in st.session_state["memories"]:
                            if mem.get('metadata', {}).get('type') == "profile":
                                #mem['memory'] = mem['memory'].split(":")[1].strip()
                                profile.append(mem)
                            elif mem.get('metadata', {}).get('type') == "style":
                                #mem['memory'] = mem['memory'].split(":")[1].strip()
                                style.append(mem)
                            elif mem.get('metadata', {}).get('type') == "commitments":
                                #mem['memory'] = mem['memory'].split(":")[1].strip()
                                commitments.append(mem)
                            else:
                                #if ':' in mem['memory']:
                                #    mem['memory'] = mem['memory'].split(":")[1].strip()
                                facts.append(mem)
                        # 更新侧边栏的记忆展示
                        st.sidebar.write("Profile：")
                        st.sidebar.json(profile)
                        st.sidebar.write("Facts：")
                        st.sidebar.json(facts)
                        st.sidebar.write("Style：")
                        st.sidebar.json(style)
                        st.sidebar.write("Commitments：")
                        st.sidebar.json(commitments)

                    if relations != st.session_state["relations"]:
                        st.session_state["relations"] = relations

                st.session_state.messages.append(
                    {"role": "assistant", "content": bot_reply, "time": datetime.now().strftime("%Y-%m-%d")})
                with col_chat:
                    st.chat_message("assistant").write(bot_reply)
                # 展示使用的记忆/新增记忆/图谱
                used_memory = json_response.get("used_memory", "")
                if used_memory or new_mem or graph_memory or summary:

                    with st.expander("🤖记忆内容展示"):
                        if used_memory:
                            st.markdown("**引用记忆：**")
                            st.markdown(used_memory)
                        if new_mem:
                            st.markdown("**新增记忆：**")
                            st.json(new_mem)
                        if summary:
                            st.markdown("**会话总结：**")
                            st.markdown(summary)
                        # deleted_entities = graph_memory.get("deleted_entities", [])
                        if graph_memory:
                            added_entities = graph_memory.get("added_entities", [])
                            if added_entities:
                                for item in st.session_state["relations"]:
                                    net.add_node(item["source"], label=item["source"])
                                    net.add_node(item["target"], label=item["target"])
                                    net.add_edge(item["source"], item["target"])
                                # 生成 HTML 文件
                                net.save_graph(f"graph-{user_id}.html")
                                HtmlFile = open(f"graph-{user_id}.html", 'r', encoding='utf-8')
                                source_code = HtmlFile.read()
                                st.markdown("**图谱展示：**")
                                st.components.v1.html(source_code, height=500)

            else:
                st.error("Error: Unable to fetch response from the backend.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error: {e}")

# 处理生成图像按钮
if generate_image_btn:
    # 获取最后一条用户消息作为 prompt（不要重复添加，因为已经在聊天输入时添加过了）
    user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
    if user_messages:
        last_user_msg = user_messages[-1]["content"]
        logger.info(f"[Generate Image] Last user message: {last_user_msg}")

        # 检查是否是自拍命令
        prompt_builder = get_prompt_builder()
        selfie_params = prompt_builder.detect_selfie_command(last_user_msg)
        logger.info(f"[Generate Image] Selfie params: {selfie_params}")

        if selfie_params:
            # 自拍模式
            city_key, mood = selfie_params
            with st.spinner(f"🖼️ Generating selfie image in {city_key} with {mood} mood..."):
                generator = get_image_video_generator("http://34.148.94.241:8000")
                result = generator.generate_selfie_image(
                    soul_id=soul_id,
                    city_key=city_key,
                    mood=mood,
                    user_id=user_id
                )

                if result:
                    # API 返回的字段是 'url'，需要映射到完整的可访问 URL
                    image_url = result.get("url") or result.get("image_url")
                    variant_id = result.get("variant_id")

                    if image_url:
                        # 如果是相对路径，转换为 imageGen 服务器的公网 URL
                        if image_url.startswith("/"):
                            # 提取文件名
                            filename = image_url.split("/")[-1]
                            # 使用 imageGen 服务器的公网地址
                            full_image_url = f"http://34.148.94.241:8000{image_url}"
                            logger.info(f"[Generate Selfie Image] Converted relative path to public URL: {full_image_url}")
                        else:
                            full_image_url = image_url

                        # 提取文件名
                        image_filename = full_image_url.split("/")[-1] if "/" in full_image_url else "selfie.png"

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"🖼️ Selfie Image Generated!\n\n![Selfie]({full_image_url})",
                            "time": datetime.now().strftime("%Y-%m-%d"),
                            "image_url": full_image_url,
                            "image_filename": image_filename
                        })
                        with col_chat:
                            st.image(full_image_url, caption="Generated Selfie", use_container_width=True)
                            # 添加下载链接
                            st.markdown(f"[📥 Download {image_filename}]({full_image_url})")
                    else:
                        st.error("Failed to generate selfie image: No URL in response.")
                else:
                    st.error("Failed to generate selfie image.")
        else:
            # 标准模式 - 从聊天上下文生成
            try:
                # 使用 spinner 显示进度，与视频生成保持一致
                with st.spinner("🖼️ Generating image from chat context... This may take seconds, please wait..."):
                    generator = get_image_video_generator("http://34.148.94.241:8000")
                    soul_manager = get_soul_manager("http://34.148.94.241:8000")
                    soul_info = soul_manager.get_all_souls().get(soul_id, {})
                    soul_keywords = soul_info.get("style_keywords", [])
                    logger.info(f"[Generate Image] Soul keywords: {soul_keywords}")

                    # 构建 cue
                    cue = generator.build_cue_from_context(
                        last_user_msg,
                        st.session_state.messages,
                        soul_keywords
                    )
                    logger.info(f"[Generate Image] Built cue: {cue}")

                    # 调用 API 生成图像
                    result = generator.generate_image(
                        soul_id=soul_id,
                        cue=cue,
                        user_id=user_id
                    )
                logger.info(f"[Generate Image] API result: {result}")

                if result:
                    # API 返回的字段是 'url'，需要映射到完整的可访问 URL
                    image_url = result.get("url") or result.get("image_url")
                    variant_id = result.get("variant_id")

                    if image_url:
                        # 检查是否是视频 URL（错误返回）
                        is_video = image_url.endswith(('.mp4', '.avi', '.mov', '.gif'))

                        if is_video:
                            # 如果返回的是视频，显示错误提示
                            st.error("⚠️ Image generation returned a video instead of an image. This is a cache issue. Please try again with a different prompt.")
                            logger.error(f"[Generate Image] Received video URL instead of image: {image_url}")
                        else:
                            # 如果是相对路径，转换为 imageGen 服务的完整 URL
                            if image_url.startswith("/"):
                                # 将 /generated/ 转换为 /static/image/（支持下载）
                                if "/generated/" in image_url:
                                    filename = image_url.split("/generated/")[-1]
                                    image_url = f"/static/image/{filename}"
                                # 使用 imageGen 的静态文件服务（公网地址）
                                full_image_url = f"http://34.148.94.241:8000{image_url}"
                            else:
                                full_image_url = image_url

                            # 提取文件名用于显示
                            image_filename = full_image_url.split("/")[-1] if "/" in full_image_url else "Generated Image"

                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"🖼️ Image Generated!\n\n![{image_filename}]({full_image_url})",
                                "time": datetime.now().strftime("%Y-%m-%d"),
                                "image_url": full_image_url,  # 保存图片 URL 用于下载
                                "image_filename": image_filename
                            })

                            with col_chat:
                                # 显示图片
                                st.image(full_image_url, caption=image_filename, use_container_width=True)
                                # 添加下载链接
                                st.markdown(f"[📥 Download {image_filename}]({full_image_url})")

                            # 强制刷新页面以显示新消息
                            st.rerun()
                    else:
                        # 清除生成标志
                        st.session_state.is_generating = False
                        st.error("Failed to generate image: No URL in response.")
                        logger.error(f"[Generate Image] No URL in result: {result}")
                else:
                    st.error("Failed to generate image: API returned None.")
                    logger.error("[Generate Image] API returned None")

            except Exception as e:
                st.error(f"Failed to generate image: {str(e)}")
                logger.error(f"[Generate Image] Exception: {e}", exc_info=True)

# 处理生成视频按钮
if generate_video_btn:
    # 获取最后一条用户消息作为 prompt（不要重复添加，因为已经在聊天输入时添加过了）
    user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
    if user_messages:
        last_user_msg = user_messages[-1]["content"]
        logger.info(f"[Generate Video] Last user message: {last_user_msg}")

        # 检查是否是自拍命令
        prompt_builder = get_prompt_builder()
        selfie_params = prompt_builder.detect_selfie_command(last_user_msg)
        logger.info(f"[Generate Video] Selfie params: {selfie_params}")

        if selfie_params:
            # 自拍模式
            city_key, mood = selfie_params
            with st.spinner(f"🎬 Generating selfie video in {city_key} with {mood} mood..."):
                generator = get_image_video_generator("http://34.148.94.241:8000")
                result = generator.generate_selfie_video(
                    soul_id=soul_id,
                    city_key=city_key,
                    mood=mood,
                    user_id=user_id
                )

                if result:
                    # API 返回的字段是 'gif_url'（已经是完整的公网 URL）
                    gif_url = result.get("gif_url", "")

                    if gif_url:
                        # 提取文件名用于显示
                        gif_filename = gif_url.split("/")[-1] if "/" in gif_url else gif_url

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"🎬 Selfie Video Generated!\n\n![{gif_filename}]({gif_url})",
                            "time": datetime.now().strftime("%Y-%m-%d"),
                            "image_url": gif_url,
                            "image_filename": gif_filename
                        })

                        with col_chat:
                            # 只显示 GIF 动画
                            st.image(gif_url, caption=gif_filename, use_container_width=True)
                            # 添加下载链接
                            st.markdown(f"[📥 Download {gif_filename}]({gif_url})")
                    else:
                        st.error("Failed to generate selfie video: No GIF URL in response.")
                else:
                    st.error("Failed to generate selfie video.")
        else:
            # 标准模式 - 从聊天上下文生成
            try:
                # 使用 spinner 显示进度，这样 Streamlit 知道我们在等待
                with st.spinner("🎬 Generating video from chat context... This may take minutes, please wait..."):
                    generator = get_image_video_generator("http://34.148.94.241:8000")
                    soul_manager = get_soul_manager("http://34.148.94.241:8000")
                    soul_info = soul_manager.get_all_souls().get(soul_id, {})
                    soul_keywords = soul_info.get("style_keywords", [])
                    logger.info(f"[Generate Video] Soul keywords: {soul_keywords}")

                    # 构建 cue
                    cue = generator.build_cue_from_context(
                        last_user_msg,
                        st.session_state.messages,
                        soul_keywords
                    )
                    logger.info(f"[Generate Video] Built cue: {cue}")

                    # 调用 API 生成视频
                    result = generator.generate_video(
                        soul_id=soul_id,
                        cue=cue,
                        user_id=user_id
                    )
                logger.info(f"[Generate Video] API result: {result}")

                # spinner 结束后处理结果
                if result:
                    # API 返回的字段是 'gif_url'（已经是完整的公网 URL）
                    gif_url = result.get("gif_url", "")

                    if gif_url:
                        # 提取文件名用于显示
                        gif_filename = gif_url.split("/")[-1] if "/" in gif_url else gif_url

                        # 添加到消息历史，包含 GIF 图片（使用 Markdown 图片语法）
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"🎬 Video Generated!\n\n![{gif_filename}]({gif_url})",
                            "time": datetime.now().strftime("%Y-%m-%d"),
                            "image_url": gif_url,
                            "image_filename": gif_filename
                        })

                        # 强制刷新页面以显示新消息
                        st.rerun()
                    else:
                        # 清除生成标志
                        st.session_state.is_generating = False
                        st.error("Failed to generate video: No GIF URL in response.")
                        logger.error(f"[Generate Video] No GIF URL in result: {result}")
                else:
                    st.error("Failed to generate video: API returned None.")
                    logger.error("[Generate Video] API returned None")

            except Exception as e:
                st.error(f"Failed to generate video: {str(e)}")
                logger.error(f"[Generate Video] Exception: {e}", exc_info=True)

# 创建一个简单的知识图谱
net = Network(width="100%", height="500px", notebook=False)

# 显示初始的记忆数据（如果没有变化）
if "memories" in st.session_state and not mem_changed:
    profile = []
    facts = []
    style = []
    commitments = []

    for mem in st.session_state["memories"]:
        # if mem['memory'].startswith("profile"):
        if mem.get('metadata', {}).get('type') == "profile":
            # mem['memory'] = mem['memory'].split(":")[1].strip()
            profile.append(mem)
        elif mem.get('metadata', {}).get('type') == "style":
            style.append(mem)
        elif mem.get('metadata', {}).get('type') == "commitments":
            commitments.append(mem)
        else:
            if ':' in mem['memory']:
                mem['memory'] = mem['memory'].split(":")[1].strip()
            facts.append(mem)
    # 更新侧边栏的记忆展示
    st.sidebar.write("Profile：")
    st.sidebar.json(profile)
    st.sidebar.write("Facts：")
    st.sidebar.json(facts)
    st.sidebar.write("Style：")
    st.sidebar.json(style)
    st.sidebar.write("Commitments：")
    st.sidebar.json(commitments)

# ============================================
# 处理 Soul 自拍图像生成按钮
# ============================================
if generate_selfie_image_btn:
    logger.info(f"[Generate Selfie Image] Soul: {soul_id}, City: {selfie_city}, Mood: {selfie_mood}")

    with st.spinner(f"🖼️ Generating {soul_id}'s {selfie_mood} selfie in {selfie_city}..."):
        generator = get_image_video_generator("http://34.148.94.241:8000")
        result = generator.generate_selfie_image(
            soul_id=soul_id,
            city_key=selfie_city,
            mood=selfie_mood,
            user_id=user_id
        )

        if result:
            image_url = result.get("url") or result.get("image_url")
            variant_id = result.get("variant_id")
            landmark_key = result.get("landmark_key", "")

            if image_url:
                # Convert relative path to full URL
                if image_url.startswith("/"):
                    full_image_url = f"http://34.148.94.241:8000{image_url}"
                    logger.info(f"[Generate Selfie Image] Converted to public URL: {full_image_url}")
                else:
                    full_image_url = image_url

                # Extract filename
                image_filename = full_image_url.split("/")[-1] if "/" in full_image_url else "selfie.png"

                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"📸 {soul_id}'s selfie is here!\n\nAt {landmark_key} in {selfie_city}, feeling {selfie_mood}\n\n![Selfie]({full_image_url})",
                    "time": datetime.now().strftime("%Y-%m-%d"),
                    "image_url": full_image_url,
                    "image_filename": image_filename
                })

                with col_chat:
                    st.success(f"✅ Selfie image generated successfully! Landmark: {landmark_key}")
                    st.image(full_image_url, caption=f"{soul_id} at {landmark_key}", use_container_width=True)
                    st.markdown(f"[📥 Download Image]({full_image_url})")
            else:
                st.error("❌ Generation failed: No image URL returned")
        else:
            st.error("❌ Selfie image generation failed")

# ============================================
# 处理 Soul 自拍视频生成按钮
# ============================================
if generate_selfie_video_btn:
    logger.info(f"[Generate Selfie Video] Soul: {soul_id}, City: {selfie_city}, Mood: {selfie_mood}")

    with st.spinner(f"🎬 Generating {soul_id}'s {selfie_mood} selfie video in {selfie_city}... (may take a few minutes)"):
        generator = get_image_video_generator("http://34.148.94.241:8000")
        result = generator.generate_selfie_video(
            soul_id=soul_id,
            city_key=selfie_city,
            mood=selfie_mood,
            user_id=user_id
        )

        if result:
            gif_url = result.get("gif_url", "")
            mp4_url = result.get("mp4_url", "")
            variant_id = result.get("variant_id")
            landmark_key = result.get("landmark_key", "")

            if gif_url:
                # Extract filename
                gif_filename = gif_url.split("/")[-1] if "/" in gif_url else "selfie.gif"

                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"🎬 {soul_id}'s selfie video is here!\n\nAt {landmark_key} in {selfie_city}, feeling {selfie_mood}\n\n![{gif_filename}]({gif_url})",
                    "time": datetime.now().strftime("%Y-%m-%d"),
                    "image_url": gif_url,
                    "image_filename": gif_filename
                })

                with col_chat:
                    st.success(f"✅ Selfie video generated successfully! Landmark: {landmark_key}")
                    st.image(gif_url, caption=f"{soul_id} at {landmark_key}", use_container_width=True)
                    if mp4_url:
                        st.markdown(f"[📥 Download GIF]({gif_url}) | [📥 Download MP4]({mp4_url})")
                    else:
                        st.markdown(f"[📥 Download GIF]({gif_url})")
            else:
                st.error("❌ Generation failed: No video URL returned")
        else:
            st.error("❌ Selfie video generation failed")
