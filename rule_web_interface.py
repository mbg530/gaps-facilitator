#!/usr/bin/env python3
"""
Simple Web Interface for Rule-Based Categorization Testing
Runs on http://localhost:5002 for easy browser access
"""

from flask import Flask, render_template_string, request, jsonify
from rule_based_categorizer import RuleBasedCategorizer
import json

app = Flask(__name__)
categorizer = RuleBasedCategorizer()

# Simple HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Rule-Based Categorization Tester</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 10px 0; }
        .result { background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .error { background: #ffebee; color: #c62828; }
        .success { background: #e8f5e9; color: #2e7d32; }
        input[type="text"] { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        button:hover { background: #45a049; }
        .quadrant { display: inline-block; margin: 5px; padding: 5px 10px; border-radius: 3px; font-weight: bold; }
        .goal { background: #e3f2fd; color: #1976d2; }
        .status { background: #f3e5f5; color: #7b1fa2; }
        .analysis { background: #fff3e0; color: #f57c00; }
        .plan { background: #e8f5e9; color: #388e3c; }
        .rules { background: #fafafa; padding: 10px; border-left: 4px solid #2196F3; margin: 10px 0; }
        .keyword { background: #e0e0e0; padding: 2px 6px; margin: 2px; border-radius: 3px; display: inline-block; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>🧪 Rule-Based Categorization Tester</h1>
    <p>Test how the rule-based system categorizes text into quadrants instantly!</p>
    
    <div class="container">
        <h3>🎯 Test Single Input</h3>
        <input type="text" id="testInput" placeholder="Enter text to categorize (e.g., 'I want to increase sales by 20%')" />
        <button onclick="testSingle()">Categorize</button>
        <div id="singleResult"></div>
    </div>
    
    <div class="container">
        <h3>📦 Quick Examples</h3>
        <button onclick="testExample('I want to increase sales by 20% this quarter')">Goal Example</button>
        <button onclick="testExample('We are currently behind on the project timeline')">Status Example</button>
        <button onclick="testExample('The main issue is poor communication between teams')">Analysis Example</button>
        <button onclick="testExample('Next step is to schedule a team meeting')">Plan Example</button>
    </div>
    
    <div class="container">
        <h3>⚡ Performance Test</h3>
        <button onclick="performanceTest()">Run Speed Test (100 categorizations)</button>
        <div id="performanceResult"></div>
    </div>
    
    <div class="container">
        <h3>📋 Current Rules</h3>
        <button onclick="viewRules()">View All Rules</button>
        <div id="rulesDisplay"></div>
    </div>

    <script>
        function testSingle() {
            const text = document.getElementById('testInput').value;
            if (!text.trim()) {
                document.getElementById('singleResult').innerHTML = '<div class="result error">Please enter some text to test.</div>';
                return;
            }
            
            fetch('/categorize', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            })
            .then(response => response.json())
            .then(data => {
                const quadrantClass = data.category.toLowerCase();
                document.getElementById('singleResult').innerHTML = `
                    <div class="result success">
                        <strong>Text:</strong> "${data.text}"<br>
                        <strong>Category:</strong> <span class="quadrant ${quadrantClass}">${data.category.toUpperCase()}</span><br>
                        <strong>Confidence:</strong> ${data.confidence.toFixed(2)}<br>
                        <strong>Speed:</strong> ${data.processing_time_ms.toFixed(1)}ms<br>
                        ${data.matched_keywords.length > 0 ? '<strong>Matched Keywords:</strong> ' + data.matched_keywords.map(k => `<span class="keyword">${k}</span>`).join('') : ''}
                    </div>
                `;
            });
        }
        
        function testExample(text) {
            document.getElementById('testInput').value = text;
            testSingle();
        }
        
        function performanceTest() {
            document.getElementById('performanceResult').innerHTML = '<div class="result">Running performance test...</div>';
            
            fetch('/performance', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                document.getElementById('performanceResult').innerHTML = `
                    <div class="result success">
                        <strong>📊 Performance Results:</strong><br>
                        Processed: ${data.total_tests} categorizations<br>
                        Total time: ${data.total_time_ms.toFixed(1)}ms<br>
                        Average: ${data.avg_time_ms.toFixed(2)}ms per categorization<br>
                        Speed: ${data.categorizations_per_second.toFixed(0)} categorizations/second<br>
                        Cost: $0.00 (no API calls needed!)
                    </div>
                `;
            });
        }
        
        function viewRules() {
            fetch('/rules')
            .then(response => response.json())
            .then(data => {
                let html = '<div class="rules">';
                for (const [quadrant, patterns] of Object.entries(data)) {
                    html += `<h4>🎯 ${quadrant.toUpperCase()} Quadrant</h4>`;
                    html += `<strong>Keywords (${patterns.keywords.length}):</strong><br>`;
                    html += patterns.keywords.slice(0, 15).map(k => `<span class="keyword">${k}</span>`).join('');
                    if (patterns.keywords.length > 15) html += `<span class="keyword">...and ${patterns.keywords.length - 15} more</span>`;
                    html += `<br><strong>Phrase Patterns:</strong> ${patterns.phrases.length} regex patterns<br><br>`;
                }
                html += '</div>';
                document.getElementById('rulesDisplay').innerHTML = html;
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/categorize', methods=['POST'])
def categorize():
    data = request.json
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    result = categorizer.categorize(text)
    return jsonify(result)

@app.route('/performance', methods=['POST'])
def performance_test():
    import time
    
    test_cases = [
        "I want to achieve better results",
        "Currently working on the project", 
        "The issue is lack of resources",
        "Plan to implement new strategy"
    ] * 25  # 100 total tests
    
    start_time = time.time()
    for text in test_cases:
        categorizer.categorize(text)
    end_time = time.time()
    
    total_time_ms = (end_time - start_time) * 1000
    avg_time_ms = total_time_ms / len(test_cases)
    categorizations_per_second = len(test_cases) / (total_time_ms / 1000)
    
    return jsonify({
        'total_tests': len(test_cases),
        'total_time_ms': total_time_ms,
        'avg_time_ms': avg_time_ms,
        'categorizations_per_second': categorizations_per_second
    })

@app.route('/rules')
def get_rules():
    return jsonify(categorizer.patterns)

if __name__ == '__main__':
    print("🌐 Starting Rule-Based Categorization Web Interface...")
    print("📍 Open your browser to: http://localhost:5002")
    print("🚀 Ready for rule-based testing!")
    app.run(host='127.0.0.1', port=5002, debug=True)
