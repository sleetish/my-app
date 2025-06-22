import React, { useState, useEffect } from 'react';
import { Terminal, CheckCircle, XCircle, AlertCircle, Code, FileText, GitBranch, TestTube, Package, Loader, Sparkles, ChevronRight, History, BookOpen } from 'lucide-react';

const SelfValidatingDevLoop = () => {
  const [prompt, setPrompt] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [validationStatus, setValidationStatus] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('code');
  const [documentation, setDocumentation] = useState('');

  // Simulate LLM code generation
  const generateCode = async () => {
    setIsGenerating(true);
    setValidationStatus(null);
    setFeedback([]);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Example code generation based on prompt
    let code = '';
    if (prompt.toLowerCase().includes('factorial')) {
      code = `def factorial(n):
    """
    Calculate the factorial of a number n.
    
    Args:
        n (int): The number to calculate factorial for
        
    Returns:
        int: The factorial of n
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    elif n == 0 or n == 1:
        return 1
    else:
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result`;
    } else if (prompt.toLowerCase().includes('fibonacci')) {
      code = `def fibonacci(n):
    """
    Generate the nth Fibonacci number.
    
    Args:
        n (int): The position in the Fibonacci sequence
        
    Returns:
        int: The nth Fibonacci number
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b`;
    } else {
      code = `# Generated code based on: "${prompt}"
def example_function():
    """
    Example function generated from prompt.
    Add your implementation here.
    """
    pass`;
    }
    
    setGeneratedCode(code);
    setIsGenerating(false);
    
    // Add to history
    setHistory(prev => [{
      id: Date.now(),
      prompt,
      code,
      timestamp: new Date().toLocaleTimeString()
    }, ...prev.slice(0, 4)]);
  };

  // Simulate code validation
  const validateCode = async () => {
    setIsValidating(true);
    setFeedback([]);
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const validationResults = [];
    
    // Syntax check
    validationResults.push({
      type: 'syntax',
      status: 'success',
      message: 'Syntax is valid'
    });
    
    // Documentation check
    if (generatedCode.includes('"""')) {
      validationResults.push({
        type: 'documentation',
        status: 'success',
        message: 'Documentation is properly formatted'
      });
    } else {
      validationResults.push({
        type: 'documentation',
        status: 'warning',
        message: 'Consider adding docstrings for better documentation'
      });
    }
    
    // Best practices check
    if (generatedCode.includes('raise')) {
      validationResults.push({
        type: 'error-handling',
        status: 'success',
        message: 'Proper error handling detected'
      });
    }
    
    // Performance check
    if (generatedCode.includes('for') && generatedCode.includes('range')) {
      validationResults.push({
        type: 'performance',
        status: 'info',
        message: 'Loop detected - consider using list comprehension for simple operations'
      });
    }
    
    // Test coverage suggestion
    validationResults.push({
      type: 'testing',
      status: 'info',
      message: 'Remember to write unit tests for this function'
    });
    
    setFeedback(validationResults);
    
    const hasErrors = validationResults.some(r => r.status === 'error');
    setValidationStatus(hasErrors ? 'error' : 'success');
    setIsValidating(false);
    
    // Update documentation
    if (!hasErrors) {
      setDocumentation(`Function successfully validated!
      
Best Practices Applied:
- Clear function naming
- Comprehensive docstrings
- Error handling for edge cases
- Efficient algorithm implementation

Next Steps:
1. Write unit tests
2. Consider edge cases
3. Optimize for performance if needed
4. Integrate with version control`);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-yellow-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <AlertCircle className="w-5 h-5 text-blue-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Self-Validating Development Loop
          </h1>
          <p className="text-gray-400">AI-powered code generation with automatic validation</p>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Input and Controls */}
          <div className="lg:col-span-1 space-y-4">
            {/* Prompt Input */}
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Terminal className="w-5 h-5" />
                Code Request
              </h2>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what you want to build..."
                className="w-full h-32 bg-gray-700 border border-gray-600 rounded-lg p-3 text-gray-100 placeholder-gray-400 focus:outline-none focus:border-blue-400 transition-colors"
              />
              <button
                onClick={generateCode}
                disabled={!prompt || isGenerating}
                className="mt-4 w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg transition-all flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Generate Code
                  </>
                )}
              </button>
            </div>

            {/* Workflow Status */}
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <GitBranch className="w-5 h-5" />
                Workflow Status
              </h2>
              <div className="space-y-3">
                <div className={`flex items-center gap-2 ${generatedCode ? 'text-green-400' : 'text-gray-500'}`}>
                  <CheckCircle className="w-4 h-4" />
                  <span>Code Generated</span>
                </div>
                <div className={`flex items-center gap-2 ${validationStatus ? 'text-green-400' : 'text-gray-500'}`}>
                  <CheckCircle className="w-4 h-4" />
                  <span>Validation Complete</span>
                </div>
                <div className={`flex items-center gap-2 ${validationStatus === 'success' ? 'text-green-400' : 'text-gray-500'}`}>
                  <CheckCircle className="w-4 h-4" />
                  <span>Ready to Deploy</span>
                </div>
              </div>
            </div>

            {/* History */}
            {history.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <History className="w-5 h-5" />
                  Recent Generations
                </h2>
                <div className="space-y-2">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      className="text-sm bg-gray-700 rounded p-2 cursor-pointer hover:bg-gray-600 transition-colors"
                      onClick={() => {
                        setPrompt(item.prompt);
                        setGeneratedCode(item.code);
                      }}
                    >
                      <p className="text-gray-300 truncate">{item.prompt}</p>
                      <p className="text-gray-500 text-xs">{item.timestamp}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Panel - Code and Validation */}
          <div className="lg:col-span-2 space-y-4">
            {/* Code Display */}
            <div className="bg-gray-800 rounded-lg border border-gray-700">
              <div className="flex border-b border-gray-700">
                <button
                  onClick={() => setActiveTab('code')}
                  className={`px-6 py-3 font-semibold transition-colors flex items-center gap-2 ${
                    activeTab === 'code' ? 'bg-gray-700 text-blue-400' : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <Code className="w-4 h-4" />
                  Generated Code
                </button>
                <button
                  onClick={() => setActiveTab('docs')}
                  className={`px-6 py-3 font-semibold transition-colors flex items-center gap-2 ${
                    activeTab === 'docs' ? 'bg-gray-700 text-blue-400' : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <BookOpen className="w-4 h-4" />
                  Documentation
                </button>
              </div>
              
              <div className="p-6">
                {activeTab === 'code' ? (
                  <>
                    {generatedCode ? (
                      <>
                        <pre className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                          <code className="text-sm font-mono text-gray-300">{generatedCode}</code>
                        </pre>
                        <button
                          onClick={validateCode}
                          disabled={isValidating}
                          className="mt-4 bg-purple-500 hover:bg-purple-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-all flex items-center gap-2"
                        >
                          {isValidating ? (
                            <>
                              <Loader className="w-4 h-4 animate-spin" />
                              Validating...
                            </>
                          ) : (
                            <>
                              <TestTube className="w-4 h-4" />
                              Validate Code
                            </>
                          )}
                        </button>
                      </>
                    ) : (
                      <div className="text-center py-12 text-gray-500">
                        <Code className="w-12 h-12 mx-auto mb-4" />
                        <p>Generated code will appear here</p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="prose prose-invert max-w-none">
                    {documentation ? (
                      <pre className="whitespace-pre-wrap text-gray-300">{documentation}</pre>
                    ) : (
                      <div className="text-center py-12 text-gray-500">
                        <BookOpen className="w-12 h-12 mx-auto mb-4" />
                        <p>Documentation will appear after validation</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Validation Feedback */}
            {feedback.length > 0 && (
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Validation Feedback
                </h2>
                <div className="space-y-3">
                  {feedback.map((item, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-3 p-3 bg-gray-700 rounded-lg"
                    >
                      {getStatusIcon(item.status)}
                      <div className="flex-1">
                        <p className="font-semibold capitalize">{item.type.replace('-', ' ')}</p>
                        <p className="text-sm text-gray-400">{item.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
                
                {validationStatus === 'success' && (
                  <div className="mt-4 p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
                    <p className="text-green-400 font-semibold flex items-center gap-2">
                      <CheckCircle className="w-5 h-5" />
                      Code is ready for implementation!
                    </p>
                    <p className="text-sm text-gray-400 mt-1">
                      All validation checks passed. The code can be automatically deployed.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SelfValidatingDevLoop;