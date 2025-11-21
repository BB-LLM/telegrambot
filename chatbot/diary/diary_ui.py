"""Diary UI components for Streamlit frontend"""
import streamlit as st
import requests
from datetime import datetime
from typing import Optional, Dict


def get_user_diary(user_id: str) -> Optional[Dict]:
    """
    从后端API获取用户的日记
    
    Args:
        user_id: 用户ID
        
    Returns:
        日记数据字典，如果未找到返回None
    """
    try:
        response = requests.get(f"http://36.138.179.204:8082/diary/{user_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # 404表示没有日记，这是正常的，返回None
            return None
        else:
            # 其他错误状态码
            st.error(f"Error fetching diary: {response.status_code}")
            try:
                error_detail = response.json().get("detail", "Unknown error")
                st.error(f"Error detail: {error_detail}")
            except:
                pass
            return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"Cannot connect to backend server (8082). Is the server running?")
        return None
    except requests.exceptions.Timeout as e:
        st.error(f"Request timeout. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        return None


def render_diary_card(diary: Dict, date: str, is_today: bool):
    """
    渲染日记卡片
    
    Args:
        diary: 日记数据字典
        date: 日期
        is_today: 是否是今天的日记
    """
    title = diary.get("title", "Today's Reflection")
    body_lines = diary.get("body_lines", [])
    tags = diary.get("tags", [])
    
    # 日期标签
    date_label = "Today" if is_today else f"{date}"
    st.markdown(f"**📔 {date_label}'s Reflection**")
    
    # 标题
    st.markdown(f"### {title}")
    
    # 正文
    for line in body_lines:
        if line.strip():  # 跳过空行
            st.markdown(f"{line.strip()}")
    
    # 标签
    if tags:
        tag_str = " ".join([f"`{tag}`" for tag in tags])
        st.markdown(f"**Tags:** {tag_str}")
    
    st.divider()


def render_diary_sidebar(user_id: str):
    """
    在右侧栏渲染日记组件
    
    Args:
        user_id: 用户ID
    """
    st.markdown("### 📔 Today's Reflection")
    st.divider()
    
    # 获取日记数据
    diary_data = get_user_diary(user_id)
    
    if diary_data:
        diary = diary_data.get("diary", {})
        date = diary_data.get("date", "")
        is_today = diary_data.get("is_today", False)
        
        # 渲染日记卡片
        render_diary_card(diary, date, is_today)
        
        # 显示按钮（可选，后续可以添加功能）
        # ui = diary.get("ui", {})
        # buttons = ui.get("inline_keyboard", [])
        # for button_row in buttons:
        #     cols = st.columns(len(button_row))
        #     for i, button in enumerate(button_row):
        #         with cols[i]:
        #             if st.button(button.get("text", ""), key=f"diary_btn_{i}"):
        #                 # 处理按钮点击
        #                 pass
    else:
        st.info("No diary available yet")
        st.caption("Diary will be generated automatically at 21:00-22:00 daily")
        
        # 可选：手动生成按钮
        if st.button("🔄 Generate Today's Diary", key="generate_diary"):
            with st.spinner("Generating diary..."):
                try:
                    # 调用手动生成接口
                    response = requests.post(
                        f"http://36.138.179.204:8082/diary/generate/{user_id}",
                        timeout=90  # 给足够的时间，因为LLM调用可能需要较长时间
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("success"):
                            st.success("✅ Diary generated successfully! Please refresh the page to view it.")
                            # 自动刷新页面以显示新生成的日记
                            st.rerun()
                        else:
                            st.error(f"Failed to generate diary: {result.get('message', 'Unknown error')}")
                    elif response.status_code == 400:
                        error_detail = response.json().get("detail", "Bad request")
                        st.warning(f"⚠️ {error_detail}")
                    elif response.status_code == 404:
                        st.error("❌ User not found or no chat history available")
                    else:
                        error_detail = response.json().get("detail", "Unknown error") if response.text else "Unknown error"
                        st.error(f"❌ Error generating diary: {error_detail}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend server (8082). Is the server running?")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timeout. The diary generation may take longer. Please try again.")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error: {e}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")

