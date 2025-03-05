#!/usr/bin/env python3
"""
Local Testing Script for Weather Agent

This script provides a convenient way to run different types of tests locally
during development. It includes options for:
- Unit tests
- Integration tests
- Agent evaluation
- Code coverage
- Linting
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import json
import time

def run_command(command, description):
    """Run a command and print its output"""
    print(f"\n=== {description} ===")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    return result.returncode == 0

def run_unit_tests(args):
    """Run unit tests with optional coverage"""
    cmd = "pytest tests/ -v"
    if args.coverage:
        cmd += " --cov=. --cov-report=html"
    if args.pattern:
        cmd += f" -k {args.pattern}"
    return run_command(cmd, "Running Unit Tests")

def run_integration_tests(args):
    """Run integration tests"""
    cmd = "pytest tests/ -v -m integration"
    if args.pattern:
        cmd += f" -k {args.pattern}"
    return run_command(cmd, "Running Integration Tests")

def run_agent_eval(args):
    """Run agent evaluation"""
    cmd = "python -m agent_eval.evaluator"
    if args.mode:
        cmd += f" --mode={args.mode}"
    success = run_command(cmd, "Running Agent Evaluation")
    
    # Display results summary
    if success and Path("agent_eval/latest_report.json").exists():
        with open("agent_eval/latest_report.json") as f:
            report = json.load(f)
            print("\nEvaluation Summary:")
            print("===================")
            for metric, value in report["summary"].items():
                print(f"{metric}: {value}")
            
            if report.get("recommendations"):
                print("\nRecommendations:")
                for rec in report["recommendations"]:
                    print(f"- {rec}")
    return success

def run_linting():
    """Run code quality checks"""
    success = True
    print("\n=== Running Code Quality Checks ===")
    
    # Run black
    print("\nChecking code formatting (black):")
    if not run_command("black . --check", ""):
        print("❌ Code formatting issues found. Run 'black .' to fix.")
        success = False
    else:
        print("✓ Code formatting OK")
    
    # Run flake8
    print("\nChecking code style (flake8):")
    if not run_command("flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics", ""):
        print("❌ Code style issues found")
        success = False
    else:
        print("✓ Code style OK")
    
    # Run mypy
    print("\nChecking type hints (mypy):")
    if not run_command("mypy .", ""):
        print("❌ Type checking issues found")
        success = False
    else:
        print("✓ Type checking OK")
    
    return success

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['WEATHER_API_KEY', 'BRAVE_API_KEY', 'TOGETHER_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("\n⚠️  Missing environment variables:")
        for var in missing:
            print(f"- {var}")
        print("\nPlease set these variables in your .env file or environment")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Run Weather Agent tests locally")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--eval", action="store_true", help="Run agent evaluation")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--lint", action="store_true", help="Run code quality checks")
    parser.add_argument("--all", action="store_true", help="Run all tests and checks")
    parser.add_argument("--pattern", help="Only run tests matching this pattern")
    parser.add_argument("--mode", choices=['basic', 'integration'], help="Evaluation mode")
    
    args = parser.parse_args()
    
    # Default to --all if no specific tests are selected
    if not any([args.unit, args.integration, args.eval, args.lint, args.all]):
        args.all = True
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    success = True
    start_time = time.time()
    
    try:
        # Run selected tests
        if args.all or args.unit:
            success &= run_unit_tests(args)
        
        if args.all or args.integration:
            success &= run_integration_tests(args)
        
        if args.all or args.eval:
            success &= run_agent_eval(args)
        
        if args.all or args.lint:
            success &= run_linting()
        
        duration = time.time() - start_time
        print(f"\n=== Test Run Complete ({duration:.2f}s) ===")
        
        if args.coverage:
            print("\nCoverage report generated in htmlcov/index.html")
        
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 