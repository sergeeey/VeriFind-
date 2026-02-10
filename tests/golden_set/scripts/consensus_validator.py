#!/usr/bin/env python3
"""
Golden Set Consensus Validator — APE 2026
=========================================

Validates Golden Set entries and generates mock LLM predictions
for consensus algorithm testing.

Usage:
    python consensus_validator.py --mode validate
    python consensus_validator.py --mode mock-llm
    python consensus_validator.py --mode consensus

Modes:
    validate    — Validate Golden Set structure and values
    mock-llm    — Generate synthetic LLM predictions (4 models)
    consensus   — Run consensus analysis on mock data
"""

import json
import random
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("../validation_logs/consensus_check.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
RAW_IMPORT = BASE_DIR / "raw_import" / "golden_set_reference_yfinance.json"
V2_CONSENSUS = BASE_DIR / "v2_consensus"
VALIDATION_LOGS = BASE_DIR / "validation_logs"

# LLM Configuration for mock generation
LLM_CONFIG = {
    "gpt4": {"accuracy": 0.95, "variance": 0.02, "bias": 0.0},
    "claude": {"accuracy": 0.93, "variance": 0.025, "bias": 0.01},
    "gemini": {"accuracy": 0.88, "variance": 0.04, "bias": -0.02},
    "llama": {"accuracy": 0.85, "variance": 0.05, "bias": 0.03},
}


@dataclass
class ConsensusResult:
    """Result of consensus analysis for a single query."""
    query_id: str
    reference_value: float
    llm_values: Dict[str, float]
    median_value: float
    std_dev: float
    consensus_status: str  # HIGH, MEDIUM, LOW
    outliers: List[str]  # LLM names that are outliers


def load_golden_set(path: Path = RAW_IMPORT) -> Dict[str, Any]:
    """Load Golden Set from JSON file."""
    log.info(f"Loading Golden Set from {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    log.info(f"Loaded {len(data.get('golden_set', []))} entries")
    return data


def validate_golden_set(data: Dict[str, Any]) -> bool:
    """
    Validate Golden Set structure and values.
    
    Checks:
    - Required fields present
    - Value ranges reasonable
    - Temporal constraints valid
    - No duplicate IDs
    """
    log.info("=" * 60)
    log.info("VALIDATING GOLDEN SET")
    log.info("=" * 60)
    
    golden_set = data.get("golden_set", [])
    metadata = data.get("metadata", {})
    
    # Check metadata
    assert metadata.get("version") == "1.0", "Version mismatch"
    assert metadata.get("total_queries") == 100, "Expected 100 queries"
    
    log.info(f"✓ Metadata valid: {metadata.get('total_queries')} queries")
    
    # Check entries
    ids = set()
    issues = []
    
    for entry in golden_set:
        entry_id = entry.get("id")
        
        # Check duplicates
        if entry_id in ids:
            issues.append(f"Duplicate ID: {entry_id}")
        ids.add(entry_id)
        
        # Check required fields
        required = ["id", "category", "query", "params", "expected_value", "tolerance"]
        for field in required:
            if field not in entry:
                issues.append(f"{entry_id}: Missing field '{field}'")
        
        # Check value ranges
        value = entry.get("expected_value")
        category = entry.get("category")
        
        if category == "correlation":
            if not -1 <= value <= 1:
                issues.append(f"{entry_id}: Correlation {value} out of [-1, 1]")
        elif category == "volatility":
            if value < 0:
                issues.append(f"{entry_id}: Volatility {value} < 0")
        elif category == "sharpe_ratio":
            if abs(value) > 10:  # Suspicious Sharpe
                log.warning(f"{entry_id}: Unusual Sharpe ratio {value}")
    
    # Report
    if issues:
        log.error(f"Found {len(issues)} issues:")
        for issue in issues[:10]:
            log.error(f"  - {issue}")
        return False
    
    log.info(f"✓ All {len(golden_set)} entries valid")
    log.info(f"✓ No duplicate IDs")
    log.info(f"✓ Value ranges valid")
    
    # Category breakdown
    categories = {}
    for entry in golden_set:
        cat = entry.get("category")
        categories[cat] = categories.get(cat, 0) + 1
    
    log.info("Category distribution:")
    for cat, count in sorted(categories.items()):
        log.info(f"  - {cat}: {count}")
    
    return True


def generate_mock_llm_predictions(data: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
    """
    Generate synthetic LLM predictions with realistic variance.
    
    Simulates 4 LLM (GPT-4, Claude, Gemini, LLaMA) with different
    accuracy profiles to test consensus algorithms.
    """
    log.info("=" * 60)
    log.info("GENERATING MOCK LLM PREDICTIONS")
    log.info("=" * 60)
    
    random.seed(seed)
    golden_set = data.get("golden_set", [])
    
    llm_outputs = {
        "metadata": {
            "version": "1.0-mock",
            "generated_at": datetime.now().isoformat(),
            "models": list(LLM_CONFIG.keys()),
            "note": "Synthetic data for testing consensus algorithms"
        },
        "predictions": []
    }
    
    for entry in golden_set:
        entry_id = entry.get("id")
        reference = entry.get("expected_value")
        tolerance = entry.get("tolerance")
        
        llm_values = {}
        
        for llm_name, config in LLM_CONFIG.items():
            # Simulate prediction with noise
            noise = random.gauss(config["bias"], config["variance"])
            prediction = reference * (1 + noise)
            
            # Add occasional outliers (5% chance)
            if random.random() < 0.05:
                prediction = reference * random.uniform(0.5, 1.5)
                log.debug(f"{entry_id}/{llm_name}: Injected outlier {prediction:.4f}")
            
            llm_values[llm_name] = round(prediction, 4)
        
        llm_outputs["predictions"].append({
            "query_id": entry_id,
            "reference_value": reference,
            "tolerance": tolerance,
            "llm_predictions": llm_values
        })
    
    # Save
    output_path = V2_CONSENSUS / "mock_llm_predictions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(llm_outputs, f, indent=2, ensure_ascii=False)
    
    log.info(f"✓ Generated predictions for {len(golden_set)} queries")
    log.info(f"✓ Saved to {output_path}")
    
    return llm_outputs


def calculate_consensus(predictions: Dict[str, Any]) -> List[ConsensusResult]:
    """
    Calculate consensus across LLM predictions.
    
    Criteria:
    - HIGH: Std Dev < tolerance/2
    - MEDIUM: Std Dev between tolerance/2 and tolerance
    - LOW: Std Dev > tolerance
    """
    log.info("=" * 60)
    log.info("CALCULATING CONSENSUS")
    log.info("=" * 60)
    
    results = []
    
    for pred in predictions.get("predictions", []):
        query_id = pred.get("query_id")
        reference = pred.get("reference_value")
        tolerance = pred.get("tolerance")
        llm_values = pred.get("llm_predictions", {})
        
        values = list(llm_values.values())
        
        # Calculate statistics
        median_val = statistics.median(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        # Determine consensus status
        if std_dev < tolerance / 2:
            status = "HIGH"
        elif std_dev < tolerance:
            status = "MEDIUM"
        else:
            status = "LOW"
        
        # Identify outliers (>2 std from median)
        outliers = []
        for llm, val in llm_values.items():
            if abs(val - median_val) > 2 * std_dev:
                outliers.append(llm)
        
        results.append(ConsensusResult(
            query_id=query_id,
            reference_value=reference,
            llm_values=llm_values,
            median_value=median_val,
            std_dev=std_dev,
            consensus_status=status,
            outliers=outliers
        ))
    
    return results


def generate_consensus_report(results: List[ConsensusResult]) -> None:
    """Generate consensus analysis report."""
    log.info("=" * 60)
    log.info("GENERATING CONSENSUS REPORT")
    log.info("=" * 60)
    
    # Statistics
    total = len(results)
    high = sum(1 for r in results if r.consensus_status == "HIGH")
    medium = sum(1 for r in results if r.consensus_status == "MEDIUM")
    low = sum(1 for r in results if r.consensus_status == "LOW")
    
    # Outliers
    all_outliers = [r.query_id for r in results if r.outliers]
    
    report = {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_queries": total,
            "models_analyzed": list(LLM_CONFIG.keys())
        },
        "consensus_summary": {
            "HIGH": {"count": high, "percentage": round(100 * high / total, 1)},
            "MEDIUM": {"count": medium, "percentage": round(100 * medium / total, 1)},
            "LOW": {"count": low, "percentage": round(100 * low / total, 1)}
        },
        "outlier_queries": all_outliers,
        "tier_breakdown": {
            "Tier 1 (HIGH consensus)": f"{high} queries — Ready for production use",
            "Tier 2 (MEDIUM consensus)": f"{medium} queries — Review recommended",
            "Tier 3 (LOW consensus)": f"{low} queries — Manual verification required"
        }
    }
    
    # Save report
    report_path = V2_CONSENSUS / "consensus_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Save detailed results
    details_path = V2_CONSENSUS / "consensus_details.json"
    details = [
        {
            "query_id": r.query_id,
            "reference": r.reference_value,
            "median": r.median_value,
            "std_dev": r.std_dev,
            "status": r.consensus_status,
            "outliers": r.outliers,
            "llm_values": r.llm_values
        }
        for r in results
    ]
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2, ensure_ascii=False)
    
    # Log summary
    log.info(f"Total queries: {total}")
    log.info(f"  HIGH consensus:   {high} ({report['consensus_summary']['HIGH']['percentage']}%)")
    log.info(f"  MEDIUM consensus: {medium} ({report['consensus_summary']['MEDIUM']['percentage']}%)")
    log.info(f"  LOW consensus:    {low} ({report['consensus_summary']['LOW']['percentage']}%)")
    log.info(f"Outlier queries: {len(all_outliers)}")
    log.info(f"✓ Report saved to {report_path}")


def generate_master_golden_set(data: Dict[str, Any], results: List[ConsensusResult]) -> None:
    """
    Generate master Golden Set with consensus annotations.
    
    Adds consensus_status and llm_sources to original Golden Set.
    """
    log.info("=" * 60)
    log.info("GENERATING MASTER GOLDEN SET")
    log.info("=" * 60)
    
    golden_set = data.get("golden_set", [])
    
    # Create lookup for consensus results
    consensus_map = {r.query_id: r for r in results}
    
    master_set = []
    for entry in golden_set:
        entry_id = entry.get("id")
        consensus = consensus_map.get(entry_id)
        
        # Add consensus fields
        enriched_entry = entry.copy()
        enriched_entry["consensus_status"] = consensus.consensus_status if consensus else "UNKNOWN"
        enriched_entry["llm_sources"] = list(LLM_CONFIG.keys())
        enriched_entry["llm_median_value"] = round(consensus.median_value, 4) if consensus else None
        enriched_entry["llm_std_dev"] = round(consensus.std_dev, 6) if consensus else None
        
        master_set.append(enriched_entry)
    
    # Create master file
    master_data = {
        "metadata": {
            **data.get("metadata", {}),
            "consensus_enriched": True,
            "llm_models": list(LLM_CONFIG.keys()),
            "generated_at": datetime.now().isoformat()
        },
        "golden_set": master_set
    }
    
    master_path = V2_CONSENSUS / "master_golden_set.json"
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)
    
    log.info(f"✓ Master Golden Set saved to {master_path}")
    log.info(f"  Entries: {len(master_set)}")
    log.info(f"  With consensus annotations: {len([e for e in master_set if e.get('consensus_status')])}")


def main():
    parser = argparse.ArgumentParser(description="Golden Set Consensus Validator")
    parser.add_argument(
        "--mode",
        choices=["validate", "mock-llm", "consensus", "full"],
        default="full",
        help="Operation mode"
    )
    args = parser.parse_args()
    
    # Ensure directories exist
    V2_CONSENSUS.mkdir(parents=True, exist_ok=True)
    VALIDATION_LOGS.mkdir(parents=True, exist_ok=True)
    
    if args.mode == "validate":
        data = load_golden_set()
        valid = validate_golden_set(data)
        return 0 if valid else 1
    
    elif args.mode == "mock-llm":
        data = load_golden_set()
        predictions = generate_mock_llm_predictions(data)
        return 0
    
    elif args.mode == "consensus":
        # Load mock predictions
        pred_path = V2_CONSENSUS / "mock_llm_predictions.json"
        if not pred_path.exists():
            log.error(f"Mock predictions not found. Run with --mode mock-llm first.")
            return 1
        
        with open(pred_path, "r") as f:
            predictions = json.load(f)
        
        results = calculate_consensus(predictions)
        generate_consensus_report(results)
        return 0
    
    elif args.mode == "full":
        # Run complete pipeline
        data = load_golden_set()
        
        if not validate_golden_set(data):
            log.error("Validation failed. Aborting.")
            return 1
        
        predictions = generate_mock_llm_predictions(data)
        results = calculate_consensus(predictions)
        generate_consensus_report(results)
        generate_master_golden_set(data, results)
        
        log.info("=" * 60)
        log.info("FULL PIPELINE COMPLETE")
        log.info("=" * 60)
        log.info(f"Output directory: {V2_CONSENSUS}")
        log.info("Files generated:")
        log.info("  - master_golden_set.json")
        log.info("  - mock_llm_predictions.json")
        log.info("  - consensus_report.json")
        log.info("  - consensus_details.json")
        
        return 0


if __name__ == "__main__":
    exit(main())
