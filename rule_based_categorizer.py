"""
Rule-Based Quadrant Categorization System
A predictable, controllable alternative to LLM-based categorization
"""

import re
from typing import Dict, List, Tuple, Optional

class RuleBasedCategorizer:
    """
    Categorizes user thoughts into quadrants using rule-based pattern matching.
    Much more predictable and controllable than LLM-based approaches.
    """
    
    def __init__(self):
        # Define keyword patterns for each quadrant
        self.patterns = {
            'goal': {
                'keywords': [
                    'want to', 'need to', 'goal', 'achieve', 'target', 'aim', 'objective',
                    'hope to', 'plan to', 'intend to', 'desire', 'aspire', 'strive',
                    'would like to', 'looking to', 'trying to', 'working toward'
                ],
                'phrases': [
                    r'by\s+\w+\s+(end|finish|complete)',  # "by the end of"
                    r'within\s+\d+\s+(days?|weeks?|months?)',  # "within 3 months"
                    r'(accomplish|reach|attain)\s+\w+',
                    r'(vision|mission|purpose)\s+(is|of)'
                ]
            },
            
            'status': {
                'keywords': [
                    'currently', 'right now', 'at present', 'today', 'this week',
                    'status', 'doing', 'working on', 'in progress', 'ongoing',
                    'have been', 'am', 'is', 'are', 'been doing', 'responsible for'
                ],
                'phrases': [
                    r'(currently|presently|now)\s+(working|doing|handling)',
                    r'(status|progress)\s+(is|of|on)',
                    r'(responsible|accountable)\s+for',
                    r'(my|our)\s+(current|present)\s+(role|position|task)'
                ]
            },
            
            'analysis': {
                'keywords': [
                    'because', 'due to', 'reason', 'cause', 'analysis', 'why',
                    'problem', 'issue', 'challenge', 'obstacle', 'barrier',
                    'root cause', 'impact', 'effect', 'consequence', 'result',
                    'leading to', 'resulted in', 'caused by', 'stems from'
                ],
                'phrases': [
                    r'(reason|cause)\s+(is|for|why)',
                    r'(problem|issue|challenge)\s+(is|with|in)',
                    r'(analysis|assessment)\s+(shows?|indicates?)',
                    r'(impact|effect|consequence)\s+(of|on|is)',
                    r'(failed|unsuccessful)\s+\w+\s+(due to|because)'
                ]
            },
            
            'plan': {
                'keywords': [
                    'will', 'plan to', 'next step', 'action', 'strategy', 'approach',
                    'going to', 'intend to', 'schedule', 'timeline', 'roadmap',
                    'next', 'then', 'after', 'following', 'subsequent', 'future'
                ],
                'phrases': [
                    r'(plan|strategy|approach)\s+(is|to|for)',
                    r'(next|following)\s+(step|action|phase)',
                    r'(will|going to|intend to)\s+\w+',
                    r'(timeline|schedule|roadmap)\s+(for|of|is)',
                    r'(action\s+plan|implementation|execution)'
                ]
            }
        }
        
        # Confidence scoring weights
        self.weights = {
            'exact_keyword': 3,
            'phrase_match': 4,
            'context_bonus': 1,
            'length_penalty': -0.1  # Longer texts get slight penalty for specificity
        }
    
    def categorize(self, text: str, context: Optional[Dict] = None) -> Dict:
        """
        Categorize text into the most appropriate quadrant.
        
        Args:
            text: User input text to categorize
            context: Optional context (existing quadrant state, conversation history)
            
        Returns:
            Dict with 'quadrant', 'confidence', 'reasoning', and 'suggestions'
        """
        if not text or not text.strip():
            return {
                'quadrant': 'status',  # Default fallback
                'confidence': 0.1,
                'reasoning': 'Empty input - defaulted to status',
                'suggestions': []
            }
        
        text_lower = text.lower().strip()
        scores = {'goal': 0, 'status': 0, 'analysis': 0, 'plan': 0}
        reasoning_details = []
        
        # Score each quadrant
        for quadrant, patterns in self.patterns.items():
            score = 0
            matches = []
            
            # Check keywords
            for keyword in patterns['keywords']:
                if keyword in text_lower:
                    score += self.weights['exact_keyword']
                    matches.append(f"keyword: '{keyword}'")
            
            # Check phrase patterns
            for pattern in patterns['phrases']:
                if re.search(pattern, text_lower):
                    score += self.weights['phrase_match']
                    matches.append(f"pattern: {pattern}")
            
            # Apply length penalty for very long texts
            if len(text) > 200:
                score += self.weights['length_penalty'] * (len(text) - 200) / 100
            
            scores[quadrant] = score
            if matches:
                reasoning_details.append(f"{quadrant}: {', '.join(matches[:3])}")
        
        # Apply contextual bonuses
        if context:
            scores = self._apply_context_bonuses(scores, text_lower, context)
        
        # Determine best quadrant
        best_quadrant = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[best_quadrant] / (sum(scores.values()) + 0.001)  # Normalize
        
        # If no clear winner, use heuristics
        if scores[best_quadrant] <= 1:
            best_quadrant, confidence = self._apply_heuristics(text_lower)
            reasoning_details.append(f"Applied heuristics: {best_quadrant}")
        
        return {
            'quadrant': best_quadrant,
            'confidence': min(confidence, 1.0),
            'reasoning': '; '.join(reasoning_details) if reasoning_details else 'Heuristic classification',
            'suggestions': self._generate_suggestions(text, best_quadrant)
        }
    
    def _apply_context_bonuses(self, scores: Dict, text: str, context: Dict) -> Dict:
        """Apply contextual bonuses based on conversation history and quadrant state."""
        # If user is asking about specific quadrant, boost that quadrant
        for quadrant in scores.keys():
            if quadrant in text:
                scores[quadrant] += self.weights['context_bonus']
        
        # If certain quadrants are empty, slightly boost them for balance
        if context.get('quadrant_counts'):
            total_items = sum(context['quadrant_counts'].values())
            if total_items > 0:
                for quadrant, count in context['quadrant_counts'].items():
                    if count == 0:
                        scores[quadrant] += 0.5  # Small boost for empty quadrants
        
        return scores
    
    def _apply_heuristics(self, text: str) -> Tuple[str, float]:
        """Apply simple heuristics when pattern matching fails."""
        # Time-based heuristics
        if any(word in text for word in ['will', 'going', 'next', 'future', 'tomorrow']):
            return 'plan', 0.6
        
        # Present tense heuristics
        if any(word in text for word in ['am', 'is', 'are', 'currently', 'now']):
            return 'status', 0.6
        
        # Question words often indicate analysis
        if any(word in text for word in ['why', 'how', 'what', 'because', 'reason']):
            return 'analysis', 0.6
        
        # Goal indicators
        if any(word in text for word in ['want', 'need', 'should', 'must', 'goal']):
            return 'goal', 0.6
        
        # Default to status for unclear inputs
        return 'status', 0.3
    
    def _generate_suggestions(self, text: str, quadrant: str) -> List[str]:
        """Generate helpful suggestions based on categorization."""
        suggestions = []
        
        if quadrant == 'goal':
            suggestions.append("Consider adding a timeline or deadline")
            suggestions.append("Think about what success looks like")
        elif quadrant == 'status':
            suggestions.append("What's the current progress percentage?")
            suggestions.append("Any blockers or challenges?")
        elif quadrant == 'analysis':
            suggestions.append("What are the root causes?")
            suggestions.append("How does this impact other areas?")
        elif quadrant == 'plan':
            suggestions.append("What are the specific next steps?")
            suggestions.append("Who is responsible for each action?")
        
        return suggestions
    
    def batch_categorize(self, texts: List[str], context: Optional[Dict] = None) -> List[Dict]:
        """Categorize multiple texts at once."""
        return [self.categorize(text, context) for text in texts]
    
    def get_statistics(self) -> Dict:
        """Get statistics about the categorization patterns."""
        stats = {}
        for quadrant, patterns in self.patterns.items():
            stats[quadrant] = {
                'keyword_count': len(patterns['keywords']),
                'phrase_pattern_count': len(patterns['phrases'])
            }
        return stats


# Example usage and testing
if __name__ == "__main__":
    categorizer = RuleBasedCategorizer()
    
    # Test cases
    test_cases = [
        "I want to improve team morale by the end of the quarter",
        "Currently working on the AI strategy document",
        "The project failed because of lack of management support",
        "Next step is to schedule a meeting with stakeholders",
        "We need to educate management on AI benefits",
        "Employee morale is significantly impacted",
        "Failed past AI efforts leading to skepticism",
        "Plan to implement training program next month"
    ]
    
    print("Rule-Based Categorization Test Results:")
    print("=" * 50)
    
    for i, text in enumerate(test_cases, 1):
        result = categorizer.categorize(text)
        print(f"\n{i}. Text: '{text}'")
        print(f"   Quadrant: {result['quadrant']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reasoning: {result['reasoning']}")
        if result['suggestions']:
            print(f"   Suggestions: {', '.join(result['suggestions'])}")
