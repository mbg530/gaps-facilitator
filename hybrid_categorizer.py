"""
Hybrid Categorization System
Combines rule-based categorization with LLM fallback for best of both worlds
"""

from rule_based_categorizer import RuleBasedCategorizer
import openai_api
import json
from typing import Dict, Optional

class HybridCategorizer:
    """
    Intelligent categorization system that uses:
    1. Rule-based categorization for predictable, fast results
    2. LLM fallback for complex cases
    3. Confidence-based decision making
    """
    
    def __init__(self, confidence_threshold: float = 0.6):
        self.rule_categorizer = RuleBasedCategorizer()
        self.confidence_threshold = confidence_threshold
        self.stats = {
            'rule_based_success': 0,
            'llm_fallback_used': 0,
            'total_categorizations': 0
        }
    
    def categorize(self, text: str, context: Optional[Dict] = None, use_llm_fallback: bool = True) -> Dict:
        """
        Categorize text using hybrid approach.
        
        Args:
            text: User input to categorize
            context: Optional context (quadrant state, conversation history)
            use_llm_fallback: Whether to use LLM if rule-based confidence is low
            
        Returns:
            Dict with categorization result, method used, and performance metrics
        """
        self.stats['total_categorizations'] += 1
        
        # Try rule-based categorization first
        rule_result = self.rule_categorizer.categorize(text, context)
        
        # If confidence is high enough, use rule-based result
        if rule_result['confidence'] >= self.confidence_threshold:
            self.stats['rule_based_success'] += 1
            return {
                **rule_result,
                'method': 'rule_based',
                'performance': {
                    'response_time_ms': '<5',  # Rule-based is always fast
                    'api_cost': 0,
                    'predictable': True
                }
            }
        
        # If confidence is low and LLM fallback is enabled, use LLM
        if use_llm_fallback:
            self.stats['llm_fallback_used'] += 1
            return self._llm_categorize(text, context, rule_result)
        
        # Otherwise, return rule-based result with low confidence warning
        return {
            **rule_result,
            'method': 'rule_based_low_confidence',
            'warning': 'Low confidence result - consider LLM fallback',
            'performance': {
                'response_time_ms': '<5',
                'api_cost': 0,
                'predictable': True
            }
        }
    
    def _llm_categorize(self, text: str, context: Optional[Dict], rule_result: Dict) -> Dict:
        """Use LLM for categorization with rule-based context."""
        try:
            # Build prompt with rule-based insights
            prompt = f"""
            Categorize this user input into one of four quadrants: goal, status, analysis, or plan.
            
            User input: "{text}"
            
            Rule-based analysis suggests: {rule_result['quadrant']} (confidence: {rule_result['confidence']:.2f})
            Reasoning: {rule_result['reasoning']}
            
            Please provide your categorization as JSON:
            {{"quadrant": "goal|status|analysis|plan", "reasoning": "your reasoning", "confidence": 0.0-1.0}}
            """
            
            # Use existing OpenAI integration
            llm_response = openai_api.conversational_facilitator(prompt)
            
            # Parse LLM response
            if isinstance(llm_response, dict) and 'action' in llm_response:
                # Handle conversational response format
                response_text = llm_response.get('question', '')
                try:
                    # Try to extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        llm_result = json.loads(json_match.group())
                        return {
                            'quadrant': llm_result.get('quadrant', rule_result['quadrant']),
                            'confidence': llm_result.get('confidence', 0.8),
                            'reasoning': f"LLM: {llm_result.get('reasoning', 'LLM categorization')}; Rule-based: {rule_result['reasoning']}",
                            'suggestions': rule_result['suggestions'],
                            'method': 'llm_with_rule_context',
                            'performance': {
                                'response_time_ms': '1000-3000',
                                'api_cost': 0.01,
                                'predictable': False
                            }
                        }
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Fallback to rule-based if LLM fails
            return {
                **rule_result,
                'method': 'rule_based_fallback',
                'warning': 'LLM failed - used rule-based result',
                'performance': {
                    'response_time_ms': '<5',
                    'api_cost': 0,
                    'predictable': True
                }
            }
            
        except Exception as e:
            # Fallback to rule-based on any error
            return {
                **rule_result,
                'method': 'rule_based_error_fallback',
                'warning': f'LLM error: {str(e)} - used rule-based result',
                'performance': {
                    'response_time_ms': '<5',
                    'api_cost': 0,
                    'predictable': True
                }
            }
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics for the hybrid system."""
        total = self.stats['total_categorizations']
        if total == 0:
            return {'message': 'No categorizations performed yet'}
        
        return {
            'total_categorizations': total,
            'rule_based_success_rate': self.stats['rule_based_success'] / total,
            'llm_fallback_rate': self.stats['llm_fallback_used'] / total,
            'estimated_cost_savings': f"${self.stats['rule_based_success'] * 0.01:.2f}",
            'estimated_speed_improvement': f"{self.stats['rule_based_success']} fast responses"
        }
    
    def compare_methods(self, text: str, context: Optional[Dict] = None) -> Dict:
        """Compare rule-based vs LLM categorization for analysis."""
        rule_result = self.rule_categorizer.categorize(text, context)
        llm_result = self._llm_categorize(text, context, rule_result)
        
        return {
            'text': text,
            'rule_based': {
                'quadrant': rule_result['quadrant'],
                'confidence': rule_result['confidence'],
                'reasoning': rule_result['reasoning']
            },
            'llm_based': {
                'quadrant': llm_result['quadrant'],
                'confidence': llm_result['confidence'],
                'reasoning': llm_result['reasoning']
            },
            'agreement': rule_result['quadrant'] == llm_result['quadrant'],
            'recommendation': 'rule_based' if rule_result['confidence'] >= 0.7 else 'llm_based'
        }


# Example usage and testing
if __name__ == "__main__":
    hybrid = HybridCategorizer(confidence_threshold=0.6)
    
    test_cases = [
        "I want to improve team morale by the end of the quarter",
        "Currently working on the AI strategy document", 
        "The project failed because of unclear requirements",
        "Next step is to schedule a meeting with stakeholders",
        "This is a complex situation that might need LLM analysis"
    ]
    
    print("Hybrid Categorization Test Results:")
    print("=" * 50)
    
    for i, text in enumerate(test_cases, 1):
        result = hybrid.categorize(text, use_llm_fallback=False)  # Test rule-based only first
        print(f"\n{i}. Text: '{text}'")
        print(f"   Quadrant: {result['quadrant']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Method: {result['method']}")
        print(f"   Performance: {result['performance']}")
    
    print(f"\nPerformance Stats:")
    stats = hybrid.get_performance_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
