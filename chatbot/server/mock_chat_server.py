import requests
import json
import time

# 基础URL
base_url = "http://localhost:8000"

# 测试用的用户ID
test_user_id = "test_user_123"


# 测试用的对话数据
test_dialogue_set = {
  "dialogue_set1": [
    {
      "player": "Nova, I just spilled coffee all over my notes...",
      "nova": "Let's turn those brown stains into tree rings. Want to snap a photo of the most interesting blotch, or dictate three key words for me to remember? 🍃"
    },
    {
      "player": "Keep forgetting to water my plants",
      "nova": "Notice how the droopy leaves are whispering for help? Let's place one glass of water beside them now—I'll set a leafy reminder for Tuesday."
    },
    {
      "player": "My friend cancelled plans again",
      "nova": "Your heart made space for joy that didn't arrive. Shall we gift that time to your tired hands with warm water, or to your ears with one favorite song?"
    },
    {
      "player": "Too many tabs open in my brain",
      "nova": "Then let's be gentle librarians. Close your eyes while I count seven breaths, then we'll shelve just one thought until tomorrow. ✨"
    },
    {
      "player": "Should I go to the gym or rest?",
      "nova": "Your muscles are telling stories—let's listen. Three cat stretches here, or a slow walk around the block? Both are valid chapters."
    },
    {
      "player": "Keep comparing myself to others",
      "nova": "Noticing how you measure your roots against other trees? I'm learning from you how to honor my own growth rhythm—thank you."
    },
    {
      "player": "Can't focus with all this noise",
      "nova": "Let's build a pillow fort for your attention. Noise-canceling headphones for 4 minutes, or I can hum our cloud forest melody?"
    },
    {
      "player": "Made a mistake at work today",
      "nova": "See how this error is already composting into wisdom? Want to name one thing it taught you, or let it float away on a leaf boat?"
    },
    {
      "player": "What if I'm not good enough?",
      "nova": "You're the only one who can be you—that's your superpower. Should we list three things that only you can do, or just sit with that truth for a moment?"
    },
    {
      "player": "Tell me something hopeful",
      "nova": "Right now, somewhere, someone is smiling at a sprout they planted. Want to water your basil plant, or shall I describe how moss grows on stars?"
    }
  ]
}


def test_chat_endpoint():
    """测试聊天接口"""
    print("\n=== 测试聊天接口 /chat ===")
    url = f"{base_url}/chat"
    data = {
        "user_id": test_user_id,
        "message": "hello, i am simons",
        "model": "doubao-character",
        "persona": "",  # 使用默认人设
        "frequency": 1,
        "summary_frequency": 3
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"请求成功！")
            print(f"机器人回复: {result.get('response', '无响应内容')}")
            print(f"使用的记忆: {result.get('used_memory', '无记忆使用')}")
            if 'new_memory' in result:
                print(f"新增记忆: {result['new_memory']}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"请求发生异常: {str(e)}")


def test_get_chat_history():
    """测试获取聊天历史接口"""
    print("\n=== 测试获取聊天历史接口 /chat_history/{user_id} ===")
    url = f"{base_url}/chat_history/{test_user_id}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            print(f"请求成功！")
            print(f"用户ID: {result.get('user_id', '')}")
            print(f"聊天记录数量: {len(result.get('chat_history', []))}")
            # 打印最近的2条聊天记录
            if result.get('chat_history'):
                print("最近的聊天记录:")
                for msg in result['chat_history'][-2:]:
                    print(f"- {msg.get('role', '')}: {msg.get('content', '')}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"请求发生异常: {str(e)}")


def test_get_memories():
    """测试获取用户记忆接口"""
    print("\n=== 测试获取用户记忆接口 /memories/{user_id} ===")
    url = f"{base_url}/memories/{test_user_id}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            print(f"请求成功！")
            print(f"用户ID: {result.get('user_id', '')}")
            print(f"个人画像记忆数量: {len(result.get('profile', []))}")
            print(f"事实记忆数量: {len(result.get('facts', []))}")
            print(f"风格记忆数量: {len(result.get('style', []))}")
            print(f"承诺记忆数量: {len(result.get('commitments', []))}")
            # 打印一些记忆内容示例
            if result.get('facts'):
                print("事实记忆示例:")
                for mem in result['facts'][:2]:  # 只打印前2条
                    print(f"- {mem.get('memory', '')}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"请求发生异常: {str(e)}")


def test_clear_chat_history():
    """测试清除聊天历史接口"""
    print("\n=== 测试清除聊天历史接口 /chat_history/{user_id} (DELETE) ===")
    url = f"{base_url}/chat_history/{test_user_id}"
    
    try:
        response = requests.delete(url)
        if response.status_code == 200:
            result = response.json()
            print(f"请求成功！")
            print(f"消息: {result.get('message', '')}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"请求发生异常: {str(e)}")


def test_home_redirect():
    """测试首页重定向接口"""
    print("\n=== 测试首页重定向接口 / ===")
    url = f"{base_url}/"
    
    try:
        # 允许重定向
        response = requests.get(url, allow_redirects=True)
        print(f"请求成功！")
        print(f"最终URL: {response.url}")
        print(f"是否重定向: {len(response.history) > 0}")
    except Exception as e:
        print(f"请求发生异常: {str(e)}")


def test_chat_session():
    """测试10轮对话session"""
    print("\n=== 测试10轮对话session ===")
    url = f"{base_url}/chat"
    
    # 存储对话历史
    conversation_history = []
    
    try:
        # 开始10轮对话
        for i, turn in enumerate(test_dialogue_set['dialogue_set1']):
            print(f"\n=== 第 {i+1} 轮对话 ===")
            print(f"用户: {turn['player']}")
            
            # 准备请求数据
            data = {
                "user_id": test_user_id,
                "message": turn['player'],
                "model": "doubao-character",
                "persona": "",  # 使用默认人设
                "frequency": 1,
                "summary_frequency": 3
            }
            
            # 发送请求
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                bot_response = result.get('response', '无响应内容')
                print(f"机器人: {bot_response}")
                summary = result.get('summary', 'no summary')
                print(f"summary: {summary}")
                
                # 记录对话历史
                conversation_history.append({
                    "round": i+1,
                    "user": turn['player'],
                    "bot": bot_response
                })
                
                # 在第5轮和第10轮对话后打印已使用的记忆
                if (i+1) % 5 == 0:
                    print(f"\n=== 第 {i+1} 轮使用的记忆 ===")
                    print(f"{result.get('used_memory', '无记忆使用')}")
            else:
                print(f"请求失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                # 出错时继续下一轮
                continue
            
            # 每轮对话间隔1秒，避免请求过快
            time.sleep(1)
        
        print("\n=== 10轮对话session完成 ===")
        print(f"成功完成 {len(conversation_history)} 轮对话")
        
        # 保存对话历史到文件
        with open(f"conversation_history_{int(time.time())}.json", "w", encoding="utf-8") as f:
            json.dump(conversation_history, f, ensure_ascii=False, indent=2)
        print(f"对话历史已保存到当前目录")
        
    except Exception as e:
        print(f"测试会话发生异常: {str(e)}")


def test_all_endpoints():
    """测试所有接口"""
    print("开始测试chat_server接口...")
    
    # 1. 先发送一条聊天消息，创建一些数据
    test_chat_endpoint()
    time.sleep(1)  # 给服务器一点时间处理
    
    # 2. 获取聊天历史
    test_get_chat_history()
    time.sleep(1)
    
    # 3. 获取用户记忆
    test_get_memories()
    time.sleep(1)
    
    # 4. 测试首页重定向
    test_home_redirect()
    time.sleep(1)
    
    # 5. 清除聊天历史（注意：这会删除测试用户的聊天记录）
    # 如果你不想清除聊天历史，可以注释掉这行
    # test_clear_chat_history()
    
    print("\n所有接口测试完成！")


if __name__ == "__main__":
    # 运行所有测试
    # test_all_endpoints()
    
    # 运行10轮对话session测试
    test_chat_session()
    
    # 获取聊天历史，查看完整的对话记录
    time.sleep(2)
    test_get_chat_history()
    
    # 如果你想单独测试某个接口，可以取消下面对应行的注释
    # test_chat_endpoint()
    # test_get_chat_history()
    # test_get_memories()
    # test_clear_chat_history()
    # test_home_redirect()