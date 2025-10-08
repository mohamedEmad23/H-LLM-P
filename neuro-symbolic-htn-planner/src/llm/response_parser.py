"""
Response Parser for LLM-generated HTN Methods

This module provides parsers to extract structured HTN Method objects from
various LLM response formats (JSON, structured text, natural language).

Features:
- Multiple format support (JSON, structured text, natural language)
- Syntax validation for methods
- Error recovery with fallback parsing strategies
- Type checking for parameters
- Conversion to HTN domain Method format
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class ParsingStrategy(Enum):
    """Different parsing strategies for LLM responses."""
    STRICT_JSON = "strict_json"     # Expects valid JSON
    STRUCTURED_TEXT = "structured"   # Expects formatted text blocks
    NATURAL_LANGUAGE = "natural"     # Extracts from natural language
    AUTO = "auto"                    # Auto-detect format


@dataclass
class ParsedMethod:
    """Represents a parsed HTN method from LLM response."""
    name: str
    task_name: str
    parameters: List[str]
    preconditions: List[str]
    subtasks: List[Tuple[str, List[str]]]  # (task_name, parameters)
    effects: List[str]
    confidence: float = 1.0  # Confidence in parsing (0.0-1.0)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "task_name": self.task_name,
            "parameters": self.parameters,
            "preconditions": self.preconditions,
            "subtasks": self.subtasks,
            "effects": self.effects,
            "confidence": self.confidence,
            "metadata": self.metadata or {}
        }
    
    def __str__(self) -> str:
        """Return formatted string representation."""
        subtasks_str = '\n    '.join(
            f"{i+1}. {name}({', '.join(params)})" 
            for i, (name, params) in enumerate(self.subtasks)
        )
        return f"""Method: {self.name}
  Task: {self.task_name}({', '.join(self.parameters)})
  Preconditions:
    {chr(10).join('- ' + p for p in self.preconditions) if self.preconditions else '- None'}
  Subtasks:
    {subtasks_str}
  Effects:
    {chr(10).join('- ' + e for e in self.effects) if self.effects else '- None'}
  Confidence: {self.confidence:.2%}
"""


class ParsingError(Exception):
    """Raised when parsing fails."""
    pass


class ResponseParser:
    """
    Parses LLM responses to extract HTN Method objects.
    
    Supports multiple parsing strategies and provides validation
    for extracted methods.
    """
    
    # Regex patterns for parsing
    PATTERNS = {
        'method_block': r'```\s*(Method:.*?)```',
        'method_line': r'Method:\s*(\w+)',
        'task_line': r'Task:\s*(\w+)\((.*?)\)',
        'precondition_section': r'Preconditions?:\s*(.*?)(?=Subtasks?:|Effects?:|```|$)',
        'subtask_section': r'Subtasks?:\s*(.*?)(?=Effects?:|```|$)',
        'effect_section': r'Effects?:\s*(.*?)(?=```|$)',
        'subtask_line': r'(?:\d+\.|\-)\s*(\w+)\((.*?)\)',
        'condition_line': r'(?:\-|\*)\s*(.+?)(?=\n|$)',
    }
    
    def __init__(self, strategy: ParsingStrategy = ParsingStrategy.AUTO):
        """
        Initialize the response parser.
        
        Args:
            strategy: Parsing strategy to use
        """
        self.strategy = strategy
    
    def parse(self, llm_response: str) -> ParsedMethod:
        """
        Parse an LLM response to extract an HTN method.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            ParsedMethod object
            
        Raises:
            ParsingError: If parsing fails
        """
        # Auto-detect strategy if needed
        if self.strategy == ParsingStrategy.AUTO:
            detected_strategy = self._detect_format(llm_response)
        else:
            detected_strategy = self.strategy
        
        # Try parsing with detected strategy
        try:
            if detected_strategy == ParsingStrategy.STRICT_JSON:
                return self._parse_json(llm_response)
            elif detected_strategy == ParsingStrategy.STRUCTURED_TEXT:
                return self._parse_structured(llm_response)
            else:  # NATURAL_LANGUAGE
                return self._parse_natural(llm_response)
        except Exception as e:
            # Fallback to other strategies
            return self._parse_with_fallback(llm_response, str(e))
    
    def parse_multiple(self, llm_response: str) -> List[ParsedMethod]:
        """
        Parse multiple methods from a single LLM response.
        
        Args:
            llm_response: Raw response containing multiple methods
            
        Returns:
            List of ParsedMethod objects
        """
        methods = []
        
        # Try to find all method blocks
        method_blocks = re.findall(
            self.PATTERNS['method_block'], 
            llm_response, 
            re.DOTALL | re.IGNORECASE
        )
        
        if method_blocks:
            for block in method_blocks:
                try:
                    method = self._parse_structured(block)
                    methods.append(method)
                except ParsingError:
                    continue
        else:
            # Try parsing as single method
            try:
                method = self.parse(llm_response)
                methods.append(method)
            except ParsingError:
                pass
        
        return methods
    
    def _detect_format(self, response: str) -> ParsingStrategy:
        """Detect the format of the response."""
        # Check for JSON
        if response.strip().startswith('{') or response.strip().startswith('['):
            return ParsingStrategy.STRICT_JSON
        
        # Check for structured text markers
        if 'Method:' in response and 'Subtasks:' in response:
            return ParsingStrategy.STRUCTURED_TEXT
        
        # Default to natural language
        return ParsingStrategy.NATURAL_LANGUAGE
    
    def _parse_json(self, response: str) -> ParsedMethod:
        """Parse JSON formatted response."""
        try:
            # Extract JSON from markdown code blocks if needed
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
            
            data = json.loads(json_str)
            
            return ParsedMethod(
                name=data.get('name', data.get('method_name', 'unknown_method')),
                task_name=data.get('task_name', data.get('task', '')),
                parameters=data.get('parameters', []),
                preconditions=data.get('preconditions', []),
                subtasks=self._parse_subtasks_from_data(data.get('subtasks', [])),
                effects=data.get('effects', []),
                confidence=0.95,
                metadata={'format': 'json'}
            )
        except json.JSONDecodeError as e:
            raise ParsingError(f"Invalid JSON format: {e}")
    
    def _parse_structured(self, response: str) -> ParsedMethod:
        """Parse structured text format."""
        # Extract method name
        method_match = re.search(self.PATTERNS['method_line'], response, re.IGNORECASE)
        if not method_match:
            raise ParsingError("Method name not found")
        method_name = method_match.group(1)
        
        # Extract task name and parameters
        task_match = re.search(self.PATTERNS['task_line'], response, re.IGNORECASE)
        if not task_match:
            raise ParsingError("Task definition not found")
        task_name = task_match.group(1)
        task_params_str = task_match.group(2)
        task_params = [p.strip() for p in task_params_str.split(',') if p.strip()]
        
        # Extract preconditions
        precond_match = re.search(
            self.PATTERNS['precondition_section'], 
            response, 
            re.DOTALL | re.IGNORECASE
        )
        preconditions = []
        if precond_match:
            precond_text = precond_match.group(1)
            preconditions = self._extract_list_items(precond_text)
        
        # Extract subtasks
        subtask_match = re.search(
            self.PATTERNS['subtask_section'], 
            response, 
            re.DOTALL | re.IGNORECASE
        )
        subtasks = []
        if subtask_match:
            subtask_text = subtask_match.group(1)
            subtasks = self._extract_subtasks(subtask_text)
        
        # Extract effects
        effect_match = re.search(
            self.PATTERNS['effect_section'], 
            response, 
            re.DOTALL | re.IGNORECASE
        )
        effects = []
        if effect_match:
            effect_text = effect_match.group(1)
            effects = self._extract_list_items(effect_text)
        
        return ParsedMethod(
            name=method_name,
            task_name=task_name,
            parameters=task_params,
            preconditions=preconditions,
            subtasks=subtasks,
            effects=effects,
            confidence=0.90,
            metadata={'format': 'structured_text'}
        )
    
    def _parse_natural(self, response: str) -> ParsedMethod:
        """Parse natural language response (less reliable)."""
        # This is a best-effort parser for natural language
        # Look for key phrases and patterns
        
        # Try to find any structured blocks first
        if 'Method:' in response:
            return self._parse_structured(response)
        
        # Look for method-like patterns in text
        method_name = "generated_method"
        task_name = "unknown_task"
        
        # Try to extract task from phrases like "to accomplish X" or "task: X"
        task_patterns = [
            r'(?:task|accomplish|achieve|goal):\s*(\w+)',
            r'decompose\s+(\w+)',
            r'method\s+for\s+(\w+)',
        ]
        for pattern in task_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                task_name = match.group(1)
                break
        
        # Extract numbered steps as subtasks
        subtasks = []
        step_pattern = r'(?:\d+\.|Step\s+\d+:)\s*([^\n]+)'
        steps = re.findall(step_pattern, response, re.IGNORECASE)
        
        for step in steps:
            # Try to parse as function call
            func_match = re.search(r'(\w+)\s*\(([^)]*)\)', step)
            if func_match:
                subtask_name = func_match.group(1)
                params_str = func_match.group(2)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                subtasks.append((subtask_name, params))
            else:
                # Just use the step text as task name
                clean_step = re.sub(r'[^\w\s]', '', step).strip()
                words = clean_step.split()
                if words:
                    subtask_name = '_'.join(words[:3])  # First 3 words
                    subtasks.append((subtask_name, []))
        
        return ParsedMethod(
            name=method_name,
            task_name=task_name,
            parameters=[],
            preconditions=[],
            subtasks=subtasks,
            effects=[],
            confidence=0.60,  # Lower confidence for natural language parsing
            metadata={'format': 'natural_language', 'warning': 'Low confidence parse'}
        )
    
    def _parse_with_fallback(self, response: str, error_msg: str) -> ParsedMethod:
        """Try all parsing strategies as fallback."""
        strategies = [
            ParsingStrategy.STRUCTURED_TEXT,
            ParsingStrategy.NATURAL_LANGUAGE,
            ParsingStrategy.STRICT_JSON,
        ]
        
        for strategy in strategies:
            try:
                if strategy == ParsingStrategy.STRICT_JSON:
                    return self._parse_json(response)
                elif strategy == ParsingStrategy.STRUCTURED_TEXT:
                    return self._parse_structured(response)
                else:
                    return self._parse_natural(response)
            except Exception:
                continue
        
        raise ParsingError(f"All parsing strategies failed. Original error: {error_msg}")
    
    def _extract_list_items(self, text: str) -> List[str]:
        """Extract list items from text (bullet points, numbered, etc.)."""
        items = []
        
        # Look for lines starting with -, *, or numbers
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove list markers
            clean_line = re.sub(r'^(?:\d+\.|\-|\*)\s*', '', line).strip()
            if clean_line and not clean_line.startswith(('Method:', 'Task:', 'Subtasks:', 'Effects:')):
                items.append(clean_line)
        
        return items
    
    def _extract_subtasks(self, text: str) -> List[Tuple[str, List[str]]]:
        """Extract subtasks with parameters."""
        subtasks = []
        
        # Look for lines with task calls: task_name(param1, param2)
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to parse as function call
            match = re.search(r'(\w+)\s*\(([^)]*)\)', line)
            if match:
                task_name = match.group(1)
                params_str = match.group(2)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                subtasks.append((task_name, params))
            else:
                # Just task name, no parameters
                clean_line = re.sub(r'^(?:\d+\.|\-|\*)\s*', '', line).strip()
                task_name = re.sub(r'[^\w]', '', clean_line.split()[0]) if clean_line else ''
                if task_name:
                    subtasks.append((task_name, []))
        
        return subtasks
    
    def _parse_subtasks_from_data(self, subtasks_data: List) -> List[Tuple[str, List[str]]]:
        """Parse subtasks from JSON data structure."""
        result = []
        for item in subtasks_data:
            if isinstance(item, dict):
                name = item.get('name', item.get('task', ''))
                params = item.get('parameters', item.get('params', []))
                result.append((name, params))
            elif isinstance(item, (list, tuple)) and len(item) >= 1:
                name = item[0]
                params = item[1] if len(item) > 1 else []
                result.append((name, params if isinstance(params, list) else [params]))
            elif isinstance(item, str):
                # Parse string format: "task_name(param1, param2)"
                match = re.search(r'(\w+)\s*\(([^)]*)\)', item)
                if match:
                    name = match.group(1)
                    params_str = match.group(2)
                    params = [p.strip() for p in params_str.split(',') if p.strip()]
                    result.append((name, params))
                else:
                    result.append((item, []))
        return result
    
    def validate_method(self, method: ParsedMethod) -> Tuple[bool, List[str]]:
        """
        Validate a parsed method for correctness.
        
        Args:
            method: Method to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        if not method.name:
            issues.append("Method name is missing")
        if not method.task_name:
            issues.append("Task name is missing")
        if not method.subtasks:
            issues.append("No subtasks defined")
        
        # Check naming conventions
        if method.name and not re.match(r'^[a-zA-Z_]\w*$', method.name):
            issues.append(f"Invalid method name format: {method.name}")
        if method.task_name and not re.match(r'^[a-zA-Z_]\w*$', method.task_name):
            issues.append(f"Invalid task name format: {method.task_name}")
        
        # Check parameters
        for param in method.parameters:
            if not param or not re.match(r'^\??[a-zA-Z_]\w*$', param):
                issues.append(f"Invalid parameter format: {param}")
        
        # Check subtasks
        for i, (task_name, params) in enumerate(method.subtasks):
            if not task_name:
                issues.append(f"Subtask {i+1} has no name")
            if task_name and not re.match(r'^[a-zA-Z_]\w*$', task_name):
                issues.append(f"Invalid subtask name at position {i+1}: {task_name}")
        
        # Check for circular dependencies (basic check)
        if method.task_name in [st[0] for st in method.subtasks]:
            issues.append(f"Circular dependency: task {method.task_name} calls itself")
        
        is_valid = len(issues) == 0
        return is_valid, issues


# Convenience functions

def parse_method(response: str, strategy: ParsingStrategy = ParsingStrategy.AUTO) -> ParsedMethod:
    """
    Parse a method from LLM response (convenience function).
    
    Args:
        response: LLM response text
        strategy: Parsing strategy to use
        
    Returns:
        ParsedMethod object
    """
    parser = ResponseParser(strategy)
    return parser.parse(response)


def parse_and_validate(response: str) -> Tuple[Optional[ParsedMethod], List[str]]:
    """
    Parse and validate a method in one step.
    
    Args:
        response: LLM response text
        
    Returns:
        Tuple of (method or None, list of issues)
    """
    try:
        parser = ResponseParser()
        method = parser.parse(response)
        is_valid, issues = parser.validate_method(method)
        
        if not is_valid:
            return method, issues
        return method, []
    except ParsingError as e:
        return None, [str(e)]


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("Response Parser - Example Usage")
    print("="*80)
    
    # Example 1: Structured text format
    print("\n### Example 1: Structured Text ###\n")
    structured_response = """
Method: move_block_to_table
  Task: move_block(?block, ?from)
  Preconditions:
    - clear(?block)
    - on(?block, ?from)
  Subtasks:
    1. unstack(?block, ?from)
    2. putdown(?block)
  Effects:
    - on(?block, table)
    - clear(?from)
"""
    
    parser = ResponseParser()
    method1 = parser.parse(structured_response)
    print(method1)
    is_valid, issues = parser.validate_method(method1)
    print(f"Valid: {is_valid}")
    if issues:
        print(f"Issues: {issues}")
    
    # Example 2: JSON format
    print("\n### Example 2: JSON Format ###\n")
    json_response = """
```json
{
  "name": "deliver_package_in_city",
  "task_name": "deliver",
  "parameters": ["?pkg", "?from", "?to"],
  "preconditions": ["at(?pkg, ?from)", "in_city(?from, city1)"],
  "subtasks": [
    ["load_truck", ["?pkg", "?truck", "?from"]],
    ["drive_truck", ["?truck", "?from", "?to"]],
    ["unload_truck", ["?pkg", "?truck", "?to"]]
  ],
  "effects": ["at(?pkg, ?to)"]
}
```
"""
    
    method2 = parser.parse(json_response)
    print(method2)
    
    # Example 3: Natural language (lower confidence)
    print("\n### Example 3: Natural Language ###\n")
    natural_response = """
To make coffee, follow these steps:
1. grind_beans(coffee_beans)
2. fill_reservoir(water)
3. brew_coffee(coffee_maker)
4. pour(coffee_maker, cup)
"""
    
    method3 = parser.parse(natural_response)
    print(method3)
    
    # Example 4: Parsing multiple methods
    print("\n### Example 4: Multiple Methods ###\n")
    multiple_response = """
Here are two methods:

```
Method: method1
  Task: task1(?x)
  Subtasks:
    1. subtask1(?x)
```

```
Method: method2
  Task: task2(?y)
  Subtasks:
    1. subtask2(?y)
    2. subtask3(?y)
```
"""
    
    methods = parser.parse_multiple(multiple_response)
    print(f"Found {len(methods)} methods")
    for i, m in enumerate(methods):
        print(f"\nMethod {i+1}: {m.name} (confidence: {m.confidence:.0%})")
    
    print("\n" + "="*80)
    print("✅ Response Parser Examples Complete")
    print("="*80)
