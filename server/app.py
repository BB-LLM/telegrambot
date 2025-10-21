import requests
import streamlit as st
import uuid
from loguru import logger
from user_agents import parse
from datetime import datetime
from pyvis.network import Network

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


# 显示侧边栏的输入选项
with st.sidebar:
    # user_id
    user_input = st.text_input(label='user_id', placeholder="请输入用户id")
    if not user_input:
        st.warning("请先输入用户id")
    if user_input:
        user_id = user_input
        st.session_state.user_input = user_input
    st.session_state["memories"], st.session_state["relations"] = get_memories(user_id)
    print(f"memories: {st.session_state['memories']}")
    # 模型选择（默认使用免费的 ChatGLM glm-4-flash）
    model = st.selectbox("models", ["glm-4-flash", "doubao-character", "deepseek-v3.1"])

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

# 创建一个简单的知识图谱
net = Network(width="100%", height="500px", notebook=False)

# 用户输入
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
                "summary_frequency": summary_frequency
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
