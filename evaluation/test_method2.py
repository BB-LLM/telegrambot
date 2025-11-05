#!/usr/bin/env python3
"""
Method 2: Dynamic Conversation Evaluation
Use user agent to conduct multi-turn conversations with TelegramBot
Aligned with pocket-souls-agents/evaluation
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Load environment variables
from config.evaluation_config import (
    DYNAMIC_CONVERSATION_CONFIG,
    USER_PERSONAS,
    CONVERSATION_STARTERS
)
from methods.telegrambot_interface import TelegramBotInterface
from methods.user_agent import UserAgent, ConversationSession, ConversationTurn
from methods.llm_judge import LLMJudge


# 完整的方法2实现 - 包含对话生成和评估
async def run_single_conversation(starter_config: Dict, openai_api_key: str):
    """运行单个对话会话"""
    telegrambot = TelegramBotInterface()
    user_agent = UserAgent(openai_api_key)
    judge = LLMJudge(openai_api_key)
    
    persona = starter_config['persona']
    
    print(f"开始对话: {starter_config['topic']}")
    print(f"用户: {persona['name']} ({persona['age']}, {persona['style']})")
    print(f"开场: {persona['starter']}")
    
    session_id = f"{starter_config['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    conversation_history = []
    turns = []
    
    current_user_input = persona['starter']
    
    for round_num in range(1, DYNAMIC_CONVERSATION_CONFIG["conversation_rounds"] + 1):
        print(f"\n轮次 {round_num}:")
        print(f"用户: {current_user_input}")
        
        try:
            # TelegramBot 回复
            bot_response = await telegrambot.send_message(current_user_input)
            print(f"TelegramBot: {bot_response}")
            
            turn = ConversationTurn(
                round_number=round_num,
                user_input=current_user_input,
                bot_response=bot_response,
                timestamp=datetime.now().isoformat()
            )
            turns.append(turn)
            
            conversation_history.append({
                "user": current_user_input,
                "bot": bot_response
            })
            
            # 生成下一轮用户输入
            if round_num < DYNAMIC_CONVERSATION_CONFIG["conversation_rounds"]:
                current_user_input = await user_agent.generate_user_response(
                    persona,
                    conversation_history,
                    bot_response,
                    round_num + 1,
                    DYNAMIC_CONVERSATION_CONFIG
                )
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"轮次 {round_num} 对话失败: {e}")
            break
    
    session = ConversationSession(
        session_id=session_id,
        topic=starter_config['topic'],
        starter=persona['starter'],
        user_persona=f"{persona['name']} - {persona['style']}",
        turns=turns,
        total_rounds=len(turns)
    )
    
    # 6维度评估
    print(f"\n开始6维度评估...")
    conversation_for_evaluation = []
    for turn in turns:
        conversation_for_evaluation.append({"role": "user", "content": turn.user_input})
        conversation_for_evaluation.append({"role": "assistant", "content": turn.bot_response})
    
    try:
        evaluation = await judge.evaluate_conversation(conversation_for_evaluation)
        print(f"评估完成: 总分 {evaluation.overall_score:.2f}/10")
        
        # 将 ConversationSession 转换为字典以便 JSON 序列化
        from dataclasses import asdict
        session_dict = asdict(session)
        
        return {
            "session": session_dict,
            "evaluation": {
                "scores": evaluation.scores,
                "explanations": evaluation.explanations,
                "overall_score": evaluation.overall_score,
                "suggestions": evaluation.suggestions,
                "examples": evaluation.examples
            }
        }
    except Exception as e:
        print(f"评估失败: {e}")
        # 将 ConversationSession 转换为字典以便 JSON 序列化
        from dataclasses import asdict
        session_dict = asdict(session)
        
        return {
            "session": session_dict,
            "evaluation": None,
            "error": str(e)
        }


async def main():
    """主函数"""
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '..', '.env')
    load_dotenv(env_path)
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("错误: 请设置 OPENAI_API_KEY 环境变量")
        return
    
    print(f"\n动态对话评估配置:")
    print(f"  计划对话数: 5 (批次评估)")
    print(f"  动态轮次: {DYNAMIC_CONVERSATION_CONFIG['conversation_rounds']} 轮")
    print(f"  真实 TelegramBot 系统: 已启用")
    print(f"  评估维度: 6 个维度")
    print(f"\n模型配置:")
    print(f"  被测模型: glm-4-flash (TelegramBot)")
    print(f"  用户代理模型: {DYNAMIC_CONVERSATION_CONFIG['user_agent_model']} ({DYNAMIC_CONVERSATION_CONFIG.get('base_url', 'OpenAI')})")
    from config.evaluation_config import LLM_JUDGE_CONFIG
    print(f"  教师模型: {LLM_JUDGE_CONFIG['model']} ({LLM_JUDGE_CONFIG.get('base_url', 'OpenAI')})")
    
    results = []
    
    for i, starter in enumerate(CONVERSATION_STARTERS):
        print(f"\n对话 {i+1}/{len(CONVERSATION_STARTERS)}")
        result = await run_single_conversation(starter, openai_api_key)
        results.append(result)
    
    # 生成总结报告
    print("\n" + "=" * 80)
    print("Final Evaluation Results - Method 2 (Dynamic Conversation)")
    print("=" * 80)
    
    # 统计有效结果
    valid_results = [r for r in results if r.get("evaluation") is not None]
    failed_results = [r for r in results if r.get("evaluation") is None]
    
    print(f"\n对话统计:")
    print(f"  总对话数: {len(results)}")
    print(f"  成功评估: {len(valid_results)}")
    print(f"  评估失败: {len(failed_results)}")
    
    if valid_results:
        # 计算总体平均分
        overall_scores = [r["evaluation"]["overall_score"] for r in valid_results]
        overall_average = sum(overall_scores) / len(overall_scores)
        
        print(f"\n总体平均分: {overall_average:.2f}/10.0")
        
        # 按主题统计
        topic_scores = {}
        for result in valid_results:
            topic = result["session"]["topic"]
            score = result["evaluation"]["overall_score"]
            if topic not in topic_scores:
                topic_scores[topic] = []
            topic_scores[topic].append(score)
        
        print(f"\n按主题统计:")
        for topic, scores in sorted(topic_scores.items()):
            avg = sum(scores) / len(scores)
            print(f"  {topic}: {avg:.2f}/10.0 (共 {len(scores)} 个对话)")
        
        # 维度分数统计
        all_dimension_scores = {}
        dimension_names = ["logic", "fluency", "engagement", "character_consistency", 
                          "action_description", "emotional_expression", "game_immersion"]
        
        for result in valid_results:
            scores = result["evaluation"].get("scores", {})
            for dim in dimension_names:
                if dim in scores:
                    if dim not in all_dimension_scores:
                        all_dimension_scores[dim] = []
                    all_dimension_scores[dim].append(scores[dim])
        
        if all_dimension_scores:
            print(f"\n维度平均分 (7个维度):")
            for dim in dimension_names:
                if dim in all_dimension_scores:
                    scores = all_dimension_scores[dim]
                    avg = sum(scores) / len(scores)
                    min_score = min(scores)
                    max_score = max(scores)
                    print(f"  {dim}: {avg:.2f}/10.0 (min: {min_score}, max: {max_score})")
        
        # 分数分布
        print(f"\n分数分布:")
        excellent_count = sum(1 for s in overall_scores if s >= 8.5)
        good_count = sum(1 for s in overall_scores if 7.5 <= s < 8.5)
        average_count = sum(1 for s in overall_scores if 6.5 <= s < 7.5)
        poor_count = sum(1 for s in overall_scores if s < 6.5)
        
        print(f"  优秀 (8.5+): {excellent_count}")
        print(f"  良好 (7.5-8.4): {good_count}")
        print(f"  一般 (6.5-7.4): {average_count}")
        print(f"  需改进 (<6.5): {poor_count}")
        
        # 评估质量分析
        print(f"\n评估质量分析:")
        if overall_average >= 8.5:
            print("  优秀: TelegramBot在动态对话中表现卓越")
        elif overall_average >= 7.5:
            print("  良好: TelegramBot在动态对话中表现良好，有少量改进空间")
        elif overall_average >= 6.5:
            print("  一般: TelegramBot在动态对话中表现尚可，有明显改进机会")
        elif overall_average >= 5.5:
            print("  中等: TelegramBot满足基本期望，但需要显著改进")
        else:
            print("  需改进: TelegramBot需要在多个方面进行大幅改进")
        
        # 详细建议（如果有关键改进建议）
        all_suggestions = []
        for result in valid_results:
            suggestions = result["evaluation"].get("suggestions", [])
            all_suggestions.extend(suggestions)
        
        if all_suggestions:
            # 统计最常见的建议
            from collections import Counter
            suggestion_counts = Counter(all_suggestions)
            top_suggestions = suggestion_counts.most_common(3)
            
            if top_suggestions:
                print(f"\n最常见改进建议:")
                for i, (suggestion, count) in enumerate(top_suggestions, 1):
                    print(f"  {i}. {suggestion} (出现 {count} 次)")
    
    # 保存结果
    output_file = f"results/method2_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 添加总结到结果
    if valid_results:
        summary = {
            "total_conversations": len(results),
            "successful_evaluations": len(valid_results),
            "failed_evaluations": len(failed_results),
            "overall_average": overall_average,
            "topic_statistics": {topic: {
                "average": sum(scores) / len(scores),
                "count": len(scores)
            } for topic, scores in topic_scores.items()},
            "dimension_statistics": {dim: {
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores)
            } for dim, scores in all_dimension_scores.items()} if all_dimension_scores else {}
        }
    else:
        summary = {
            "total_conversations": len(results),
            "successful_evaluations": 0,
            "failed_evaluations": len(failed_results),
            "overall_average": None,
            "topic_statistics": {},
            "dimension_statistics": {}
        }
    
    final_results = {
        "summary": summary,
        "conversations": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")
    print("动态对话评估完成!")


if __name__ == "__main__":
    asyncio.run(main())
