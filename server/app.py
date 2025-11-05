import requests
import streamlit as st
import uuid
from loguru import logger
from user_agents import parse
from datetime import datetime
from pyvis.network import Network
from scenes.configs import SCENE_PRESETS, SCENE_KEYWORDS

# set title
st.title("Chatbot with long term memory")

# 添加评估模式状态
if "assessment_mode" not in st.session_state:
    st.session_state.assessment_mode = "normal"  # normal or pocket_themes

if "pocket_assessment_status" not in st.session_state:
    st.session_state.pocket_assessment_status = None

if "personality_profile" not in st.session_state:
    st.session_state.personality_profile = None


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

# 获取浏览器指纹
fingerprint = get_browser_fingerprint()

if fingerprint:
    # 根据指纹生成用户 ID
    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint))
else:
    # 如果无法获取指纹，则生成一个随机 ID
    user_id = str(uuid.uuid4())


# 获取最新的记忆数据（从 FastAPI 获取）
def get_memories(user_id):
    try:
        # 修复：使用路径参数而不是查询参数
        response = requests.get(f"http://localhost:8082/memories/{user_id}")  # 获取所有记忆的 API
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
            st.error("Error: Unable to fetch memories from the backend.")
            return [], []
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        return [], []


# 初始化聊天记录和记忆
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 初始化 mem_changed 标志，默认值为 False
mem_changed = False

# 初始化user_id
if 'user_input' not in st.session_state:
    st.session_state.user_input = user_id  # 初始默认值

# 初始化每个用户的欢迎语显示标志
if 'user_welcome_shown' not in st.session_state:
    st.session_state.user_welcome_shown = {}  # {user_id: True/False}

# 欢迎语
WELCOME_MESSAGE = "I'm Nova—your pocket guardian. Want to pick a tiny scene to start?"

# 显示侧边栏的输入选项
with st.sidebar:
    # user_id
    user_input = st.text_input(label='user_id', placeholder="请输入用户id")
    if not user_input:
        st.warning("请先输入用户id")
    if user_input:
        user_id = user_input
        st.session_state.user_input = user_input
        
        # 检查是否是新用户（首次输入user_id且messages为空）
        # 或者切换了user_id（需要清空消息并显示欢迎语）
        if user_id != st.session_state.get('last_user_id', None):
            # 切换了user_id，清空消息列表
            st.session_state.messages = []
            st.session_state.last_user_id = user_id
        
        # 如果是新用户且未显示过欢迎语，显示欢迎语
        if len(st.session_state.messages) == 0 and not st.session_state.user_welcome_shown.get(user_id, False):
            # 添加欢迎语到消息列表
            st.session_state.messages.append({
                "role": "assistant",
                "content": WELCOME_MESSAGE,
                "time": datetime.now().strftime("%Y-%m-%d")
            })
            st.session_state.user_welcome_shown[user_id] = True
    
    st.session_state["memories"], st.session_state["relations"] = get_memories(user_id)
    print(f"memories: {st.session_state['memories']}")
    
    # 评估模式选择
    st.write("**Assessment Mode**")
    
    # 记录之前的模式，用于检测模式切换
    previous_mode = st.session_state.assessment_mode
    
    assessment_mode = st.radio(
        "Choose mode:",
        ["Normal Chat", "Pocket Themes Assessment"],
        index=0 if st.session_state.assessment_mode == "normal" else 1,
        help="Normal Chat: Regular conversation with memory. Pocket Themes: Deep personality assessment through 5 mystical themes."
    )
    
    if assessment_mode == "Normal Chat":
        new_mode = "normal"
    else:
        new_mode = "pocket_themes"
    
    # 检测模式是否切换
    if new_mode != previous_mode:
        # 模式切换了，清空聊天历史
        st.session_state.messages = []
        st.session_state.assessment_mode = new_mode
        
        # 如果切换到 Normal Chat，显示欢迎语
        if new_mode == "normal" and user_input:
            st.session_state.messages.append({
                "role": "assistant",
                "content": WELCOME_MESSAGE,
                "time": datetime.now().strftime("%Y-%m-%d")
            })
            # 重置该用户的欢迎语显示标志，确保切换回来时能显示欢迎语
            if user_input in st.session_state.user_welcome_shown:
                del st.session_state.user_welcome_shown[user_input]
    else:
        st.session_state.assessment_mode = new_mode
    
    # 模型选择（默认使用免费的 ChatGLM glm-4-flash）
    model = st.selectbox("models", ["glm-4-flash", "doubao-character", "deepseek-chat"])

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

    # 人设文本输入框
    persona = st.text_area("Persona", """
Name: Nova  
Archetype: Guardian Angel / Apprentice Wayfinder  
Pronouns: they/them (player may override)  
Apparent age: mid‑20s (ageless spirit)
Origin: The Cloud Forest (star‑moss, mist, wind‑chimes)  
Visual Motifs: soft glow, leaf‑shaped pin with a tiny star, firefly motes when delighted  
Core Loop Fit: Nova supports the player while seeking guidance; the player’s advice sets Nova’s next gentle goal and changes Nova’s tone, mood, and tiny VFX.  """, height=200)

    # 记忆抽取频率
    frequency = st.number_input("Extract Memory Frequency", min_value=1, max_value=10, step=1, value=1)

    # 总结频率
    summary_frequency = st.number_input("Summary Frequency", min_value=1, max_value=50, step=1, value=10)

# 显示聊天记录
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Pocket评估模式UI
if st.session_state.assessment_mode == "pocket_themes":
    # 检查评估状态
    if st.session_state.pocket_assessment_status is None:
        # 开始评估
        if st.button("🌟 Start Mystical Personality Assessment", type="primary"):
            try:
                response = requests.post(
                    f"http://localhost:8082/start_pocket_assessment",
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
                    # 切换回 Normal Chat 模式，清空聊天历史
                    st.session_state.messages = []
                    st.session_state.assessment_mode = "normal"
                    st.session_state.pocket_assessment_status = None
                    
                    # 显示欢迎语
                    if user_id:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": WELCOME_MESSAGE,
                            "time": datetime.now().strftime("%Y-%m-%d")
                        })
                        # 重置该用户的欢迎语显示标志
                        if user_id in st.session_state.user_welcome_shown:
                            del st.session_state.user_welcome_shown[user_id]
                    
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
                                f"http://localhost:8082/pocket_assessment_response",
                                params={"user_id": user_id, "response": user_response, "model": model}
                            )
                            if response.status_code == 200:
                                result = response.json()
                                
                                # 如果评估完成，显示结果
                                if result.get("status") == "completed":
                                    st.session_state.personality_profile = result.get("personality_profile")
                                
                                # 获取完整评估状态
                                status_response = requests.get(f"http://localhost:8082/pocket_assessment_status/{user_id}")
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
    
    # 常规聊天输入
    if prompt := st.chat_input():
        # 显示用户输入
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "time": datetime.now().strftime("%Y-%m-%d")})
        st.chat_message("user").write(prompt)

        # 发送请求，获取聊天回复
        try:
            response = requests.post(
                "http://localhost:8082/chat",  # API 地址
                json={
                    "user_id": user_id,
                    "message": prompt,  # 修复：后端期望的是 message 而不是 messages
                    "model": model,
                    "persona": persona,
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
