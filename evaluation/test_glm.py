#!/usr/bin/env python3
"""
TelegramBot Performance Test - Speed and Response Time Evaluation
测试不同 LLM 模型的响应速度和性能

支持两种测试模式：
1. 纯 LLM 测试：直接调用 LLM，测试纯粹的语言模型响应速度
2. 完整系统测试：通过 TelegramBot API，包含记忆、场景、情感检测等功能
"""

import asyncio
import os
import sys
import json
import time
import statistics
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import requests

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(project_root))  # Go up one level to access mem module

# Available models to test
AVAILABLE_MODELS = [
    "glm-4-flash"
  
]

# Model configurations (from server/chat_server.py)
MODEL_CONFIGS = {
    "glm-4-flash": {
        "api_key": "0031af15104f4a49bb70e1e6bf1e4d72.nybmwLU1gf7U41fh",
        "model": "glm-4-flash",
        "openai_base_url": "https://open.bigmodel.cn/api/paas/v4/"
    }
   
}
# Test cases for performance testing (simple and diverse)
PERFORMANCE_TEST_CASES = [
    "Hello, how are you?",
    "What's the weather like today?",
    "Tell me a joke.",
    "I'm feeling stressed. Can you help?",
    "What are your thoughts on artificial intelligence?",
    "Can you write a short poem?",
    "What's 2+2?",
    "How do I learn to code?",
    "What's your favorite color?",
    "Tell me about yourself."
]


@dataclass
class PerformanceTestResult:
    """Performance test result for a single request"""
    model: str
    test_case: str
    response_time: float  # in seconds
    response_length: int  # character count
    success: bool
    error: Optional[str] = None


@dataclass
class ModelPerformanceSummary:
    """Summary of performance for a model"""
    model: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    average_response_time: float
    median_response_time: float
    min_response_time: float
    max_response_time: float
    std_deviation: float
    average_response_length: int
    total_tokens_per_second: Optional[float] = None


class PerformanceTester:
    """Performance tester for TelegramBot models"""
    
    def __init__(self, api_url: str = "http://localhost:8082", test_mode: str = "llm_only"):
        """
        Args:
            api_url: TelegramBot API URL (for full_system mode)
            test_mode: "llm_only" for direct LLM calls, "full_system" for TelegramBot API
        """
        self.api_url = api_url
        self.test_mode = test_mode
        self.default_persona = """
Name: Nova  
Archetype: Guardian Angel / Apprentice Wayfinder  
Pronouns: they/them
Apparent age: mid‑20s (ageless spirit)
Origin: The Cloud Forest (star‑moss, mist, wind‑chimes)  
Visual Motifs: soft glow, leaf‑shaped pin with a tiny star, firefly motes when delighted  
"""
    
    async def test_llm_only(self, model: str, test_case: str) -> PerformanceTestResult:
        """Test direct LLM call (bypass TelegramBot system)"""
        try:
            from mem.com.factory import LlmFactory
            
            if model not in MODEL_CONFIGS:
                return PerformanceTestResult(
                    model=model,
                    test_case=test_case,
                    response_time=0.0,
                    response_length=0,
                    success=False,
                    error=f"Model {model} not found in MODEL_CONFIGS"
                )
            
            config = MODEL_CONFIGS[model]
            llm = LlmFactory.create("openai", config)
            
            # Simple system prompt for testing
            system_prompt = "You are a helpful AI assistant. Respond naturally and concisely."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": test_case}
            ]
            
            start_time = time.time()
            response = await asyncio.to_thread(llm.generate_response, messages=messages, response_format=None)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_length = len(response)
            
            return PerformanceTestResult(
                model=model,
                test_case=test_case,
                response_time=response_time,
                response_length=response_length,
                success=True
            )
            
        except Exception as e:
            response_time = time.time() - start_time if 'start_time' in locals() else 0.0
            return PerformanceTestResult(
                model=model,
                test_case=test_case,
                response_time=response_time,
                response_length=0,
                success=False,
                error=str(e)
            )
    
    async def test_full_system(self, model: str, test_case: str) -> PerformanceTestResult:
        """Test through TelegramBot API (full system with memory, emotions, etc.)"""
        payload = {
            "user_id": "test_glm_user4",
            "message": test_case,
            "model": model,
            "persona": self.default_persona,
            "frequency": 1,
            "summary_frequency": 10,
            "scene": "default",
            "assessment_mode": "normal"
        }
        
        start_time = time.time()
        success = False
        response_length = 0
        error = None
        
        try:
            response = requests.post(
                f"{self.api_url}/chat",
                json=payload,
                timeout=60
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                json_response = response.json()
                bot_reply = json_response.get("response", "")
                response_length = len(bot_reply)
                success = True
            else:
                error = f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            error = "Request timeout (60s)"
        except requests.exceptions.ConnectionError:
            response_time = time.time() - start_time
            error = "Connection error"
        except Exception as e:
            response_time = time.time() - start_time
            error = str(e)
        
        return PerformanceTestResult(
            model=model,
            test_case=test_case,
            response_time=response_time,
            response_length=response_length,
            success=success,
            error=error
        )
    
    async def test_single_request(self, model: str, test_case: str) -> PerformanceTestResult:
        """Test a single request and measure response time"""
        if self.test_mode == "llm_only":
            return await self.test_llm_only(model, test_case)
        else:
            return await self.test_full_system(model, test_case)
    
    async def test_model(self, model: str, test_cases: List[str], num_runs: int = 3) -> List[PerformanceTestResult]:
        """Test a model with multiple test cases, each run multiple times"""
        results = []
        
        print(f"\n测试模型: {model}")
        print(f"  测试用例数: {len(test_cases)}")
        print(f"  每个用例运行次数: {num_runs}")
        print(f"  总请求数: {len(test_cases) * num_runs}")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n  测试用例 {i}/{len(test_cases)}: {test_case[:50]}...")
            
            for run in range(num_runs):
                print(f"    运行 {run + 1}/{num_runs}...", end=" ", flush=True)
                result = await self.test_single_request(model, test_case)
                results.append(result)
                
                if result.success:
                    print(f"✓ {result.response_time:.2f}s ({result.response_length} chars)")
                else:
                    print(f"✗ 失败: {result.error}")
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.5)
        
        return results
    
    def calculate_model_summary(self, model: str, results: List[PerformanceTestResult]) -> ModelPerformanceSummary:
        """Calculate performance summary for a model"""
        successful_results = [r for r in results if r.success and r.model == model]
        failed_results = [r for r in results if not r.success and r.model == model]
        
        if not successful_results:
            return ModelPerformanceSummary(
                model=model,
                total_tests=len(results),
                successful_tests=0,
                failed_tests=len(failed_results),
                average_response_time=0.0,
                median_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                std_deviation=0.0,
                average_response_length=0
            )
        
        response_times = [r.response_time for r in successful_results]
        response_lengths = [r.response_length for r in successful_results]
        
        return ModelPerformanceSummary(
            model=model,
            total_tests=len(results),
            successful_tests=len(successful_results),
            failed_tests=len(failed_results),
            average_response_time=statistics.mean(response_times),
            median_response_time=statistics.median(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            std_deviation=statistics.stdev(response_times) if len(response_times) > 1 else 0.0,
            average_response_length=int(statistics.mean(response_lengths))
        )


async def run_performance_test(models: List[str] = None, test_cases: List[str] = None, 
                                num_runs: int = 3, test_mode: str = "llm_only"):
    """Run performance test for multiple models
    
    Args:
        models: List of models to test
        test_cases: List of test cases
        num_runs: Number of runs per test case
        test_mode: "llm_only" for direct LLM calls, "full_system" for TelegramBot API
    """
    
    if models is None:
        models = AVAILABLE_MODELS
    
    if test_cases is None:
        test_cases = PERFORMANCE_TEST_CASES
    
    print("=" * 80)
    print("TELEGRAMBOT 性能测试 - 响应速度和时间评估")
    print("=" * 80)
    
    mode_desc = "纯 LLM 测试（直接调用语言模型）" if test_mode == "llm_only" else "完整系统测试（包含记忆、场景、情感检测等）"
    
    print(f"\n测试配置:")
    print(f"  测试模式: {test_mode} - {mode_desc}")
    print(f"  测试模型: {', '.join(models)}")
    print(f"  测试用例数: {len(test_cases)}")
    print(f"  每用例运行次数: {num_runs}")
    if test_mode == "full_system":
        print(f"  API地址: http://localhost:8082")
    
    tester = PerformanceTester(test_mode=test_mode)
    
    all_results = []
    model_summaries = []
    
    # Test each model
    for model in models:
        print(f"\n{'=' * 80}")
        print(f"开始测试模型: {model}")
        print(f"{'=' * 80}")
        
        try:
            results = await tester.test_model(model, test_cases, num_runs)
            all_results.extend(results)
            
            summary = tester.calculate_model_summary(model, results)
            model_summaries.append(summary)
            
        except KeyboardInterrupt:
            print("\n\n测试被用户中断")
            break
        except Exception as e:
            print(f"\n测试模型 {model} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    # Generate comprehensive report
    print(f"\n{'=' * 80}")
    print("性能测试总结报告")
    print(f"{'=' * 80}")
    
    if model_summaries:
        print(f"\n模型对比:")
        print(f"{'模型':<20} {'成功率':<10} {'平均响应(s)':<15} {'中位数(s)':<15} {'最小(s)':<10} {'最大(s)':<10} {'平均长度':<10}")
        print("-" * 100)
        
        for summary in model_summaries:
            success_rate = (summary.successful_tests / summary.total_tests * 100) if summary.total_tests > 0 else 0
            print(f"{summary.model:<20} {success_rate:>6.1f}%   "
                  f"{summary.average_response_time:>10.2f}    "
                  f"{summary.median_response_time:>10.2f}    "
                  f"{summary.min_response_time:>8.2f}    "
                  f"{summary.max_response_time:>8.2f}    "
                  f"{summary.average_response_length:>8}")
        
        # Detailed statistics for each model
        print(f"\n详细统计:")
        for summary in model_summaries:
            print(f"\n{summary.model}:")
            print(f"  总测试数: {summary.total_tests}")
            print(f"  成功: {summary.successful_tests}, 失败: {summary.failed_tests}")
            if summary.successful_tests > 0:
                print(f"  响应时间:")
                print(f"    平均: {summary.average_response_time:.2f}s")
                print(f"    中位数: {summary.median_response_time:.2f}s")
                print(f"    最小: {summary.min_response_time:.2f}s")
                print(f"    最大: {summary.max_response_time:.2f}s")
                print(f"    标准差: {summary.std_deviation:.2f}s")
                print(f"  响应长度:")
                print(f"    平均: {summary.average_response_length} 字符")
        
        # Ranking
        successful_summaries = [s for s in model_summaries if s.successful_tests > 0]
        if successful_summaries:
            print(f"\n速度排名 (按平均响应时间):")
            sorted_summaries = sorted(successful_summaries, key=lambda x: x.average_response_time)
            for i, summary in enumerate(sorted_summaries, 1):
                print(f"  {i}. {summary.model}: {summary.average_response_time:.2f}s")
    
    # Save results
    output_file = f"results/performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    output_data = {
        "test_config": {
            "models": models,
            "test_cases": test_cases,
            "num_runs_per_case": num_runs,
            "timestamp": datetime.now().isoformat()
        },
        "summaries": [asdict(s) for s in model_summaries],
        "detailed_results": [asdict(r) for r in all_results]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")
    print("性能测试完成!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TelegramBot 性能测试工具")
    parser.add_argument("--models", nargs="+", default=AVAILABLE_MODELS,
                       help="要测试的模型列表 (默认: 所有可用模型)")
    parser.add_argument("--num-runs", type=int, default=3,
                       help="每个测试用例的运行次数 (默认: 3)")
    parser.add_argument("--test-cases", type=int, default=None,
                       help="使用前N个测试用例 (默认: 全部)")
    parser.add_argument("--mode", choices=["llm_only", "full_system"], default="llm_only",
                       help="测试模式: llm_only=纯LLM测试(推荐), full_system=完整系统测试")
    
    args = parser.parse_args()
    
    test_cases = PERFORMANCE_TEST_CASES
    if args.test_cases:
        test_cases = test_cases[:args.test_cases]
    
    asyncio.run(run_performance_test(
        models=args.models,
        test_cases=test_cases,
        num_runs=args.num_runs,
        test_mode=args.mode
    ))

