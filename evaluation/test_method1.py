#!/usr/bin/env python3
"""
Complete TelegramBot Evaluation System: 10-point scale + test cases + retry mechanism
Aligned with pocket-souls-agents/evaluation
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Load environment variables
env_path = os.path.join(project_root, '..', '.env')
load_dotenv(env_path)

# Import evaluation configuration
from config.evaluation_config import LLM_JUDGE_CONFIG, AVAILABLE_TEACHER_MODELS
from methods.method1_fixed_test import FixedTestEvaluator


async def run_complete_evaluation():
    """Run complete evaluation with retry mechanism"""
    print("=" * 80)
    print("TELEGRAMBOT EVALUATION: Comprehensive Test Suite + 10-Point Scale")
    print("=" * 80)

    # Check API key
    openai_api_key = os.getenv("OPENAI_API_KEY")

    print(f"Environment check:")
    print(f"   .env file path: {env_path}")
    print(f"   .env file exists: {os.path.exists(env_path)}")
    print(f"   OPENAI_API_KEY loaded: {'Yes' if openai_api_key else 'No'}")

    if not openai_api_key:
        print("Error: Please set OPENAI_API_KEY environment variable")
        print(f"   Make sure .env file exists at: {env_path}")
        return

    # Show configuration
    print(f"\n评估配置:")
    print(f"   TelegramBot Model: glm-4-flash (via TelegramBot API)")
    print(f"   Judge Model: {LLM_JUDGE_CONFIG['model']} (using OPENAI_API_KEY)")
    print(f"   Evaluation Scale: 10-point scale")
    print(f"   Temperature: {LLM_JUDGE_CONFIG['temperature']} (strict consistency)")

    # Test cases file path
    test_cases_file = os.path.join(project_root, "test_cases", "test_cases.json")

    if not os.path.exists(test_cases_file):
        print(f"Error: Test cases file not found: {test_cases_file}")
        return

    print(f"\n测试用例文件: {test_cases_file}")
    print(f"Loading test cases...")

    # Create evaluator - using 10-point scale configuration
    evaluator = FixedTestEvaluator(openai_api_key)

    try:
        # First round evaluation
        print("Starting initial evaluation...")

        results = await evaluator.evaluate_test_file(test_cases_file)

        if "error" in results:
            print(f"Evaluation failed: {results['error']}")
            return

        # Check for failed tests
        failed_count = results['summary'].get('failed_tests', 0)
        valid_count = results['summary'].get('valid_tests', 0)

        print(f"\nInitial results:")
        print(f"   Total test cases: {valid_count + failed_count}")
        print(f"   Valid tests: {valid_count}")
        print(f"   Failed tests: {failed_count}")

        # Show final results summary
        summary = results["summary"]
        print("\n" + "=" * 80)
        print("Final Evaluation Results")
        print("=" * 80)

        final_valid = summary.get('valid_tests', 0)
        final_failed = summary.get('failed_tests', 0)

        total_cases = final_valid + final_failed
        print(f"Total test cases: {total_cases}")
        print(f"Valid results: {final_valid}")
        print(f"Failed tests: {final_failed}")
        print(f"Overall average score: {summary['overall_average']:.2f}/10.0")

        # Score distribution
        print(f"\nScore distribution (10-point scale):")
        excellent_count = sum(1 for result in results['results'] if result['evaluation']['overall_score'] >= 8.0)
        good_count = sum(1 for result in results['results'] if 6.0 <= result['evaluation']['overall_score'] < 8.0)
        average_count = sum(1 for result in results['results'] if 4.0 <= result['evaluation']['overall_score'] < 6.0)
        poor_count = sum(1 for result in results['results'] if result['evaluation']['overall_score'] < 4.0)

        print(f"  Excellent (8.0+): {excellent_count}")
        print(f"  Good (6.0-7.9): {good_count}")
        print(f"  Average (4.0-5.9): {average_count}")
        print(f"  Poor (<4.0): {poor_count}")

        print(f"\nDimension scores (10-point scale):")
        for dim, scores in summary['dimension_scores'].items():
            print(f"  {dim}: {scores['average']:.2f}/10.0 (min: {scores['min']}, max: {scores['max']})")

        # Save detailed results
        output_file = f"results/method1_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\nComplete results saved to: {output_file}")
        print("Evaluation completed!")

        # Evaluation quality analysis
        avg_score = summary['overall_average']
        print(f"\nEvaluation quality analysis:")
        if avg_score >= 8.5:
            print("   Excellent: TelegramBot performs exceptionally")
        elif avg_score >= 7.5:
            print("   Very Good: TelegramBot performs well with minor improvement areas")
        elif avg_score >= 6.5:
            print("   Good: TelegramBot performs decently with clear improvement opportunities")
        elif avg_score >= 5.5:
            print("   Average: TelegramBot meets basic expectations but needs significant improvement")
        else:
            print("   Needs Improvement: TelegramBot requires substantial improvements in multiple areas")

        if final_failed > 0:
            print(f"\nNote: {final_failed} tests still failed - may need API troubleshooting")

    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
    except Exception as e:
        print(f"\nEvaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_complete_evaluation())

