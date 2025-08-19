#!/usr/bin/env python3
"""
Standalone Rule-Based Categorization Tester
Can be run independently from any terminal without Windsurf
"""

import sys
import os
import json
from rule_based_categorizer import RuleBasedCategorizer

def main():
    print("🧪 Standalone Rule-Based Categorization Tester")
    print("=" * 55)
    print("This tool runs independently in your terminal!")
    print()
    
    categorizer = RuleBasedCategorizer()
    
    while True:
        print("\nOptions:")
        print("1. Test single input")
        print("2. View current rules")
        print("3. Add new keyword")
        print("4. Batch test examples")
        print("5. Performance stats")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == '1':
            test_single_input(categorizer)
        elif choice == '2':
            view_rules(categorizer)
        elif choice == '3':
            add_keyword(categorizer)
        elif choice == '4':
            batch_test(categorizer)
        elif choice == '5':
            performance_stats(categorizer)
        elif choice == '6':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

def test_single_input(categorizer):
    print("\n🧪 Test Single Input")
    print("-" * 20)
    text = input("Enter text to categorize: ").strip()
    
    if not text:
        print("❌ Please enter some text.")
        return
    
    result = categorizer.categorize(text)
    
    print(f"\n📊 Results:")
    print(f"Text: '{text}'")
    print(f"Category: {result['category'].upper()}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Speed: {result['processing_time_ms']:.1f}ms")
    
    if result['matched_keywords']:
        print(f"Matched Keywords: {', '.join(result['matched_keywords'])}")
    if result['matched_phrases']:
        print(f"Matched Phrases: {', '.join(result['matched_phrases'])}")

def view_rules(categorizer):
    print("\n📋 Current Categorization Rules")
    print("-" * 35)
    
    for quadrant, patterns in categorizer.patterns.items():
        print(f"\n🎯 {quadrant.upper()} Quadrant:")
        print(f"   Keywords ({len(patterns['keywords'])}): {', '.join(patterns['keywords'][:8])}{'...' if len(patterns['keywords']) > 8 else ''}")
        print(f"   Phrases ({len(patterns['phrases'])}): {len(patterns['phrases'])} regex patterns")

def add_keyword(categorizer):
    print("\n➕ Add New Keyword")
    print("-" * 18)
    
    print("Available quadrants: goal, status, analysis, plan")
    quadrant = input("Which quadrant? ").strip().lower()
    
    if quadrant not in categorizer.patterns:
        print("❌ Invalid quadrant. Choose: goal, status, analysis, plan")
        return
    
    keyword = input("Enter new keyword/phrase: ").strip()
    if not keyword:
        print("❌ Please enter a keyword.")
        return
    
    categorizer.patterns[quadrant]['keywords'].append(keyword)
    print(f"✅ Added '{keyword}' to {quadrant.upper()} quadrant")
    
    # Test the new keyword
    test_text = input(f"Test with example text (or press Enter to skip): ").strip()
    if test_text:
        result = categorizer.categorize(test_text)
        print(f"Result: {result['category'].upper()} (confidence: {result['confidence']:.2f})")

def batch_test(categorizer):
    print("\n📦 Batch Test Examples")
    print("-" * 22)
    
    examples = [
        "I want to increase sales by 20% this quarter",
        "We're currently behind on the project timeline", 
        "The main issue is poor communication between teams",
        "Next step is to schedule a team meeting",
        "Our goal is to launch the product by December",
        "The problem stems from inadequate resources",
        "I'm working on the marketing campaign right now",
        "We need to plan the next phase carefully"
    ]
    
    print("Testing sample inputs...")
    results = {}
    
    for text in examples:
        result = categorizer.categorize(text)
        category = result['category']
        if category not in results:
            results[category] = []
        results[category].append((text, result['confidence']))
    
    for category, items in results.items():
        print(f"\n🎯 {category.upper()}:")
        for text, confidence in items:
            print(f"   • {text} (confidence: {confidence:.2f})")

def performance_stats(categorizer):
    print("\n⚡ Performance Statistics")
    print("-" * 25)
    
    # Quick performance test
    test_cases = [
        "I want to achieve better results",
        "Currently working on the project", 
        "The issue is lack of resources",
        "Plan to implement new strategy"
    ] * 25  # 100 total tests
    
    import time
    start_time = time.time()
    
    for text in test_cases:
        categorizer.categorize(text)
    
    end_time = time.time()
    total_time = (end_time - start_time) * 1000  # Convert to ms
    avg_time = total_time / len(test_cases)
    
    print(f"📊 Processed {len(test_cases)} categorizations")
    print(f"⏱️  Total time: {total_time:.1f}ms")
    print(f"🚀 Average time: {avg_time:.2f}ms per categorization")
    print(f"💨 Speed: {len(test_cases) / (total_time/1000):.0f} categorizations/second")
    print(f"💰 Cost: $0.00 (no API calls)")

if __name__ == "__main__":
    main()
