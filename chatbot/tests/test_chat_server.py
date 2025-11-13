import json
import unittest
import uuid
import time
from datetime import datetime

import requests

class TestChatServerRequests(unittest.TestCase):
    def setUp(self):
        """测试前的初始化工作"""
        # 服务基础URL
        self.base_url = "http://localhost:8000"
        # 生成唯一的用户ID用于测试
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        # 初始化测试数据
        self.test_message = "你好，我是测试用户"
        self.test_model = "doubao-character"
        # 确保测试环境干净
        self._cleanup_test_data()
    
    def tearDown(self):
        """测试后的清理工作"""
        # 清理测试数据
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """清理测试数据"""
        try:
            # 清除测试用户的聊天历史
            requests.delete(f"{self.base_url}/chat_history/{self.user_id}")
        except Exception as e:
            # 如果服务未启动或其他原因导致清理失败，忽略错误
            pass
    
    def test_chat_endpoint(self):
        """测试聊天接口 - POST /chat"""
        # 准备请求数据
        data = {
            "user_id": self.user_id,
            "message": self.test_message,
            "model": self.test_model,
            "persona": "",
            "frequency": 1,
            "summary_frequency": 10
        }
        
        # 发送请求
        response = requests.post(f"{self.base_url}/chat", json=data)
        
        # 验证响应状态码
        self.assertEqual(response.status_code, 200, f"聊天接口请求失败，状态码：{response.status_code}")
        
        # 验证响应内容
        response_data = response.json()
        self.assertIn("response", response_data, "聊天响应中缺少response字段")
        self.assertIn("used_memory", response_data, "聊天响应中缺少used_memory字段")
        
        # 打印响应内容（可选，用于调试）
        print(f"聊天接口响应：{response_data}")
    
    def test_get_chat_history(self):
        """测试获取聊天历史接口 - GET /chat_history/{user_id}"""
        # 首先发送一条消息以确保有聊天历史
        self._send_test_message()
        
        # 发送获取聊天历史的请求
        response = requests.get(f"{self.base_url}/chat_history/{self.user_id}")
        
        # 验证响应状态码
        self.assertEqual(response.status_code, 200, f"获取聊天历史接口请求失败，状态码：{response.status_code}")
        
        # 验证响应内容
        response_data = response.json()
        self.assertIn("user_id", response_data, "聊天历史响应中缺少user_id字段")
        self.assertIn("chat_history", response_data, "聊天历史响应中缺少chat_history字段")
        self.assertEqual(response_data["user_id"], self.user_id, "返回的用户ID与请求的不一致")
        self.assertIsInstance(response_data["chat_history"], list, "chat_history字段应为列表类型")
        self.assertGreater(len(response_data["chat_history"]), 0, "聊天历史为空")
        
        # 打印响应内容（可选，用于调试）
        print(f"聊天历史接口响应：{response_data}")
    
    def test_get_all_memories(self):
        """测试获取所有记忆接口 - GET /memories/{user_id}"""
        # 首先发送几条消息以确保有记忆数据
        self._send_test_message()
        # 等待记忆处理完成
        time.sleep(1)
        
        # 发送获取所有记忆的请求
        response = requests.get(f"{self.base_url}/memories/{self.user_id}")
        
        # 验证响应状态码
        self.assertEqual(response.status_code, 200, f"获取记忆接口请求失败，状态码：{response.status_code}")
        
        # 验证响应内容
        response_data = response.json()
        self.assertIn("user_id", response_data, "记忆响应中缺少user_id字段")
        self.assertIn("profile", response_data, "记忆响应中缺少profile字段")
        self.assertIn("facts", response_data, "记忆响应中缺少facts字段")
        self.assertIn("style", response_data, "记忆响应中缺少style字段")
        self.assertIn("commitments", response_data, "记忆响应中缺少commitments字段")
        self.assertEqual(response_data["user_id"], self.user_id, "返回的用户ID与请求的不一致")
        
        # 打印响应内容（可选，用于调试）
        print(f"记忆接口响应：{response_data}")
    
    def test_clear_chat_history(self):
        """测试清除聊天历史接口 - DELETE /chat_history/{user_id}"""
        # 首先发送一条消息以确保有聊天历史
        self._send_test_message()
        
        # 发送清除聊天历史的请求
        response = requests.delete(f"{self.base_url}/chat_history/{self.user_id}")
        
        # 验证响应状态码
        self.assertEqual(response.status_code, 200, f"清除聊天历史接口请求失败，状态码：{response.status_code}")
        
        # 验证响应内容
        response_data = response.json()
        self.assertIn("message", response_data, "清除聊天历史响应中缺少message字段")
        self.assertEqual(response_data["message"], "Chat history cleared successfully", "清除聊天历史的消息不正确")
        
        # 验证聊天历史确实被清除
        history_response = requests.get(f"{self.base_url}/chat_history/{self.user_id}")
        history_data = history_response.json()
        self.assertEqual(len(history_data["chat_history"]), 0, "聊天历史未被成功清除")
        
        # 打印响应内容（可选，用于调试）
        print(f"清除聊天历史接口响应：{response_data}")
    
    def test_home_redirect(self):
        """测试首页重定向接口 - GET /"""
        # 发送请求并允许重定向
        response = requests.get(f"{self.base_url}/", allow_redirects=True)
        
        # 验证最终状态码
        self.assertEqual(response.status_code, 200, f"首页重定向失败，最终状态码：{response.status_code}")
        
        # 验证重定向到文档页面
        self.assertIn("/docs", response.url, "未重定向到文档页面")
        
        # 打印响应URL（可选，用于调试）
        print(f"首页重定向最终URL：{response.url}")
    '''
    def test_chat_with_unsupported_model(self):
        """测试使用不支持的模型"""
        # 准备请求数据，使用不支持的模型
        data = {
            "user_id": self.user_id,
            "message": self.test_message,
            "model": "unsupported-model",
            "persona": "",
            "frequency": 1,
            "summary_frequency": 10
        }
        
        # 发送请求
        response = requests.post(f"{self.base_url}/chat", json=data)
        
        # 验证错误响应状态码
        self.assertEqual(response.status_code, 400, f"使用不支持的模型时，应返回400状态码，实际返回：{response.status_code}")
        
        # 验证错误响应内容
        response_data = response.json()
        self.assertIn("detail", response_data, "错误响应中缺少detail字段")
        self.assertTrue("unsupported-model" in response_data["detail"], "错误消息中应包含不支持的模型名称")
        
        # 打印响应内容（可选，用于调试）
        print(f"使用不支持的模型响应：{response_data}")
    '''
    def _send_test_message(self, message=None):
        """发送测试消息的辅助方法"""
        data = {
            "user_id": self.user_id,
            "message": message or self.test_message,
            "model": self.test_model,
            "persona": "",
            "frequency": 1,
            "summary_frequency": 10
        }
        response = requests.post(f"{self.base_url}/chat", json=data)
        return response.json()

if __name__ == "__main__":
    # 运行测试
    unittest.main()