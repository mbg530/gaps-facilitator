"""
Rule Testing Interface
Interactive tool for testing and adjusting categorization rules
"""

from rule_based_categorizer import RuleBasedCategorizer
from hybrid_categorizer import HybridCategorizer
import json
import os

class RuleTester:
    """Interactive interface for testing and adjusting categorization rules."""
    
    def __init__(self):
        self.categorizer = RuleBasedCategorizer()
        self.hybrid = HybridCategorizer()
        self.test_cases = [
            "I want to improve team morale by the end of the quarter",
            "Currently working on the AI strategy document",
            "The project failed because of lack of management support", 
            "Next step is to schedule a meeting with stakeholders",
            "We need to educate management on AI benefits",
            "Employee morale is significantly impacted",
            "Failed past AI efforts leading to skepticism",
            "Plan to implement training program next month"
        ]
    
    def run_interactive_test(self):
        """Run interactive testing session."""
        print("🧪 Rule-Based Categorization Tester")
        print("=" * 50)
        
        while True:
            print("\nOptions:")
            print("1. Test single input")
            print("2. Test all sample cases")
            print("3. Add new keyword")
            print("4. Test with custom text file")
            print("5. Compare rule-based vs hybrid")
            print("6. View current rules")
            print("7. Performance statistics")
            print("8. Exit")
            
            choice = input("\nEnter choice (1-8): ").strip()
            
            if choice == '1':
                self._test_single_input()
            elif choice == '2':
                self._test_all_samples()
            elif choice == '3':
                self._add_keyword()
            elif choice == '4':
                self._test_from_file()
            elif choice == '5':
                self._compare_methods()
            elif choice == '6':
                self._view_rules()
            elif choice == '7':
                self._show_statistics()
            elif choice == '8':
                print("Goodbye! 👋")
                break
            else:
                print("Invalid choice. Please try again.")
    
    def _test_single_input(self):
        """Test a single user input."""
        text = input("\nEnter text to categorize: ").strip()
        if not text:
            print("Empty input!")
            return
        
        result = self.categorizer.categorize(text)
        
        print(f"\n📊 Results for: '{text}'")
        print(f"   Quadrant: {result['quadrant']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reasoning: {result['reasoning']}")
        
        if result['suggestions']:
            print(f"   Suggestions: {', '.join(result['suggestions'])}")
        
        # Ask for feedback
        correct = input(f"\nIs '{result['quadrant']}' correct? (y/n/other): ").strip().lower()
        if correct == 'n':
            actual = input("What should it be? (goal/status/analysis/plan): ").strip().lower()
            if actual in ['goal', 'status', 'analysis', 'plan']:
                print(f"📝 Note: '{text}' should be '{actual}' (not '{result['quadrant']}')")
                self._suggest_rule_improvement(text, actual, result['quadrant'])
        elif correct not in ['y', 'yes']:
            if correct in ['goal', 'status', 'analysis', 'plan']:
                print(f"📝 Note: '{text}' should be '{correct}' (not '{result['quadrant']}')")
                self._suggest_rule_improvement(text, correct, result['quadrant'])
    
    def _test_all_samples(self):
        """Test all sample cases."""
        print(f"\n📊 Testing {len(self.test_cases)} sample cases:")
        print("-" * 60)
        
        for i, text in enumerate(self.test_cases, 1):
            result = self.categorizer.categorize(text)
            print(f"{i:2}. {result['quadrant']:8} ({result['confidence']:.2f}) | {text}")
        
        print(f"\n📈 Summary:")
        high_confidence = sum(1 for text in self.test_cases 
                            if self.categorizer.categorize(text)['confidence'] >= 0.7)
        print(f"   High confidence (≥0.7): {high_confidence}/{len(self.test_cases)}")
        print(f"   Success rate: {high_confidence/len(self.test_cases)*100:.1f}%")
    
    def _add_keyword(self):
        """Add a new keyword to a quadrant."""
        print("\nQuadrants: goal, status, analysis, plan")
        quadrant = input("Which quadrant to add keyword to: ").strip().lower()
        
        if quadrant not in ['goal', 'status', 'analysis', 'plan']:
            print("Invalid quadrant!")
            return
        
        keyword = input(f"Enter new keyword for '{quadrant}': ").strip().lower()
        if not keyword:
            print("Empty keyword!")
            return
        
        # Add keyword to the categorizer
        if keyword not in self.categorizer.patterns[quadrant]['keywords']:
            self.categorizer.patterns[quadrant]['keywords'].append(keyword)
            print(f"✅ Added '{keyword}' to {quadrant} keywords")
            
            # Test the change
            test_text = input(f"Test text with '{keyword}' (optional): ").strip()
            if test_text:
                result = self.categorizer.categorize(test_text)
                print(f"Result: {result['quadrant']} (confidence: {result['confidence']:.2f})")
        else:
            print(f"'{keyword}' already exists in {quadrant} keywords")
    
    def _test_from_file(self):
        """Test categorization from a text file."""
        filename = input("Enter filename (or path): ").strip()
        
        try:
            with open(filename, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            print(f"\n📊 Testing {len(lines)} lines from {filename}:")
            print("-" * 60)
            
            for i, text in enumerate(lines, 1):
                result = self.categorizer.categorize(text)
                print(f"{i:2}. {result['quadrant']:8} ({result['confidence']:.2f}) | {text[:50]}...")
                
        except FileNotFoundError:
            print(f"File '{filename}' not found!")
        except Exception as e:
            print(f"Error reading file: {e}")
    
    def _compare_methods(self):
        """Compare rule-based vs hybrid categorization."""
        text = input("\nEnter text to compare methods: ").strip()
        if not text:
            print("Empty input!")
            return
        
        rule_result = self.categorizer.categorize(text)
        hybrid_result = self.hybrid.categorize(text, use_llm_fallback=False)
        
        print(f"\n🔄 Comparison for: '{text}'")
        print("-" * 50)
        print(f"Rule-based:  {rule_result['quadrant']:8} (confidence: {rule_result['confidence']:.2f})")
        print(f"Hybrid:      {hybrid_result['quadrant']:8} (confidence: {hybrid_result['confidence']:.2f})")
        print(f"Method used: {hybrid_result.get('method', 'rule_based')}")
        
        if rule_result['quadrant'] == hybrid_result['quadrant']:
            print("✅ Both methods agree!")
        else:
            print("⚠️  Methods disagree - might need rule adjustment")
    
    def _view_rules(self):
        """Display current rules."""
        print("\n📋 Current Categorization Rules:")
        print("=" * 50)
        
        for quadrant, patterns in self.categorizer.patterns.items():
            print(f"\n{quadrant.upper()}:")
            print(f"  Keywords ({len(patterns['keywords'])}): {', '.join(patterns['keywords'][:10])}")
            if len(patterns['keywords']) > 10:
                print(f"    ... and {len(patterns['keywords'])-10} more")
            print(f"  Patterns ({len(patterns['phrases'])}): {len(patterns['phrases'])} regex patterns")
    
    def _show_statistics(self):
        """Show performance statistics."""
        print("\n📈 Performance Statistics:")
        print("-" * 30)
        
        stats = self.categorizer.get_statistics()
        for quadrant, data in stats.items():
            print(f"{quadrant:8}: {data['keyword_count']:2} keywords, {data['phrase_pattern_count']:2} patterns")
        
        # Test sample performance
        high_conf = sum(1 for text in self.test_cases 
                       if self.categorizer.categorize(text)['confidence'] >= 0.7)
        print(f"\nSample test performance: {high_conf}/{len(self.test_cases)} high confidence")
        
        hybrid_stats = self.hybrid.get_performance_stats()
        if hybrid_stats.get('total_categorizations', 0) > 0:
            print(f"\nHybrid system stats:")
            for key, value in hybrid_stats.items():
                print(f"  {key}: {value}")
    
    def _suggest_rule_improvement(self, text, correct_quadrant, predicted_quadrant):
        """Suggest rule improvements based on feedback."""
        words = text.lower().split()
        
        print(f"\n💡 Suggestions to improve categorization:")
        print(f"   Text: '{text}'")
        print(f"   Should be: {correct_quadrant}")
        print(f"   Was predicted: {predicted_quadrant}")
        
        # Find potential keywords to add
        current_keywords = set()
        for patterns in self.categorizer.patterns.values():
            current_keywords.update(patterns['keywords'])
        
        new_keywords = [word for word in words if word not in current_keywords 
                       and len(word) > 2 and word.isalpha()]
        
        if new_keywords:
            print(f"   Consider adding to {correct_quadrant}: {', '.join(new_keywords[:3])}")
        
        # Check if any current keywords are misleading
        misleading = []
        for word in words:
            if word in self.categorizer.patterns[predicted_quadrant]['keywords']:
                misleading.append(word)
        
        if misleading:
            print(f"   Consider removing from {predicted_quadrant}: {', '.join(misleading)}")


def create_sample_test_file():
    """Create a sample test file for batch testing."""
    sample_texts = [
        "I want to achieve better work-life balance",
        "Currently managing three different projects",
        "The delay happened because of resource constraints", 
        "Will start the implementation phase next week",
        "Need to improve customer satisfaction scores",
        "Working on the quarterly budget review",
        "Root cause analysis shows process bottlenecks",
        "Action plan includes training and new tools"
    ]
    
    with open('sample_test_cases.txt', 'w') as f:
        for text in sample_texts:
            f.write(f"{text}\n")
    
    print("📁 Created 'sample_test_cases.txt' for batch testing")


if __name__ == "__main__":
    # Create sample test file
    create_sample_test_file()
    
    # Run interactive tester
    tester = RuleTester()
    tester.run_interactive_test()
