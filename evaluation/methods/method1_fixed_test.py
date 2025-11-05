"""
Method 1: Fixed Test Set Evaluation
Use fixed user inputs to evaluate TelegramBot response quality
Aligned with pocket-souls-agents/evaluation
"""

import json
import asyncio
import time
import random
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from methods.llm_judge import LLMJudge, EvaluationResult
from methods.telegrambot_interface import TelegramBotInterface
from config.evaluation_config import TEST_CONFIG


@dataclass
class FixedTestCase:
    """Fixed test case data structure"""
    id: str
    category: str
    user_input: str
    context: List[Dict]


@dataclass
class FixedTestResult:
    """Fixed test result"""
    test_case: FixedTestCase
    bot_response: str
    evaluation: EvaluationResult
    timestamp: str


class FixedTestEvaluator:
    """Fixed test set evaluator"""

    def __init__(self, openai_api_key: str):
        self.judge = LLMJudge(openai_api_key)
        self.telegrambot = TelegramBotInterface()
        self.config = TEST_CONFIG["fixed_test"]

    async def load_test_cases(self, test_cases_file: str) -> List[FixedTestCase]:
        """加载测试用例"""
        try:
            with open(test_cases_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            test_cases = []
            for item in data:
                test_case = FixedTestCase(
                    id=item["id"],
                    category=item["category"],
                    user_input=item["user_input"],
                    context=item.get("context", [])
                )
                test_cases.append(test_case)

            print(f"成功加载 {len(test_cases)} 个测试用例")
            return test_cases

        except Exception as e:
            print(f"加载测试用例失败: {e}")
            return []

    async def run_single_test(self, test_case: FixedTestCase, max_retries: int = 3) -> FixedTestResult:
        """运行单个测试用例并带有重试机制确保获得真实的 TelegramBot 回复"""
        from datetime import datetime

        print(f"运行测试用例: {test_case.id} - {test_case.user_input}")

        # 获取 TelegramBot 回复（get_response 内部已有重试机制）
        bot_response = await self.telegrambot.get_response(
            test_case.user_input,
            max_retries
        )
        print(f"有效的 TelegramBot 回复: {bot_response[:100]}...")

        # 重试 LLM 评估
        for eval_attempt in range(max_retries + 1):
            try:
                evaluation = await self.judge.evaluate_single_response(
                    test_case.user_input,
                    bot_response,
                    test_case.context
                )

                # 检查评估是否成功（不是备用结果）
                if not self._is_fallback_evaluation(evaluation):
                    print(f"有效评估: {evaluation.overall_score}/10")
                    break
                else:
                    if eval_attempt < max_retries:
                        print(f"警告: LLM 评估失败，重试 (尝试 {eval_attempt + 1}/{max_retries + 1})")
                        await asyncio.sleep(2)
                        continue
                    else:
                        raise Exception("LLM 评估重试后仍失败")

            except Exception as e:
                if eval_attempt < max_retries:
                    print(f"警告: 评估错误，重试: {e}")
                    await asyncio.sleep(2)
                    continue
                else:
                    raise Exception(f"评估在 {max_retries} 次重试后失败: {e}")

        return FixedTestResult(
            test_case=test_case,
            bot_response=bot_response,
            evaluation=evaluation,
            timestamp=datetime.now().isoformat()
        )

    def _is_fallback_evaluation(self, evaluation) -> bool:
        """检查这是否是备用评估结果"""
        return (
            "LLM 评估失败" in str(evaluation.suggestions) or
            "评估失败，使用默认分数" in str(evaluation.explanations.values()) or
            evaluation.overall_score == 5.0 and len(set(evaluation.scores.values())) == 1
        )

    async def run_batch_test(self, test_cases: List[FixedTestCase]) -> List[FixedTestResult]:
        """批量运行测试"""
        results = []
        batch_size = self.config["batch_size"]

        for i in range(0, len(test_cases), batch_size):
            batch = test_cases[i:i + batch_size]
            print(f"\n处理批次 {i//batch_size + 1}/{(len(test_cases)-1)//batch_size + 1}")

            # 并发处理批次中的测试用例
            batch_tasks = [self.run_single_test(test_case) for test_case in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"测试失败: {result}")
                else:
                    results.append(result)

            # 批次之间的短暂休息，避免 API 限流
            if i + batch_size < len(test_cases):
                await asyncio.sleep(1)

        return results

    async def evaluate_test_file(self, test_cases_file: str) -> Dict:
        """评估整个测试文件"""
        # 加载测试用例
        test_cases = await self.load_test_cases(test_cases_file)
        if not test_cases:
            return {"error": "无法加载测试用例"}

        # 运行测试
        results = await self.run_batch_test(test_cases)

        # 过滤失败的测试用例
        valid_results = []
        failed_results = []

        for result in results:
            if (result.evaluation.overall_score == 5.0 and
                "LLM 评估失败" in str(result.evaluation.suggestions)):
                failed_results.append(result)
                print(f"跳过失败的测试: {result.test_case.id}")
            else:
                valid_results.append(result)

        print(f"\n有效测试: {len(valid_results)}, 失败测试: {len(failed_results)}")

        # 生成统计报告（仅基于有效结果）
        report = self._generate_report(valid_results)
        report['failed_tests'] = len(failed_results)
        report['valid_tests'] = len(valid_results)

        return {
            "summary": report,
            "results": [asdict(result) for result in valid_results],
            "failed_results": [asdict(result) for result in failed_results]
        }

    async def retry_failed_tests(self, failed_results: List[FixedTestResult], max_retries: int = 3) -> List[FixedTestResult]:
        """重试失败的测试用例"""
        print(f"\n重试 {len(failed_results)} 个失败的测试...")

        retry_results = []
        for result in failed_results:
            test_case = result.test_case
            print(f"重试: {test_case.id} - {test_case.user_input}")

            success = False
            for attempt in range(max_retries):
                try:
                    # 重新运行单个测试
                    new_result = await self.run_single_test(test_case)

                    # 检查是否成功
                    if (new_result.evaluation.overall_score != 5.0 or
                        "LLM 评估失败" not in str(new_result.evaluation.suggestions)):
                        retry_results.append(new_result)
                        print(f"重试成功: {test_case.id} (尝试 {attempt + 1})")
                        success = True
                        break
                    else:
                        print(f"重试仍失败: {test_case.id} (尝试 {attempt + 1})")

                except Exception as e:
                    print(f"重试错误: {test_case.id} (尝试 {attempt + 1}): {e}")

                # 等待后重试
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)

            if not success:
                print(f"所有重试都失败: {test_case.id}")

        print(f"成功重试 {len(retry_results)}/{len(failed_results)} 个测试")
        return retry_results

    def _generate_report(self, results: List[FixedTestResult]) -> Dict:
        """生成评估报告"""
        if not results:
            return {"error": "无测试结果"}

        # 计算每个维度的平均分数
        dimension_scores = {}
        for dim in ["logic", "fluency", "engagement", "character_consistency",
                   "action_description", "emotional_expression", "game_immersion"]:
            scores = [result.evaluation.scores.get(dim, 0) for result in results]
            dimension_scores[dim] = {
                "average": round(sum(scores) / len(scores), 2),
                "min": min(scores),
                "max": max(scores)
            }

        # 计算总体分数
        overall_scores = [result.evaluation.overall_score for result in results]
        overall_average = round(sum(overall_scores) / len(overall_scores), 2)

        # 按类别统计
        category_stats = {}
        for result in results:
            category = result.test_case.category
            if category not in category_stats:
                category_stats[category] = []
            category_stats[category].append(result.evaluation.overall_score)

        for category in category_stats:
            scores = category_stats[category]
            category_stats[category] = {
                "count": len(scores),
                "average": round(sum(scores) / len(scores), 2),
                "min": min(scores),
                "max": max(scores)
            }

        # 收集改进建议
        all_suggestions = []
        for result in results:
            all_suggestions.extend(result.evaluation.suggestions)

        # 统计最常见的建议
        suggestion_counts = {}
        for suggestion in all_suggestions:
            suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1

        top_suggestions = sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_tests": len(results),
            "overall_average": overall_average,
            "dimension_scores": dimension_scores,
            "category_stats": category_stats,
            "top_suggestions": [{"suggestion": s[0], "frequency": s[1]} for s in top_suggestions],
            "score_distribution": {
                "excellent (8.0+)": len([s for s in overall_scores if s >= 8.0]),
                "good (6.0-7.9)": len([s for s in overall_scores if 6.0 <= s < 8.0]),
                "average (4.0-5.9)": len([s for s in overall_scores if 4.0 <= s < 6.0]),
                "poor (<4.0)": len([s for s in overall_scores if s < 4.0])
            }
        }
