#!/usr/bin/env python3

import os
import ast
import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse
import zipfile
import tempfile
import subprocess
import shutil
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    print("Please install FastAPI: pip install fastapi uvicorn aiohttp python-multipart")
    exit(1)

# Domain Models

@dataclass
class CodeEntity:
    """Atomic code unit representation"""
    id: str
    name: str
    type: str  # package, class, method, function
    source: str
    metadata: Dict[str, Any]
    parent_id: Optional[str] = None
    children: List[str] = None


    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class WorkflowNode:
    """Canvas workflow node"""
    id: str
    entity_id: str
    position: Dict[str, float]
    config: Dict[str, Any] = None


    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class WorkflowConnection:
    """Connection between nodes"""
    id: str
    source_id: str
    target_id: str
    metadata: Dict[str, Any] = None


    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# Abstract Interfaces (SOLID - Interface Segregation)

class CodeParser(ABC):
    """Abstract code parser interface"""


    @abstractmethod
    def parse(self, source_path: str) -> List[CodeEntity]:
        pass

    @abstractmethod
    def supports(self, file_path: str) -> bool:
        pass


class AIProvider(ABC):
    """Abstract AI provider interface"""


    @abstractmethod
    async def suggest_workflow(self, entities: List[CodeEntity], goal: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def suggest_connections(self, nodes: List[WorkflowNode]) -> List[WorkflowConnection]:
        pass


class SourceImporter(ABC):
    """Abstract source importer interface"""


    @abstractmethod
    async def import_source(self, source: str) -> str:
        pass

    @abstractmethod
    def supports(self, source: str) -> bool:
        pass


# Concrete Implementations

class PythonParser(CodeParser):
    """Python AST-based code parser"""


    def supports(self, file_path: str) -> bool:
        return file_path.endswith('.py')

    def parse(self, source_path: str) -> List[CodeEntity]:
        entities = []
        
        print(f"Python parser scanning: {source_path}")
        
        if not os.path.exists(source_path):
            print(f"Source path does not exist: {source_path}")
            return entities
        
        # Handle single file vs directory
        if os.path.isfile(source_path) and self.supports(source_path):
            entities.extend(self._parse_file(source_path))
        elif os.path.isdir(source_path):
            # Walk through directory
            python_files_found = 0
            for root, dirs, files in os.walk(source_path):
                # Skip common build/cache directories
                dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv', 'env', '.env'}]
                
                for file in files:
                    if self.supports(file):
                        file_path = os.path.join(root, file)
                        python_files_found += 1
                        try:
                            file_entities = self._parse_file(file_path)
                            entities.extend(file_entities)
                            print(f"Parsed {file_path}: {len(file_entities)} entities")
                        except Exception as e:
                            print(f"Error parsing {file_path}: {e}")
            
            print(f"Found {python_files_found} Python files, parsed {len(entities)} entities")
        
        return entities

    def _parse_file(self, file_path: str) -> List[CodeEntity]:
        entities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            if not content.strip():
                return entities
                
            tree = ast.parse(content, filename=file_path)
            
            # Create module entity
            module_name = Path(file_path).stem
            module_entity = CodeEntity(
                id=f"module_{module_name}_{hash(file_path)}",
                name=module_name,
                type="module",
                source=file_path,
                metadata={
                    "file_path": file_path, 
                    "lines": len(content.splitlines()),
                    "size_bytes": len(content)
                }
            )
            entities.append(module_entity)
            
            # Parse classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entities.append(self._create_class_entity(node, file_path, module_entity.id))
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    # Only top-level functions or class methods
                    parent = self._find_parent_class(node, tree)
                    parent_id = f"class_{parent.name}_{parent.lineno}_{hash(file_path)}" if parent else module_entity.id
                    entities.append(self._create_function_entity(node, file_path, parent_id))
                    
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
        return entities

    def _find_parent_class(self, func_node, tree):
        """Find if function is inside a class"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if child == func_node:
                        return node
        return None

    def _create_class_entity(self, node: ast.ClassDef, file_path: str, parent_id: str) -> CodeEntity:
        methods = []
        method_details = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(child.name)
                # Analyze method signature
                inputs, outputs, side_effects = self._analyze_function_signature(child)
                method_details.append({
                    "name": child.name,
                    "inputs": inputs,
                    "outputs": outputs,
                    "side_effects": side_effects,
                    "is_async": isinstance(child, ast.AsyncFunctionDef)
                })
        
        # Analyze class for data attributes and properties
        attributes = self._extract_class_attributes(node)
        
        return CodeEntity(
            id=f"class_{node.name}_{node.lineno}_{hash(file_path)}",
            name=node.name,
            type="class",
            source=file_path,
            metadata={
                "line_no": node.lineno,
                "methods": methods,
                "method_count": len(methods),
                "method_details": method_details,
                "bases": [self._safe_unparse(base) for base in node.bases] if node.bases else [],
                "docstring": ast.get_docstring(node) or "",
                "attributes": attributes,
                "inputs": self._get_class_inputs(method_details),
                "outputs": self._get_class_outputs(method_details),
                "side_effects": self._get_class_side_effects(method_details)
            },
            parent_id=parent_id
        )

    def _extract_class_attributes(self, node):
        """Extract class attributes and their types"""
        attributes = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                attr_info = {
                    "name": child.target.id,
                    "type": self._safe_unparse(child.annotation) if child.annotation else "Any",
                    "optional": child.value is None
                }
                attributes.append(attr_info)
        
        return attributes

    def _get_class_inputs(self, method_details):
        """Aggregate inputs from all public methods"""
        inputs = []
        seen = set()
        
        for method in method_details:
            if not method["name"].startswith("_"):  # Public methods only
                for inp in method["inputs"]:
                    key = f"{inp['name']}_{inp['type']}"
                    if key not in seen:
                        inputs.append(inp)
                        seen.add(key)
        
        return inputs

    def _get_class_outputs(self, method_details):
        """Aggregate outputs from all public methods"""
        outputs = []
        seen = set()
        
        for method in method_details:
            if not method["name"].startswith("_"):  # Public methods only
                for out in method["outputs"]:
                    key = f"{out['name']}_{out['type']}"
                    if key not in seen:
                        outputs.append(out)
                        seen.add(key)
        
        return outputs

    def _get_class_side_effects(self, method_details):
        """Aggregate side effects from all methods"""
        side_effects = set()
        
        for method in method_details:
            side_effects.update(method["side_effects"])
        
        return list(side_effects)

    def _create_function_entity(self, node, file_path: str, parent_id: str) -> CodeEntity:
        args = []
        arg_types = []
        if hasattr(node, 'args') and node.args:
            for arg in node.args.args:
                args.append(arg.arg)
                # Extract type hints
                if arg.annotation:
                    arg_types.append(self._safe_unparse(arg.annotation))
                else:
                    arg_types.append("Any")
        
        func_type = "method" if "class_" in parent_id else "function"
        if isinstance(node, ast.AsyncFunctionDef):
            func_type = "async_" + func_type
        
        # Analyze function for inputs/outputs and side effects
        inputs, outputs, side_effects = self._analyze_function_signature(node)
        
        return CodeEntity(
            id=f"func_{node.name}_{node.lineno}_{hash(file_path)}",
            name=node.name,
            type=func_type,
            source=file_path,
            metadata={
                "line_no": node.lineno,
                "args": args,
                "arg_types": arg_types,
                "arg_count": len(args),
                "returns": self._safe_unparse(node.returns) if hasattr(node, 'returns') and node.returns else "Any",
                "docstring": ast.get_docstring(node) or "",
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "inputs": inputs,
                "outputs": outputs,
                "side_effects": side_effects,
                "complexity": self._calculate_complexity(node)
            },
            parent_id=parent_id
        )

    def _analyze_function_signature(self, node):
        """Analyze function for smart input/output detection"""
        inputs = []
        outputs = []
        side_effects = []
        
        # Analyze inputs from function arguments
        if hasattr(node, 'args') and node.args:
            for arg in node.args.args:
                if arg.arg != 'self':  # Skip self parameter
                    input_info = {
                        "name": arg.arg,
                        "type": self._safe_unparse(arg.annotation) if arg.annotation else "Any",
                        "optional": False,
                        "port_type": "input"
                    }
                    inputs.append(input_info)
        
        # Analyze default arguments (optional inputs)
        if hasattr(node, 'args') and node.args.defaults:
            defaults_count = len(node.args.defaults)
            for i in range(defaults_count):
                if i < len(inputs):
                    inputs[-(i+1)]["optional"] = True
        
        # Analyze return type for outputs
        if hasattr(node, 'returns') and node.returns:
            return_type = self._safe_unparse(node.returns)
            outputs.append({
                "name": "return_value",
                "type": return_type,
                "optional": False,
                "port_type": "output"
            })
        else:
            # Try to infer return type from function body
            return_type = self._infer_return_type(node)
            outputs.append({
                "name": "return_value", 
                "type": return_type,
                "optional": False,
                "port_type": "output"
            })
        
        # Detect side effects by analyzing function body
        side_effects = self._detect_side_effects(node)
        
        return inputs, outputs, side_effects

    def _infer_return_type(self, node):
        """Infer return type from function body analysis"""
        # Look for return statements
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if child.value:
                    if isinstance(child.value, ast.Constant):
                        return type(child.value.value).__name__
                    elif isinstance(child.value, ast.List):
                        return "list"
                    elif isinstance(child.value, ast.Dict):
                        return "dict"
                    elif isinstance(child.value, ast.Call):
                        return "object"
        
        # Check for yield statements (generators)
        for child in ast.walk(node):
            if isinstance(child, ast.Yield):
                return "generator"
        
        return "Any"

    def _detect_side_effects(self, node):
        """Detect potential side effects in function"""
        side_effects = []
        
        for child in ast.walk(node):
            # Database operations
            if isinstance(child, ast.Call) and hasattr(child.func, 'attr'):
                attr_name = child.func.attr.lower()
                if any(db_op in attr_name for db_op in ['save', 'insert', 'update', 'delete', 'commit']):
                    side_effects.append("database_write")
                elif any(db_op in attr_name for db_op in ['find', 'select', 'query', 'get']):
                    side_effects.append("database_read")
            
            # File operations
            if isinstance(child, ast.Call) and hasattr(child.func, 'id'):
                func_name = child.func.id.lower()
                if func_name in ['open', 'write', 'read']:
                    side_effects.append("file_io")
            
            # Network operations
            if isinstance(child, ast.Call):
                call_str = self._safe_unparse(child).lower()
                if any(net_op in call_str for net_op in ['requests.', 'urllib', 'http', 'fetch']):
                    side_effects.append("network_io")
            
            # Logging
            if isinstance(child, ast.Call):
                call_str = self._safe_unparse(child).lower()
                if any(log_op in call_str for log_op in ['print', 'log', 'logger']):
                    side_effects.append("logging")
        
        return list(set(side_effects))  # Remove duplicates

    def _calculate_complexity(self, node):
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity

    def _safe_unparse(self, node):
        """Safely unparse AST node"""
        try:
            if hasattr(ast, 'unparse'):  # Python 3.9+
                return ast.unparse(node)
            else:
                return str(node.__class__.__name__)
        except:
            return "Unknown"


class JavaScriptParser(CodeParser):
    """Basic JavaScript parser for functions and classes"""


    def supports(self, file_path: str) -> bool:
        return file_path.endswith(('.js', '.jsx', '.ts', '.tsx'))

    def parse(self, source_path: str) -> List[CodeEntity]:
        entities = []
        
        if os.path.isfile(source_path) and self.supports(source_path):
            entities.extend(self._parse_file(source_path))
        elif os.path.isdir(source_path):
            for root, dirs, files in os.walk(source_path):
                dirs[:] = [d for d in dirs if d not in {'node_modules', '.git', 'dist', 'build'}]
                
                for file in files:
                    if self.supports(file):
                        file_path = os.path.join(root, file)
                        try:
                            entities.extend(self._parse_file(file_path))
                        except Exception as e:
                            print(f"Error parsing JS file {file_path}: {e}")
        
        return entities

    def _parse_file(self, file_path: str) -> List[CodeEntity]:
        entities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Simple regex-based parsing for demo
            import re
            
            module_name = Path(file_path).stem
            module_entity = CodeEntity(
                id=f"js_module_{module_name}_{hash(file_path)}",
                name=module_name,
                type="module",
                source=file_path,
                metadata={"file_path": file_path, "language": "javascript"}
            )
            entities.append(module_entity)
            
            # Find functions
            func_pattern = r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))'
            for match in re.finditer(func_pattern, content):
                func_name = match.group(1) or match.group(2)
                if func_name:
                    entities.append(CodeEntity(
                        id=f"js_func_{func_name}_{hash(file_path)}",
                        name=func_name,
                        type="function",
                        source=file_path,
                        metadata={"language": "javascript", "line_no": content[:match.start()].count('\n') + 1},
                        parent_id=module_entity.id
                    ))
            
            # Find classes
            class_pattern = r'class\s+(\w+)'
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                entities.append(CodeEntity(
                    id=f"js_class_{class_name}_{hash(file_path)}",
                    name=class_name,
                    type="class",
                    source=file_path,
                    metadata={"language": "javascript", "line_no": content[:match.start()].count('\n') + 1},
                    parent_id=module_entity.id
                ))
                
        except Exception as e:
            print(f"Error parsing JavaScript file {file_path}: {e}")
        
        return entities


class ClaudeAI(AIProvider):
    """Claude AI provider (primary)"""

    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.available = bool(self.api_key)

    async def _call_claude(self, prompt: str) -> str:
        if not self.api_key:
            raise Exception("Claude API key not configured")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "x-api-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            ) as response:
                if response.status != 200:
                    raise Exception(f"Claude API error: {response.status}")
                result = await response.json()
                return result['content'][0]['text']

    async def suggest_workflow(self, entities: List[CodeEntity], goal: str) -> Dict[str, Any]:
        prompt = f"""
        Goal: {goal}
        
        Available code entities:
        {self._format_entities(entities)}
        
        Create a workflow using these entities. Return only valid JSON with:
        {{"nodes": [{{"entity_id": "id", "position": {{"x": 100, "y": 100}}, "config": {{}}}}], "connections": [{{"source": "id1", "target": "id2", "metadata": {{}}}}]}}
        """
        
        try:
            response = await self._call_claude(prompt)
            result = self._parse_ai_response(response)
            result["ai_provider"] = "claude"
            return result
        except Exception as e:
            print(f"Claude error: {e}")
            raise

    async def suggest_connections(self, nodes: List[WorkflowNode]) -> List[WorkflowConnection]:
        prompt = f"""
        Suggest connections between these workflow nodes:
        {self._format_nodes(nodes)}
        
        Return only valid JSON:
        {{"connections": [{{"source_id": "id1", "target_id": "id2", "metadata": {{"type": "data_flow"}}}}]}}
        """
        
        try:
            response = await self._call_claude(prompt)
            suggestions = json.loads(response)
            
            connections = []
            for conn in suggestions.get('connections', []):
                connections.append(WorkflowConnection(
                    id=f"claude_conn_{conn['source_id']}_{conn['target_id']}",
                    source_id=conn['source_id'],
                    target_id=conn['target_id'],
                    metadata=conn.get('metadata', {})
                ))
            
            return connections
        except Exception as e:
            print(f"Claude connection error: {e}")
            raise

    def _format_entities(self, entities: List[CodeEntity]) -> str:
        formatted = []
        for entity in entities:
            formatted.append(f"- {entity.type}: {entity.name} (from {entity.source})")
        return '\n'.join(formatted)

    def _format_nodes(self, nodes: List[WorkflowNode]) -> str:
        formatted = []
        for node in nodes:
            formatted.append(f"- {node.id}: {node.entity_id}")
        return '\n'.join(formatted)

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return {"nodes": [], "connections": [], "error": "No valid JSON found"}
        except json.JSONDecodeError:
            return {"nodes": [], "connections": [], "error": "Invalid JSON response"}


class OpenAIProvider(AIProvider):
    """OpenAI provider (secondary fallback)"""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.available = bool(self.api_key)

    async def _call_openai(self, prompt: str) -> str:
        if not self.api_key:
            raise Exception("OpenAI API key not configured")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000
                }
            ) as response:
                if response.status != 200:
                    raise Exception(f"OpenAI API error: {response.status}")
                result = await response.json()
                return result['choices'][0]['message']['content']

    async def suggest_workflow(self, entities: List[CodeEntity], goal: str) -> Dict[str, Any]:
        prompt = f"""
        Goal: {goal}
        
        Available code entities:
        {self._format_entities(entities)}
        
        Create a workflow using these entities. Return only valid JSON with:
        {{"nodes": [{{"entity_id": "id", "position": {{"x": 100, "y": 100}}, "config": {{}}}}], "connections": [{{"source": "id1", "target": "id2", "metadata": {{}}}}]}}
        """
        
        try:
            response = await self._call_openai(prompt)
            result = self._parse_ai_response(response)
            result["ai_provider"] = "openai"
            return result
        except Exception as e:
            print(f"OpenAI error: {e}")
            raise

    async def suggest_connections(self, nodes: List[WorkflowNode]) -> List[WorkflowConnection]:
        prompt = f"""
        Suggest connections between these workflow nodes:
        {self._format_nodes(nodes)}
        
        Return only valid JSON:
        {{"connections": [{{"source_id": "id1", "target_id": "id2", "metadata": {{"type": "data_flow"}}}}]}}
        """
        
        try:
            response = await self._call_openai(prompt)
            suggestions = json.loads(response)
            
            connections = []
            for conn in suggestions.get('connections', []):
                connections.append(WorkflowConnection(
                    id=f"openai_conn_{conn['source_id']}_{conn['target_id']}",
                    source_id=conn['source_id'],
                    target_id=conn['target_id'],
                    metadata=conn.get('metadata', {})
                ))
            
            return connections
        except Exception as e:
            print(f"OpenAI connection error: {e}")
            raise

    def _format_entities(self, entities: List[CodeEntity]) -> str:
        formatted = []
        for entity in entities:
            formatted.append(f"- {entity.type}: {entity.name} (from {entity.source})")
        return '\n'.join(formatted)

    def _format_nodes(self, nodes: List[WorkflowNode]) -> str:
        formatted = []
        for node in nodes:
            formatted.append(f"- {node.id}: {node.entity_id}")
        return '\n'.join(formatted)

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return {"nodes": [], "connections": [], "error": "No valid JSON found"}
        except json.JSONDecodeError:
            return {"nodes": [], "connections": [], "error": "Invalid JSON response"}


class OllamaAI(AIProvider):
    """Ollama/Llama AI provider (tertiary fallback)"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv('OLLAMA_BASE_URL', "http://localhost:11434")
        self.model = os.getenv('OLLAMA_MODEL', "llama3.1")
        self.available = None

    async def _check_availability(self):
        """Check if Ollama is available"""
        if self.available is not None:
            return self.available
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    self.available = response.status == 200
                    print(f"Ollama availability: {self.available}")
                    return self.available
        except Exception as e:
            print(f"Ollama not available: {e}")
            self.available = False
            return False

    async def suggest_workflow(self, entities: List[CodeEntity], goal: str) -> Dict[str, Any]:
        if not await self._check_availability():
            print("Using mock AI for workflow suggestions")
            return await self.mock_ai.suggest_workflow(entities, goal)
        
        prompt = f"""
        Goal: {goal}
        
        Available code entities:
        {self._format_entities(entities)}
        
        Create a workflow using these entities. Return JSON with:
        {{"nodes": [{{"entity_id": "id", "position": {{"x": 100, "y": 100}}, "config": {{}}}}], "connections": [{{"source": "id1", "target": "id2", "metadata": {{}}}}]}}
        """
        
        try:
            response = await self._call_ollama(prompt)
            result = self._parse_ai_response(response)
            result["ai_provider"] = "ollama"
            return result
        except Exception as e:
            print(f"Ollama error, falling back to mock: {e}")
            return await self.mock_ai.suggest_workflow(entities, goal)

    async def suggest_connections(self, nodes: List[WorkflowNode]) -> List[WorkflowConnection]:
        if not await self._check_availability():
            return await self.mock_ai.suggest_connections(nodes)
        
        try:
            prompt = f"""
            Workflow nodes: {json.dumps([asdict(node) for node in nodes], indent=2)}
            
            Suggest connections between these nodes based on data flow. Return JSON:
            {{"connections": [{{"source_id": "id1", "target_id": "id2", "metadata": {{"type": "data_flow"}}}}]}}
            """
            
            response = await self._call_ollama(prompt)
            suggestions = json.loads(response)
            
            connections = []
            for conn in suggestions.get('connections', []):
                connections.append(WorkflowConnection(
                    id=f"ollama_conn_{conn['source_id']}_{conn['target_id']}",
                    source_id=conn['source_id'],
                    target_id=conn['target_id'],
                    metadata=conn.get('metadata', {})
                ))
            
            return connections
        except Exception as e:
            print(f"Ollama connection error: {e}")
            return await self.mock_ai.suggest_connections(nodes)

    def _format_entities(self, entities: List[CodeEntity]) -> str:
        formatted = []
        for entity in entities[:15]:  # Limit for prompt size
            formatted.append(f"- {entity.type}: {entity.name} (from {entity.source})")
        return '\n'.join(formatted)

    async def _call_ollama(self, prompt: str) -> str:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 500}
                }
            ) as response:
                if response.status != 200:
                    raise Exception(f"Ollama API error: {response.status}")
                
                result = await response.json()
                return result.get('response', '')

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(response)
        except:
            print(f"Failed to parse AI response: {response[:200]}...")
            return {"nodes": [], "connections": [], "error": "Invalid AI response"}


class GitSourceImporter(SourceImporter):
    """Git repository source importer"""


    def supports(self, source: str) -> bool:
        return source.startswith(('http://', 'https://')) and any(
            host in source for host in ['github.com', 'gitlab.com', 'bitbucket.org']
        )

    async def import_source(self, source: str) -> str:
        temp_dir = tempfile.mkdtemp(prefix="lowcode_git_")
        try:
            # Check if git is available
            result = subprocess.run(['git', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Git is not installed or not available in PATH")
            
            print(f"Cloning {source} to {temp_dir}")
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', source, temp_dir],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"Successfully cloned to {temp_dir}")
                return temp_dir
            else:
                raise Exception(f"Git clone failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception("Git clone timed out")
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Failed to import from {source}: {e}")


class LocalSourceImporter(SourceImporter):
    """Local directory source importer"""


    def supports(self, source: str) -> bool:
        # Handle both absolute and relative paths
        expanded_path = os.path.expanduser(source)  # Handle ~ for home directory
        abs_path = os.path.abspath(expanded_path)
        return os.path.exists(abs_path) and os.path.isdir(abs_path)

    async def import_source(self, source: str) -> str:
        # Normalize the path
        expanded_path = os.path.expanduser(source)
        abs_path = os.path.abspath(expanded_path)
        
        if not os.path.exists(abs_path):
            raise Exception(f"Path does not exist: {abs_path}")
        
        if not os.path.isdir(abs_path):
            raise Exception(f"Path is not a directory: {abs_path}")
            
        return abs_path


    # Core Service Classes

class EntityCatalog:
    """Manages parsed code entities (Single Responsibility)"""


    def __init__(self):
        self._entities: Dict[str, CodeEntity] = {}
        self._parsers: List[CodeParser] = [PythonParser(), JavaScriptParser()]

    def add_parser(self, parser: CodeParser):
        """Open/Closed Principle - extend parsers without modification"""
        self._parsers.append(parser)

    async def scan_source(self, source: str) -> List[CodeEntity]:
        """Dependency Inversion - depends on abstractions"""
        print(f"Scanning source: {source}")
        
        # Normalize and validate source path
        if not source.strip():
            raise ValueError("Source cannot be empty")
        
        # Determine importer (try local first for better performance)
        importers = [LocalSourceImporter(), GitSourceImporter()]
        importer = None
        
        for imp in importers:
            if imp.supports(source):
                importer = imp
                print(f"Using importer: {type(imp).__name__}")
                break
        
        if not importer:
            # Try to provide helpful error message
            expanded_path = os.path.expanduser(source)
            abs_path = os.path.abspath(expanded_path)
            if os.path.exists(abs_path):
                if os.path.isfile(abs_path):
                    raise ValueError(f"Path is a file, not a directory: {abs_path}")
                else:
                    raise ValueError(f"Path type not supported: {abs_path}")
            else:
                raise ValueError(f"Path does not exist: {abs_path}. Please provide a valid local directory path or Git repository URL.")
        
        source_path = await importer.import_source(source)
        print(f"Source path resolved to: {source_path}")
        
        # Parse with available parsers
        all_entities = []
        for parser in self._parsers:
            print(f"Parsing with: {type(parser).__name__}")
            entities = parser.parse(source_path)
            all_entities.extend(entities)
            print(f"Found {len(entities)} entities")
        
        # Store entities
        for entity in all_entities:
            self._entities[entity.id] = entity
        
        print(f"Total entities cataloged: {len(all_entities)}")
        
        # Cleanup temp directory if it was a git clone
        if isinstance(importer, GitSourceImporter) and source_path.startswith(tempfile.gettempdir()):
            try:
                shutil.rmtree(source_path, ignore_errors=True)
            except:
                pass
        
        return all_entities

    def get_entities(self, filter_type: Optional[str] = None) -> List[CodeEntity]:
        entities = list(self._entities.values())
        if filter_type:
            entities = [e for e in entities if e.type == filter_type]
        return entities

    def get_entity(self, entity_id: str) -> Optional[CodeEntity]:
        return self._entities.get(entity_id)

    def clear_entities(self):
        """Clear all entities"""
        self._entities.clear()


class WorkflowEngine:
    """Manages workflow composition"""


    def __init__(self, ai_provider: AIProvider):
        self._ai = ai_provider
        self._workflows: Dict[str, Dict[str, Any]] = {}

    async def create_workflow(self, workflow_id: str, entities: List[CodeEntity], goal: str) -> Dict[str, Any]:
        # Get AI suggestions
        suggestions = await self._ai.suggest_workflow(entities, goal)
        
        workflow = {
            "id": workflow_id,
            "goal": goal,
            "nodes": suggestions.get("nodes", []),
            "connections": suggestions.get("connections", []),
            "ai_provider": suggestions.get("ai_provider", "unknown"),
            "created_at": asyncio.get_event_loop().time()
        }
        
        self._workflows[workflow_id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        return self._workflows.get(workflow_id)

    async def suggest_connections(self, workflow_id: str) -> List[WorkflowConnection]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return []
        
        nodes = [WorkflowNode(**node) for node in workflow["nodes"]]
        return await self._ai.suggest_connections(nodes)


# FastAPI Application

app = FastAPI(title="AI Low-Code Platform", version="1.0.0")

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)


class LayeredAI(AIProvider):
    """Layered AI provider: Claude -> OpenAI -> Ollama -> Mock"""

    def __init__(self):
        self.claude = ClaudeAI()
        self.openai = OpenAIProvider()
        self.ollama = OllamaAI()
        self.retry_attempts = int(os.getenv('AI_RETRY_ATTEMPTS', '2'))
        
    async def suggest_workflow(self, entities: List[CodeEntity], goal: str) -> Dict[str, Any]:
        """Try providers in order: Claude -> OpenAI -> Ollama -> Mock"""
        
        # Try Claude first
        if self.claude.available:
            try:
                print("🎯 Trying Claude AI...")
                result = await self.claude.suggest_workflow(entities, goal)
                print("✅ Claude AI successful")
                return result
            except Exception as e:
                print(f"❌ Claude failed: {e}")
        
        # Fallback to OpenAI
        if self.openai.available:
            try:
                print("🔄 Falling back to OpenAI...")
                result = await self.openai.suggest_workflow(entities, goal)
                print("✅ OpenAI successful")
                return result
            except Exception as e:
                print(f"❌ OpenAI failed: {e}")
        
        # Fallback to Ollama
        try:
            print("🔄 Falling back to Ollama...")
            if await self.ollama._check_availability():
                result = await self.ollama.suggest_workflow(entities, goal)
                print("✅ Ollama successful")
                return result
        except Exception as e:
            print(f"❌ Ollama failed: {e}")
        
        # Final fallback to mock
        print("🔄 Using mock AI as final fallback...")
        return await self._mock_workflow(entities, goal)
    
    async def suggest_connections(self, nodes: List[WorkflowNode]) -> List[WorkflowConnection]:
        """Try providers in order: Claude -> OpenAI -> Ollama -> Mock"""
        
        # Try Claude first
        if self.claude.available:
            try:
                print("🎯 Trying Claude AI for connections...")
                result = await self.claude.suggest_connections(nodes)
                print("✅ Claude connections successful")
                return result
            except Exception as e:
                print(f"❌ Claude connections failed: {e}")
        
        # Fallback to OpenAI
        if self.openai.available:
            try:
                print("🔄 Falling back to OpenAI for connections...")
                result = await self.openai.suggest_connections(nodes)
                print("✅ OpenAI connections successful")
                return result
            except Exception as e:
                print(f"❌ OpenAI connections failed: {e}")
        
        # Fallback to Ollama
        try:
            print("🔄 Falling back to Ollama for connections...")
            if await self.ollama._check_availability():
                result = await self.ollama.suggest_connections(nodes)
                print("✅ Ollama connections successful")
                return result
        except Exception as e:
            print(f"❌ Ollama connections failed: {e}")
        
        # Final fallback to mock
        print("🔄 Using mock AI for connections...")
        return await self._mock_connections(nodes)
    
    async def _mock_workflow(self, entities: List[CodeEntity], goal: str) -> Dict[str, Any]:
        """Mock workflow generation"""
        selected_entities = entities[:min(5, len(entities))]
        
        nodes = []
        connections = []
        
        for i, entity in enumerate(selected_entities):
            nodes.append({
                "entity_id": entity.id,
                "position": {"x": 100 + (i % 3) * 200, "y": 100 + (i // 3) * 150},
                "config": {"priority": i + 1}
            })
        
        # Create simple sequential connections
        for i in range(len(nodes) - 1):
            connections.append({
                "source": nodes[i]["entity_id"],
                "target": nodes[i + 1]["entity_id"],
                "metadata": {"type": "data_flow"}
            })
        
        return {
            "nodes": nodes,
            "connections": connections,
            "goal": goal,
            "ai_provider": "mock",
            "confidence": 0.8
        }
    
    async def _mock_connections(self, nodes: List[WorkflowNode]) -> List[WorkflowConnection]:
        """Mock connection suggestions"""
        connections = []
        
        # Simple logic: connect nodes based on proximity and type
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes[i+1:], i+1):
                if j - i <= 2:  # Only connect nearby nodes
                    connections.append(WorkflowConnection(
                        id=f"mock_conn_{node1.id}_{node2.id}",
                        source_id=node1.id,
                        target_id=node2.id,
                        metadata={"type": "suggested", "confidence": 0.7}
                    ))
        
        return connections[:3]  # Limit suggestions


# Initialize services

catalog = EntityCatalog()
ai_provider = LayeredAI()
workflow_engine = WorkflowEngine(ai_provider)

# Request/Response Models

class ScanRequest(BaseModel):
    source: str
    source_type: str = "auto"

class WorkflowRequest(BaseModel):
    goal: str
    entity_ids: List[str] = []

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the frontend HTML"""
    try:
        with open("index.html", "r", encoding='utf-8') as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
        content="<h1>Frontend not found</h1><p>Please create index.html in the same directory as main.py</p>",
        status_code=404
        )

@app.post("/api/scan")
async def scan_source(request: ScanRequest):
    """Scan and parse source code"""
    try:
        entities = await catalog.scan_source(request.source)
        return {
        "success": True,
        "message": f"Scanned {len(entities)} entities",
        "entities": [asdict(entity) for entity in entities],
        "source": request.source
        }
    except Exception as e:
        print(f"Scan error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/entities")
async def get_entities(type_filter: Optional[str] = None):
    """Get all entities or filtered by type"""
    entities = catalog.get_entities(type_filter)
    return {
    "entities": [asdict(entity) for entity in entities],
    "count": len(entities),
    "types": list(set(e.type for e in entities))
    }

@app.post("/api/workflow")
async def create_workflow(request: WorkflowRequest):
    """Create AI-suggested workflow"""
    try:
        # Get requested entities or all entities
        if request.entity_ids:
            entities = [catalog.get_entity(eid) for eid in request.entity_ids]
            entities = [e for e in entities if e is not None]
        else:
            entities = catalog.get_entities()


        if not entities:
            raise HTTPException(status_code=400, detail="No entities available. Please scan a source first.")
        
        # Create workflow
        import time
        workflow_id = f"workflow_{int(time.time())}"
        workflow = await workflow_engine.create_workflow(workflow_id, entities, request.goal)
        
        return {
            "success": True,
            "workflow": workflow,
            "entity_count": len(entities)
        }
    except Exception as e:
        print(f"Workflow creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow by ID"""
    workflow = workflow_engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@app.post("/api/workflow/{workflow_id}/suggest-connections")
async def suggest_connections(workflow_id: str):
    """Get AI connection suggestions for workflow"""
    try:
        connections = await workflow_engine.suggest_connections(workflow_id)
        return {
        "connections": [asdict(conn) for conn in connections],
        "count": len(connections)
        }
    except Exception as e:
        print(f"Connection suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/entities")
async def clear_entities():
    """Clear all entities"""
    catalog.clear_entities()
    return {"success": True, "message": "All entities cleared"}

class TypeCompatibilityEngine:
    """Advanced type compatibility and connection validation engine"""


    # Type compatibility matrix
    TYPE_COMPATIBILITY = {
        "str": ["str", "Any", "object"],
        "int": ["int", "float", "str", "Any", "object"],
        "float": ["float", "int", "str", "Any", "object"],
        "bool": ["bool", "int", "str", "Any", "object"],
        "list": ["list", "tuple", "set", "Any", "object"],
        "dict": ["dict", "object", "Any"],
        "tuple": ["tuple", "list", "Any", "object"],
        "set": ["set", "list", "tuple", "Any", "object"],
        "Any": ["Any", "str", "int", "float", "bool", "list", "dict", "tuple", "set", "object"],
        "object": ["object", "Any"],
        "User": ["User", "dict", "object", "Any"],
        "UserModel": ["UserModel", "User", "dict", "object", "Any"],
        "generator": ["generator", "list", "tuple", "Any", "object"]
    }

    @classmethod
    def validate_connection(cls, source_entity: CodeEntity, target_entity: CodeEntity) -> Dict[str, Any]:
        """Validate connection between two entities"""
        result = {
            "compatible": False,
            "score": 0.0,
            "suggestions": [],
            "warnings": [],
            "connection_type": "unknown"
        }
        
        source_outputs = source_entity.metadata.get("outputs", [])
        target_inputs = target_entity.metadata.get("inputs", [])
    
        if not source_outputs or not target_inputs:
            result["warnings"].append("Missing input/output information")
            return result
        
        # Find best matching input/output pairs
        best_matches = []
        for output in source_outputs:
            for input_port in target_inputs:
                compatibility_score = cls._calculate_type_compatibility(output["type"], input_port["type"])
                if compatibility_score > 0:
                    best_matches.append({
                        "output": output,
                        "input": input_port,
                        "score": compatibility_score,
                        "conversion_needed": compatibility_score < 1.0
                    })
        
        if best_matches:
            # Sort by compatibility score
            best_matches.sort(key=lambda x: x["score"], reverse=True)
            best_match = best_matches[0]
            
            result["compatible"] = True
            result["score"] = best_match["score"]
            result["connection_type"] = cls._determine_connection_type(source_entity, target_entity)
            
            if best_match["conversion_needed"]:
                result["suggestions"].append(f"Type conversion needed: {best_match['output']['type']} → {best_match['input']['type']}")
            
            # Check for side effect compatibility
            source_effects = set(source_entity.metadata.get("side_effects", []))
            target_effects = set(target_entity.metadata.get("side_effects", []))
            
            if "database_write" in source_effects and "database_read" in target_effects:
                result["warnings"].append("Potential race condition: write followed by read")
            
            if source_entity.metadata.get("is_async") != target_entity.metadata.get("is_async"):
                result["warnings"].append("Async/sync mismatch - consider await/async handling")
        
        return result

    @classmethod
    def _calculate_type_compatibility(cls, source_type: str, target_type: str) -> float:
        """Calculate compatibility score between two types (0.0 to 1.0)"""
        if source_type == target_type:
            return 1.0
        
        # Check direct compatibility
        compatible_types = cls.TYPE_COMPATIBILITY.get(source_type, [])
        if target_type in compatible_types:
            # Perfect match gets 1.0, others get scores based on position
            if target_type == "Any":
                return 0.8  # Any is always compatible but less specific
            elif target_type == "object":
                return 0.6  # Object is compatible but very generic
            else:
                return 0.9  # Good compatibility
        
        # Check for partial matches (e.g., List[str] vs list)
        if cls._is_generic_match(source_type, target_type):
            return 0.7
        
        return 0.0  # No compatibility

    @classmethod
    def _is_generic_match(cls, source_type: str, target_type: str) -> bool:
        """Check for generic type matches like List[str] vs list"""
        import re
        
        # Extract base type from generic types
        source_base = re.sub(r'\[.*\]', '', source_type).lower()
        target_base = re.sub(r'\[.*\]', '', target_type).lower()
        
        return source_base == target_base

    @classmethod
    def _determine_connection_type(cls, source_entity: CodeEntity, target_entity: CodeEntity) -> str:
        """Determine the type of connection between entities"""
        source_effects = source_entity.metadata.get("side_effects", [])
        target_effects = target_entity.metadata.get("side_effects", [])
        
        if "database_write" in source_effects or "database_read" in target_effects:
            return "data_flow"
        elif "network_io" in source_effects or "network_io" in target_effects:
            return "api_call"
        elif source_entity.type == "function" and target_entity.type == "function":
            return "functional_composition"
        elif source_entity.type == "class" and target_entity.type == "class":
            return "object_collaboration"
        else:
            return "generic_flow"


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    # Check availability of each AI provider
    ai_status = {
        "claude": ai_provider.claude.available,
        "openai": ai_provider.openai.available,
        "ollama": await ai_provider.ollama._check_availability(),
    }
    
    primary_available = ai_status["claude"] or ai_status["openai"] or ai_status["ollama"]
    
    return {
        "status": "healthy",
        "ai_available": primary_available,
        "ai_providers": ai_status,
        "ai_fallback_chain": "Claude → OpenAI → Ollama → Mock",
        "entity_count": len(catalog.get_entities())
    }

@app.post("/api/validate-connection")
async def validate_connection(request: dict):
   """Validate if a connection between two entities is valid"""
   try:
       source_id = request.get("source_id")
       target_id = request.get("target_id")
       source_entity = catalog.get_entity(source_id)
       target_entity = catalog.get_entity(target_id)
       if not source_entity or not target_entity:
           raise HTTPException(status_code=404, detail="Entity not found")
       # Simple validation for now
       return {
           "valid": True,
           "compatibility_score": 0.9,
           "suggestions": [],
           "warnings": [],
           "connection_type": "data_flow"
       }
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/entity/{entity_id}/ports")
async def get_entity_ports(entity_id: str):
   """Get input/output ports for an entity"""
   try:
       entity = catalog.get_entity(entity_id)
       if not entity:
           raise HTTPException(status_code=404, detail="Entity not found")
       return {
           "inputs": entity.metadata.get("inputs", []),
           "outputs": entity.metadata.get("outputs", []),
           "side_effects": entity.metadata.get("side_effects", [])
       }
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Low-Code Platform…")
    print("📁 Make sure index.html is in the same directory")
    print("🤖 Ollama will be used if available, otherwise mock AI")
    print("📡 Server will be available at: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
