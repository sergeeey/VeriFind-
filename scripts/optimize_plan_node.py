"""
Optimize PLAN Node with DSPy + DeepSeek R1.

Week 5 Day 4: Real optimization using training examples.

Usage:
    python scripts/optimize_plan_node.py --examples data/training_examples/plan_optimization_examples.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import dspy
from src.optimization.deepseek_adapter import configure_deepseek, estimate_cost
from src.optimization.plan_optimizer import PlanOptimizer
from src.optimization.metrics import CompositeMetric


def load_training_examples(examples_path: str):
    """Load training examples from JSON file."""
    with open(examples_path, 'r', encoding='utf-8') as f:
        examples = json.load(f)

    print(f"✅ Loaded {len(examples)} training examples")
    return examples


def prepare_training_examples(training_data):
    """Convert training examples to PlanOptimizer format."""
    from src.optimization.plan_optimizer import TrainingExample
    from src.orchestration.schemas.plan_output import AnalysisPlan, DataRequirement, CodeBlock
    from datetime import datetime, UTC

    training_examples = []

    for idx, ex in enumerate(training_data, 1):
        # Create AnalysisPlan from good_plan
        good_plan = ex['good_plan']
        query = ex['query']

        # Convert data_requirements dict to List[DataRequirement]
        data_reqs = []
        req_data = good_plan['data_requirements']
        for ticker in req_data.get('tickers', []):
            data_req = DataRequirement(
                ticker=ticker,
                start_date=req_data.get('start_date', '2024-01-01'),
                end_date=req_data.get('end_date', '2024-12-31'),
                data_type='ohlcv',  # Default to OHLCV
                source='yfinance'  # Default to yfinance
            )
            data_reqs.append(data_req)

        # Convert code string to List[CodeBlock]
        code_block = CodeBlock(
            step_id='main_analysis',
            description=good_plan['description'],
            code=good_plan['code'],
            depends_on=[],
            timeout_seconds=60
        )

        # Create AnalysisPlan with required fields
        plan = AnalysisPlan(
            query_id=f'train_{idx:03d}',
            user_query=query,
            plan_reasoning=good_plan['reasoning'],
            data_requirements=data_reqs,
            code_blocks=[code_block],
            expected_output_format='Dictionary with numerical results',
            confidence_level=ex.get('quality_score', 0.9),
            caveats=ex.get('issues_in_bad', [])[:3] if 'issues_in_bad' in ex else [],
            created_at=datetime.now(UTC).isoformat(),
            model_used='deepseek-reasoner'
        )

        # Create TrainingExample
        training_ex = TrainingExample(
            user_query=query,
            expected_plan=plan,
            query_date=ex.get('query_date')  # Optional field
        )

        training_examples.append(training_ex)

    return training_examples


def run_optimization(
    examples_path: str,
    output_path: str,
    model: str = 'deepseek-reasoner',
    num_trials: int = 3,
    dry_run: bool = False
):
    """
    Run DSPy optimization with DeepSeek R1.

    Args:
        examples_path: Path to training examples JSON
        output_path: Path to save optimized prompt
        model: DeepSeek model name
        num_trials: Number of optimization trials
        dry_run: If True, skip actual optimization (for testing)
    """
    print("="*80)
    print("🚀 DSPy PLAN Node Optimization with DeepSeek R1")
    print("="*80)
    print()

    # Check API key
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ ERROR: DEEPSEEK_API_KEY not found in environment")
        print("   Set it in .env file or export DEEPSEEK_API_KEY=...")
        sys.exit(1)

    print(f"✅ DeepSeek API key found: {api_key[:10]}...{api_key[-4:]}")
    print()

    # Load training examples
    print("📚 Loading training examples...")
    training_data = load_training_examples(examples_path)
    training_examples = prepare_training_examples(training_data)
    print(f"   Prepared {len(training_examples)} training examples")
    print()

    if dry_run:
        print("🏃 DRY RUN MODE - skipping actual optimization")
        print("   Training examples loaded successfully!")
        return

    # Configure DeepSeek
    print(f"🔧 Configuring DeepSeek R1 ({model})...")
    lm = configure_deepseek(model=model, temperature=0.0)
    print(f"   ✅ Language model configured: {lm}")
    print()

    # Initialize optimizer (no API key needed - DSPy configured globally)
    print("🎯 Initializing PlanOptimizer...")
    optimizer = PlanOptimizer(api_key="dummy")  # API key required but DeepSeek configured via dspy.settings

    # Add training examples
    optimizer.add_training_examples(training_examples)
    print(f"   ✅ Added {len(optimizer.training_examples)} training examples")
    print()

    # Setup metric
    metric = CompositeMetric()
    print(f"   ✅ Using CompositeMetric: {metric.weights}")
    print()

    # Estimate cost
    print("💰 Estimating optimization cost...")
    # Rough estimate: 5 examples * 3 bootstraps * (1500 input + 800 output tokens per example)
    estimated_input = len(training_examples) * num_trials * 1500
    estimated_output = len(training_examples) * num_trials * 800
    estimated_cost = estimate_cost(estimated_input, estimated_output, model=model)
    print(f"   Estimated tokens: {estimated_input} input + {estimated_output} output")
    print(f"   Estimated cost: ${estimated_cost:.4f}")
    print()

    # Confirm before proceeding
    response = input("   Proceed with optimization? [y/N]: ").strip().lower()
    if response != 'y':
        print("   ❌ Optimization cancelled")
        return
    print()

    # Run optimization
    print("⚡ Running DSPy BootstrapFewShot optimization...")
    print(f"   Max bootstrapped demos: {num_trials}")
    print(f"   Max labeled demos: 8")
    print(f"   This may take 3-7 minutes...")
    print()

    try:
        # Real DSPy optimization with DeepSeek R1
        optimized_module = optimizer.optimize(
            optimizer_type="bootstrap",
            max_bootstrapped_demos=num_trials,
            max_labeled_demos=8
        )

        print("   ✅ Optimization complete!")
        print()

        # Save optimized prompt
        print(f"💾 Saving optimized prompt to {output_path}...")
        optimized_prompt = optimizer.export_optimized_prompt()

        # Save as JSON with metadata
        output_data = {
            "optimized_prompt": optimized_prompt,
            "model": model,
            "training_examples": len(training_examples),
            "optimizer_type": "bootstrap",
            "max_bootstrapped_demos": num_trials,
            "timestamp": datetime.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print("   ✅ Prompt saved successfully")
        print()

        # Print summary
        print("="*80)
        print("📊 OPTIMIZATION SUMMARY")
        print("="*80)
        print(f"Training examples: {len(training_examples)}")
        print(f"Max bootstrapped demos: {num_trials}")
        print(f"Optimizer: DSPy BootstrapFewShot")
        print(f"Model: {model}")
        print(f"Estimated cost: ${estimated_cost:.4f}")
        print(f"Output: {output_path}")
        print()
        print("✅ Week 5 Day 4 SUCCESS - Real DSPy optimization with DeepSeek R1 complete!")
        print("="*80)

    except Exception as e:
        print(f"❌ ERROR during optimization: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Optimize PLAN Node with DSPy + DeepSeek R1'
    )
    parser.add_argument(
        '--examples',
        type=str,
        default='data/training_examples/plan_optimization_examples.json',
        help='Path to training examples JSON file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/optimized_prompts/plan_node_optimized.json',
        help='Path to save optimized prompt'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='deepseek-reasoner',
        choices=['deepseek-reasoner', 'deepseek-chat'],
        help='DeepSeek model to use'
    )
    parser.add_argument(
        '--trials',
        type=int,
        default=3,
        help='Number of optimization trials'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (load examples but skip optimization)'
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run optimization
    run_optimization(
        examples_path=args.examples,
        output_path=args.output,
        model=args.model,
        num_trials=args.trials,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
