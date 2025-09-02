#!/usr/bin/env python3
"""
AIEvalEngine v3.0 - Multi-Model AI Jury System for Code and Document Evaluation
Enhanced with LLM-based document understanding and multi-round evaluation
"""

import os
import sys
import json
import sqlite3
import shutil
import zipfile
import tempfile
import logging
import argparse
import requests
import subprocess
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """Structured evaluation result"""
    category: str
    subcategory: str
    score: int
    max_score: int
    details: str
    evidence: List[str]
    recommendations: List[str]
    llm_analysis: Optional[str] = None

@dataclass
class ProjectMetadata:
    """Project metadata structure"""
    name: str
    type: str
    languages: List[str]
    frameworks: List[str]
    file_count: int
    has_tests: bool
    has_docs: bool
    has_ci: bool

class LayeredAIClient:
    """Client for layered AI services with fallback and multi-model support"""
    
    def __init__(self):
        load_dotenv()
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.ollama_host = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1')
        self.session = requests.Session()
        self.force_provider = None  # For multi-round evaluation
        self.force_model = None     # For specific model selection
        self.last_successful_model = None  # Track which model was used
        
        # Available models per provider
        self.available_models = {
            'claude': [
                'claude-3-5-sonnet-20241022',
                'claude-3-haiku-20240307', 
                'claude-3-opus-20240229'
            ],
            'openai': [
                'gpt-4o',
                'gpt-4',
                'gpt-4-turbo',
                'gpt-3.5-turbo'
            ],
            'ollama': self._get_ollama_models()
        }
    
    def _get_ollama_models(self) -> List[str]:
        """Get available Ollama models"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'].replace(':latest', '') for model in data.get('models', [])]
            else:
                return ['llama3.1']  # Fallback
        except:
            return ['llama3.1']  # Fallback
    
    def set_specific_model(self, provider: str, model: str):
        """Set specific model for evaluation"""
        self.force_provider = provider
        self.force_model = model
        
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000) -> str:
        """Generate response using layered AI services with fallback"""
        
        # Handle forced provider for multi-round evaluation
        if self.force_provider == 'claude':
            if self.anthropic_api_key:
                try:
                    model = self.force_model or 'claude-3-5-sonnet-20241022'
                    result = self._call_claude(prompt, system_prompt, max_tokens, model)
                    self.last_successful_model = model
                    return result
                except Exception as e:
                    raise Exception(f"Claude API failed: {e}")
            else:
                raise Exception("Claude API key not configured")
        
        elif self.force_provider == 'openai':
            if self.openai_api_key:
                try:
                    model = self.force_model or 'gpt-4'
                    result = self._call_openai(prompt, system_prompt, max_tokens, model)
                    self.last_successful_model = model
                    return result
                except Exception as e:
                    raise Exception(f"OpenAI API failed: {e}")
            else:
                raise Exception("OpenAI API key not configured")
        
        elif self.force_provider == 'ollama':
            try:
                model = self.force_model or self.ollama_model
                result = self._call_ollama(prompt, system_prompt, max_tokens, model)
                self.last_successful_model = model
                return result
            except Exception as e:
                raise Exception(f"Ollama API failed: {e}")
        
        # Default layered fallback behavior
        # Try Claude first
        if self.anthropic_api_key:
            try:
                result = self._call_claude(prompt, system_prompt, max_tokens)
                self.last_successful_model = 'claude-3-5-sonnet-20241022'
                return result
            except Exception as e:
                logger.warning(f"Claude API failed: {e}, falling back to OpenAI")
        
        # Try OpenAI second
        if self.openai_api_key:
            try:
                result = self._call_openai(prompt, system_prompt, max_tokens)
                self.last_successful_model = 'gpt-4'
                return result
            except Exception as e:
                logger.warning(f"OpenAI API failed: {e}, falling back to Ollama")
        
        # Fall back to Ollama
        try:
            result = self._call_ollama(prompt, system_prompt, max_tokens)
            self.last_successful_model = self.ollama_model
            return result
        except Exception as e:
            logger.error(f"All AI services failed. Last error: {e}")
            self.last_successful_model = 'error'
            return "Error: All AI services unavailable"
    
    def _call_claude(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000, model: str = None) -> str:
        """Call Claude API with correct format"""
        headers = {
            'x-api-key': self.anthropic_api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": model or "claude-3-5-sonnet-20241022",  # Use specified model or default
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        # Add system prompt as separate parameter (not in messages)
        if system_prompt:
            payload["system"] = system_prompt
        
        response = self.session.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()['content'][0]['text']
        else:
            raise Exception(f"Claude API error {response.status_code}: {response.text}")
    
    def _call_openai(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000, model: str = None) -> str:
        """Call OpenAI API"""
        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model or "gpt-4",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": 0.1
        }
        
        response = self.session.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            raise Exception(f"OpenAI API error {response.status_code}: {response.text}")
    
    def _call_ollama(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000, model: str = None) -> str:
        """Call Ollama API"""
        payload = {
            "model": model or self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = self.session.post(
            f"{self.ollama_host}/api/generate",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()['response']
        else:
            raise Exception(f"Ollama API error {response.status_code}: {response.text}")


class EvaluationDatabase:
    """Enhanced SQLite database for storing complete evaluation results including multi-round data"""
    
    def __init__(self, db_path: str = "aieval_results.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables for complete rubric storage and multi-round evaluation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create evaluations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                source_type TEXT NOT NULL,
                project_name TEXT,
                project_type TEXT,
                languages TEXT,
                frameworks TEXT,
                total_score INTEGER,
                max_score INTEGER,
                percentage REAL,
                grade TEXT,
                evaluation_date TEXT,
                llm_model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create detailed subcategory results table with percentage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER,
                category TEXT,
                subcategory TEXT,
                score INTEGER,
                max_score INTEGER,
                percentage REAL,
                details TEXT,
                evidence TEXT,
                recommendations TEXT,
                llm_analysis TEXT,
                FOREIGN KEY (evaluation_id) REFERENCES evaluations (id)
            )
        ''')
        
        # Create category scores table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS category_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER,
                category TEXT,
                total_score INTEGER,
                max_score INTEGER,
                percentage REAL,
                weight REAL,
                FOREIGN KEY (evaluation_id) REFERENCES evaluations (id)
            )
        ''')
        
        # Create rubric configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rubric_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER,
                rubric_version TEXT,
                total_points INTEGER,
                evaluation_type TEXT,
                rubric_json TEXT,
                FOREIGN KEY (evaluation_id) REFERENCES evaluations (id)
            )
        ''')
        
        # Create multi-round evaluation master table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS multiround_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                source_type TEXT NOT NULL,
                project_name TEXT,
                num_rounds INTEGER,
                providers TEXT,
                final_score REAL,
                final_grade TEXT,
                evaluation_date TEXT,
                document_analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create individual rounds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                multiround_id INTEGER,
                provider TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                model_name TEXT,
                total_score REAL,
                max_score INTEGER,
                percentage REAL,
                grade TEXT,
                evaluation_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (multiround_id) REFERENCES multiround_evaluations (id)
            )
        ''')
        
        # Create round category scores table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS round_category_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id INTEGER,
                category TEXT,
                score REAL,
                max_score INTEGER,
                percentage REAL,
                FOREIGN KEY (round_id) REFERENCES evaluation_rounds (id)
            )
        ''')
        
        # Create provider statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                multiround_id INTEGER,
                provider TEXT,
                avg_score REAL,
                min_score REAL,
                max_score REAL,
                std_deviation REAL,
                variance REAL,
                confidence_interval TEXT,
                num_rounds INTEGER,
                FOREIGN KEY (multiround_id) REFERENCES multiround_evaluations (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def save_multiround_evaluation(self, source_path: str, source_type: str, project_name: str, 
                                 num_rounds: int, providers: List[str], doc_analysis: str = None) -> int:
        """Save multi-round evaluation master record with document analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO multiround_evaluations 
            (source_path, source_type, project_name, num_rounds, providers, evaluation_date, document_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (source_path, source_type, project_name, num_rounds, 
              ','.join(providers), datetime.now().isoformat(), doc_analysis))
        
        multiround_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return multiround_id
    
    def save_evaluation_round(self, multiround_id: int, provider: str, round_num: int, 
                            model_name: str, results: Dict[str, Any], eval_time: float) -> int:
        """Save individual evaluation round results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_score = results['total_score']
        max_score = results['max_score']
        percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        cursor.execute('''
            INSERT INTO evaluation_rounds 
            (multiround_id, provider, round_number, model_name, total_score, max_score, 
             percentage, grade, evaluation_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (multiround_id, provider, round_num, model_name, total_score, max_score,
              percentage, results['grade'], eval_time))
        
        round_id = cursor.lastrowid
        
        # Save category scores for this round
        for category, category_result in results['detailed_results'].items():
            if isinstance(category_result, dict) and 'score' in category_result:
                cursor.execute('''
                    INSERT INTO round_category_scores 
                    (round_id, category, score, max_score, percentage)
                    VALUES (?, ?, ?, ?, ?)
                ''', (round_id, category, category_result['score'], 
                      category_result['max_score'], 
                      (category_result['score'] / category_result['max_score']) * 100))
        
        conn.commit()
        conn.close()
        return round_id
    
    def save_provider_statistics(self, multiround_id: int, provider: str, stats: Dict[str, Any]):
        """Save statistical analysis for provider performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO provider_statistics 
            (multiround_id, provider, avg_score, min_score, max_score, 
             std_deviation, variance, confidence_interval, num_rounds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (multiround_id, provider, stats['avg_score'], stats['min_score'],
              stats['max_score'], stats['std_deviation'], stats['variance'],
              f"{stats['confidence_interval'][0]:.1f}-{stats['confidence_interval'][1]:.1f}",
              stats['num_rounds']))
        
        conn.commit()
        conn.close()
    
    def finalize_multiround_evaluation(self, multiround_id: int, final_score: float, final_grade: str):
        """Update multiround evaluation with final averaged results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE multiround_evaluations 
            SET final_score = ?, final_grade = ?
            WHERE id = ?
        ''', (final_score, final_grade, multiround_id))
        
        conn.commit()
        conn.close()


class DocumentProcessor:
    """Handles document and repository processing with LLM-based understanding"""
    
    def __init__(self):
        self.temp_dir = None
        self.llm_client = LayeredAIClient()
    
    def process_repository(self, source: str, source_type: str = 'auto') -> tuple:
        """Process repository and analyze both code and documents"""
        
        if source_type == 'auto':
            source_type = self._detect_source_type(source)
        
        # Extract/prepare source
        if source_type == 'zip':
            project_path = self._extract_zip(source)
        elif source_type == 'git':
            project_path = self._clone_repo(source)
        elif source_type == 'directory':
            project_path = source
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        # Analyze structure (both code and documents)
        structure = self.analyze_structure(project_path)
        
        # Perform LLM-based document analysis
        doc_analysis = self.analyze_documents_with_llm(structure)
        structure['llm_document_analysis'] = doc_analysis
        
        # Create metadata
        metadata = ProjectMetadata(
            name=os.path.basename(project_path) if project_path != source else Path(source).name,
            type=self._detect_project_type(structure, doc_analysis),
            languages=list(structure['languages']),
            frameworks=list(structure['frameworks']),
            file_count=len(structure['files']),
            has_tests=len(structure['test_files']) > 0,
            has_docs=len(structure['doc_files']) > 0,
            has_ci=any('ci' in f.lower() or 'github' in f.lower() or 'gitlab' in f.lower()
                       for f in structure['files'])
        )
        
        return metadata, structure
    
    def analyze_documents_with_llm(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze and understand document structure and content"""
        if not structure['doc_files_content']:
            return {'document_analysis': 'No documents found for analysis'}
        
        # Prepare document summary for LLM analysis
        doc_summary = "=== DOCUMENT ANALYSIS REQUEST ===\n"
        doc_summary += f"Found {len(structure['doc_files_content'])} document files:\n"
        
        for file_path, content in structure['doc_files_content'].items():
            doc_summary += f"\n--- {file_path} ---\n"
            # Limit to first 200 lines for analysis
            lines = content.split('\n')[:200]
            doc_summary += '\n'.join(lines)
            if len(content.split('\n')) > 200:
                total_lines = len(content.split('\n'))
                doc_summary += f"\n... (truncated, total lines: {total_lines})"
            doc_summary += "\n"
        
        analysis_prompt = """Analyze these documents and provide a structured understanding:

1. DOCUMENT TYPE & PURPOSE:
   - What type of submission is this? (technical spec, project proposal, research paper, user manual, etc.)
   - What is the main purpose and intended audience?

2. CONTENT STRUCTURE:
   - How is the content organized? (sections, chapters, topics)
   - What are the main topics covered?
   - Is there a logical flow and hierarchy?

3. TECHNICAL DEPTH:
   - What is the technical complexity level?
   - Are there code examples, diagrams, specifications?
   - What domain/technology areas are covered?

4. COMPLETENESS ASSESSMENT:
   - Does this appear to be a complete submission?
   - Are there obvious gaps or missing sections?
   - What requirements might this be addressing?

5. QUALITY INDICATORS:
   - Writing clarity and professionalism
   - Use of supporting evidence/examples
   - Visual aids and formatting quality

Format your response as JSON:
{
  "document_type": "string",
  "purpose": "string", 
  "main_topics": ["topic1", "topic2"],
  "structure_quality": "poor|fair|good|excellent",
  "technical_depth": "basic|intermediate|advanced",
  "completeness": "incomplete|partial|complete",
  "quality_assessment": {
    "writing_clarity": "poor|fair|good|excellent",
    "technical_accuracy": "poor|fair|good|excellent", 
    "organization": "poor|fair|good|excellent",
    "evidence_support": "poor|fair|good|excellent"
  },
  "identified_gaps": ["gap1", "gap2"],
  "strengths": ["strength1", "strength2"],
  "evaluation_focus": ["focus_area1", "focus_area2"]
}"""

        try:
            response = self.llm_client.generate(analysis_prompt, doc_summary, max_tokens=3000)
            
            # Parse JSON response
            import json
            try:
                analysis = json.loads(response.strip())
                logger.info(f"LLM Document Analysis: {analysis.get('document_type', 'Unknown')} - {analysis.get('completeness', 'Unknown')}")
                return analysis
            except json.JSONDecodeError:
                # Fallback if LLM doesn't return valid JSON
                logger.warning("LLM returned non-JSON response, storing as text")
                return {
                    'document_analysis': response,
                    'analysis_method': 'llm_text_response'
                }
                
        except Exception as e:
            logger.warning(f"LLM document analysis failed: {e}")
            return {'document_analysis': 'LLM analysis unavailable'}

    def analyze_structure(self, project_path: str) -> Dict[str, Any]:
        """Analyze project structure including code and documents"""
        structure = {
            'files': [],
            'directories': [],
            'languages': set(),
            'frameworks': set(),
            'config_files': [],
            'test_files': [],
            'doc_files': [],
            'code_files': {},  # Store actual code content for LLM analysis
            'doc_files_content': {},  # Store document content for LLM analysis
            'file_sizes': {}
        }

        language_extensions = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
            '.go': 'Go', '.rs': 'Rust', '.php': 'PHP', '.rb': 'Ruby'
        }

        config_patterns = [
            'package.json', 'requirements.txt', 'pom.xml', 'Cargo.toml',
            'composer.json', 'Gemfile', 'go.mod', 'Dockerfile', 'docker-compose.yml',
            '.env', 'config.py', 'settings.py'
        ]

        test_patterns = ['test_', '_test.', 'spec_',
                         '_spec.', '/tests/', '/test/', '__tests__']
        doc_patterns = ['README', 'CHANGELOG', 'LICENSE', '/docs/', '/doc/', 
                        '.md', '.txt', '.pdf', '.docx', '.doc', '.rtf']

        for root, dirs, files in os.walk(project_path):
            # Skip hidden directories and common build/dependency folders
            dirs[:] = [d for d in dirs if not d.startswith('.') and
                       d not in ['node_modules', '__pycache__', 'target', 'build', 'dist', 'vendor']]

            for file in files:
                if file.startswith('.') and file not in ['.env', '.gitignore']:
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, project_path)

                # Skip large files
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > 1024 * 1024:  # Skip files > 1MB
                        continue
                    structure['file_sizes'][relative_path] = file_size
                except:
                    continue

                structure['files'].append(relative_path)

                # Detect language
                ext = Path(file).suffix.lower()
                if ext in language_extensions:
                    structure['languages'].add(language_extensions[ext])

                    # Store code content for LLM analysis (limit to reasonable size)
                    if file_size < 25000000:  # Only files < 25MB for LLM analysis
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                structure['code_files'][relative_path] = content
                        except:
                            pass

                # Detect config files
                if any(pattern in file.lower() for pattern in config_patterns):
                    structure['config_files'].append(relative_path)

                # Detect test files
                if any(pattern in relative_path.lower() for pattern in test_patterns):
                    structure['test_files'].append(relative_path)

                # Detect documentation files
                if any(pattern in relative_path.upper() for pattern in doc_patterns):
                    structure['doc_files'].append(relative_path)
                    
                    # Store document content for LLM analysis
                    if file_size < 25000000:  # Same limit as code files
                        try:
                            if file.lower().endswith(('.md', '.txt', '.rst')):
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    structure['doc_files_content'][relative_path] = content
                            elif file.lower().endswith('.pdf'):
                                # For PDF files, we'll need to extract text (placeholder for now)
                                structure['doc_files_content'][relative_path] = f"[PDF FILE: {relative_path}]"
                            elif file.lower().endswith(('.docx', '.doc')):
                                # For Word files, we'll need to extract text (placeholder for now)
                                structure['doc_files_content'][relative_path] = f"[WORD FILE: {relative_path}]"
                        except:
                            pass

        # Detect frameworks based on config files and code content
        self._detect_frameworks(structure, project_path)

        return structure

    def _detect_project_type(self, structure: Dict[str, Any], doc_analysis: Dict[str, Any] = None) -> str:
        """Detect project type based on structure and LLM document analysis"""
        
        # First check if LLM document analysis provides insight
        if doc_analysis and 'document_type' in doc_analysis:
            doc_type = doc_analysis['document_type'].lower()
            if any(keyword in doc_type for keyword in ['proposal', 'specification', 'research', 'manual', 'report']):
                return doc_type.replace(' ', '_')
        
        # Fallback to traditional code-based detection
        files = [f.lower() for f in structure['files']]
        
        # Web application indicators
        if any(f in files for f in ['package.json', 'index.html', 'app.js']):
            return 'web_application'
        
        # API/Backend indicators
        elif any(f in files for f in ['app.py', 'main.py', 'server.py', 'api.py']):
            return 'backend_application'
        
        # Library/Package indicators
        elif any(f in files for f in ['setup.py', '__init__.py', 'cargo.toml']):
            return 'library'
        
        # Documentation-heavy project
        elif len(structure['doc_files']) > len(structure.get('code_files', {})):
            return 'documentation_project'
        
        else:
            return 'mixed_project'

    def _detect_frameworks(self, structure: Dict[str, Any], project_path: str):
        """Detect frameworks based on configuration files and imports"""
        framework_indicators = {
            'Django': ['django', 'settings.py', 'manage.py'],
            'Flask': ['flask', 'app.py'],
            'FastAPI': ['fastapi', 'main.py'],
            'React': ['react', 'package.json', 'src/'],
            'Vue': ['vue', '@vue'],
            'Angular': ['angular', '@angular'],
            'Express': ['express', 'server.js'],
            'Spring': ['spring', 'pom.xml', '@SpringBootApplication'],
            'Laravel': ['laravel', 'composer.json', 'artisan']
        }

        detected_frameworks = set()

        # Check config files
        for config_file in structure['config_files']:
            if config_file in ['package.json', 'pom.xml', 'composer.json']:
                try:
                    config_path = os.path.join(project_path, config_file)
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        for framework, indicators in framework_indicators.items():
                            if any(indicator in content for indicator in indicators):
                                detected_frameworks.add(framework)
                except:
                    pass

        # Check code content
        for content in structure['code_files'].values():
            content_lower = content.lower()
            for framework, indicators in framework_indicators.items():
                if any(indicator in content_lower for indicator in indicators):
                    detected_frameworks.add(framework)

        structure['frameworks'] = detected_frameworks

    def get_code_sample(self, structure: Dict[str, Any], max_files: int = 5) -> str:
        """Get representative code and document sample for LLM analysis"""
        code_sample = "=== PROJECT STRUCTURE ===\n"

        # Add directory structure
        dirs = sorted(set(os.path.dirname(f)
                      for f in structure['files'] if '/' in f))
        for dir_name in dirs[:10]:  # Limit to 10 directories
            code_sample += f"📁 {dir_name}/\n"

        code_sample += f"\n=== FILE OVERVIEW ===\n"
        code_sample += f"Total files: {len(structure['files'])}\n"
        code_sample += f"Languages: {', '.join(structure['languages'])}\n"
        code_sample += f"Frameworks: {', '.join(structure['frameworks'])}\n"
        code_sample += f"Config files: {len(structure['config_files'])}\n"
        code_sample += f"Test files: {len(structure['test_files'])}\n"
        code_sample += f"Documentation files: {len(structure['doc_files'])}\n\n"

        # Add LLM document analysis if available
        if 'llm_document_analysis' in structure and structure['llm_document_analysis']:
            doc_analysis = structure['llm_document_analysis']
            code_sample += "=== LLM DOCUMENT ANALYSIS ===\n"
            if isinstance(doc_analysis, dict):
                code_sample += f"Document Type: {doc_analysis.get('document_type', 'Unknown')}\n"
                code_sample += f"Purpose: {doc_analysis.get('purpose', 'Not specified')}\n"
                code_sample += f"Technical Depth: {doc_analysis.get('technical_depth', 'Unknown')}\n"
                code_sample += f"Completeness: {doc_analysis.get('completeness', 'Unknown')}\n"
                code_sample += f"Main Topics: {', '.join(doc_analysis.get('main_topics', []))}\n"
                code_sample += f"Quality Assessment: {doc_analysis.get('quality_assessment', {})}\n"
                code_sample += f"Evaluation Focus: {', '.join(doc_analysis.get('evaluation_focus', []))}\n\n"
            else:
                code_sample += f"{doc_analysis}\n\n"

        # Add code samples
        code_sample += "=== CODE SAMPLES ===\n"
        important_patterns = ['main.py', 'app.py', 'index.js', 'server.js', '__init__.py', 'models.py']
        code_files = list(structure['code_files'].items())

        # Sort by importance
        def file_importance(item):
            file_path, content = item
            filename = os.path.basename(file_path)
            if any(pattern in filename.lower() for pattern in important_patterns):
                return 0  # High priority
            elif 'test' in file_path.lower():
                return 2  # Lower priority
            else:
                return 1  # Medium priority

        code_files.sort(key=file_importance)

        for file_path, content in code_files[:max_files]:
            code_sample += f"\n--- {file_path} ---\n"
            lines = content.split('\n')[:100]
            code_sample += '\n'.join(lines)
            if len(content.split('\n')) > 100:
                total_lines = len(content.split('\n'))
                code_sample += f"\n... (truncated, total lines: {total_lines})"
            code_sample += "\n"

        # Add documentation content
        if structure['doc_files_content']:
            code_sample += "\n=== DOCUMENTATION CONTENT ===\n"
            
            # Prioritize README and important docs
            doc_priority = ['README', 'readme', 'DOCUMENTATION', 'SPEC', 'PROPOSAL']
            doc_files = list(structure['doc_files_content'].items())
            
            def doc_importance(item):
                file_path, content = item
                filename = os.path.basename(file_path).upper()
                if any(pattern in filename for pattern in doc_priority):
                    return 0  # High priority
                else:
                    return 1  # Medium priority
            
            doc_files.sort(key=doc_importance)
            
            for file_path, content in doc_files[:max_files]:
                code_sample += f"\n--- {file_path} ---\n"
                # Limit content to first 150 lines for docs (more than code)
                lines = content.split('\n')[:150]
                code_sample += '\n'.join(lines)
                if len(content.split('\n')) > 150:
                    total_lines = len(content.split('\n'))
                    code_sample += f"\n... (truncated, total lines: {total_lines})"
                code_sample += "\n"

        return code_sample

    def _detect_source_type(self, source: str) -> str:
        """Auto-detect source type"""
        if source.endswith('.zip'):
            return 'zip'
        elif source.startswith('http') and ('github.com' in source or 'gitlab.com' in source):
            return 'git'
        elif os.path.isdir(source):
            return 'directory'
        else:
            raise ValueError(f"Cannot detect source type for: {source}")

    def _extract_zip(self, zip_path: str) -> str:
        """Extract zip file to temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
        
        # Find the main project directory
        extracted_items = os.listdir(self.temp_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(self.temp_dir, extracted_items[0])):
            return os.path.join(self.temp_dir, extracted_items[0])
        else:
            return self.temp_dir

    def _clone_repo(self, repo_url: str) -> str:
        """Clone git repository to temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(['git', 'clone', repo_url, self.temp_dir], 
                      check=True, capture_output=True)
        return self.temp_dir

    def cleanup(self):
        """Clean up temporary directories"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class AIEvalEngine:
    """Main evaluation engine with LLM-powered document understanding and multi-model jury system"""

    def __init__(self, rubric_path: Optional[str] = "AIEVAL-Rubric.json"):
        self.rubric_manager = RubricManager(rubric_path)
        self.doc_processor = DocumentProcessor()
        self.llm_client = LayeredAIClient()
        self.database = EvaluationDatabase()

    def evaluate_multiround_with_models(self, source: str, source_type: str = 'auto', 
                                       rounds: int = 3, provider_models: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """
        Perform multi-round evaluation with specific models per provider and LLM document understanding
        """
        import statistics
        import time
        
        if provider_models is None:
            provider_models = {'claude': [], 'openai': []}
        
        # Expand models using defaults where needed
        expanded_models = []
        for provider, models in provider_models.items():
            if not models:  # Use default models
                models = self.llm_client.available_models.get(provider, [provider])
            
            for model in models:
                expanded_models.append((provider, model))
        
        total_evaluations = len(expanded_models) * rounds
        print(f"🎯 Starting evaluation with {len(expanded_models)} models, {rounds} rounds each ({total_evaluations} total evaluations)")
        
        # Process repository and documents
        try:
            metadata, structure = self.doc_processor.process_repository(source, source_type)
            project_name = metadata.name
            
            # Store document analysis
            doc_analysis_json = json.dumps(structure.get('llm_document_analysis', {}))
            
            # Create multi-round evaluation record
            providers_list = list(provider_models.keys())
            multiround_id = self.database.save_multiround_evaluation(
                source, source_type, project_name, rounds, providers_list, doc_analysis_json)
            
            model_results = {}
            provider_results = {}
            all_round_data = []
            
            # Run evaluation rounds for each model
            for provider, model in expanded_models:
                model_key = f"{provider}:{model}"
                print(f"\n🤖 Running {rounds} rounds with {model_key}...")
                model_scores = []
                
                for round_num in range(1, rounds + 1):
                    print(f"   Round {round_num}/{rounds}...", end=" ")
                    start_time = time.time()
                    
                    # Set specific model for this evaluation
                    self.llm_client.set_specific_model(provider, model)
                    
                    # Run single evaluation with document understanding
                    round_result = self._evaluate_single_round_with_docs(metadata, structure)
                    eval_time = time.time() - start_time
                    
                    # Save round to database
                    round_id = self.database.save_evaluation_round(
                        multiround_id, provider, round_num, model,
                        round_result, eval_time)
                    
                    model_scores.append(round_result['total_score'])
                    all_round_data.append({
                        'provider': provider,
                        'model': model,
                        'round': round_num,
                        'score': round_result['total_score'],
                        'result': round_result
                    })
                    
                    print(f"Score: {round_result['total_score']:.1f}")
                
                # Calculate model statistics
                if len(model_scores) > 1:
                    model_stats = {
                        'avg_score': statistics.mean(model_scores),
                        'min_score': min(model_scores),
                        'max_score': max(model_scores),
                        'std_deviation': statistics.stdev(model_scores),
                        'variance': statistics.variance(model_scores),
                        'confidence_interval': self._calculate_confidence_interval(model_scores),
                        'num_rounds': len(model_scores)
                    }
                else:
                    model_stats = {
                        'avg_score': model_scores[0],
                        'min_score': model_scores[0],
                        'max_score': model_scores[0],
                        'std_deviation': 0.0,
                        'variance': 0.0,
                        'confidence_interval': (model_scores[0], model_scores[0]),
                        'num_rounds': 1
                    }
                
                model_results[model_key] = model_stats
                self.database.save_provider_statistics(multiround_id, model_key, model_stats)
                
                print(f"   {model_key} Average: {model_stats['avg_score']:.1f} ± {model_stats['std_deviation']:.1f}")
            
            # Calculate provider-level averages
            for provider in providers_list:
                provider_model_results = [stats for key, stats in model_results.items() if key.startswith(f"{provider}:")]
                if provider_model_results:
                    provider_avg = statistics.mean([stats['avg_score'] for stats in provider_model_results])
                    provider_results[provider] = {
                        'avg_score': provider_avg,
                        'models': [key.split(':', 1)[1] for key in model_results.keys() if key.startswith(f"{provider}:")],
                        'model_stats': {key: stats for key, stats in model_results.items() if key.startswith(f"{provider}:")}
                    }
            
            # Calculate final overall score
            overall_avg = statistics.mean([stats['avg_score'] for stats in model_results.values()])
            final_grade = self.rubric_manager.get_grade(int(overall_avg))
            
            # Finalize multiround evaluation
            self.database.finalize_multiround_evaluation(multiround_id, overall_avg, final_grade)
            
            return {
                'multiround_id': multiround_id,
                'source': source,
                'project_name': project_name,
                'rounds': rounds,
                'provider_models': provider_models,
                'model_results': model_results,
                'provider_results': provider_results,
                'final_score': overall_avg,
                'final_grade': final_grade,
                'all_rounds': all_round_data,
                'total_evaluations': total_evaluations,
                'document_analysis': structure.get('llm_document_analysis', {}),
                'metadata': {
                    'name': metadata.name,
                    'type': metadata.type,
                    'languages': metadata.languages,
                    'frameworks': metadata.frameworks,
                    'file_count': metadata.file_count,
                    'has_tests': metadata.has_tests,
                    'has_docs': metadata.has_docs,
                    'has_ci': metadata.has_ci
                }
            }
            
        except Exception as e:
            logger.error(f"Multi-round evaluation failed: {e}")
            raise
        finally:
            self.doc_processor.cleanup()
            self.llm_client.force_provider = None
            self.llm_client.force_model = None

    def _evaluate_single_round_with_docs(self, metadata, structure) -> Dict[str, Any]:
        """Perform a single evaluation round with document-aware evaluation"""
        all_results = []
        total_score = 0
        max_total_score = 0
        
        # Get document context for adaptive evaluation
        doc_analysis = structure.get('llm_document_analysis', {})
        
        # Determine which evaluators to use based on content
        use_code_evaluators = len(structure.get('code_files', {})) > 0
        use_doc_evaluators = len(structure.get('doc_files_content', {})) > 0
        
        # Run evaluations based on content type
        evaluators_to_run = {}
        
        if use_code_evaluators:
            evaluators_to_run.update({
                'architecture_design': ArchitectureLLMEvaluator,
                'code_quality': CodeQualityLLMEvaluator,
                'functionality_requirements': FunctionalityLLMEvaluator,
            })
        
        if use_doc_evaluators:
            evaluators_to_run.update({
                'documentation_quality': DocumentationLLMEvaluator,
                'content_quality': ContentQualityLLMEvaluator,
                'presentation_format': PresentationLLMEvaluator,
                'requirements_compliance': RequirementsLLMEvaluator,
            })
        
        # Run all applicable evaluations
        for category, evaluator_class in evaluators_to_run.items():
            try:
                evaluator = evaluator_class(self.llm_client, structure)
                results = evaluator.evaluate()
                all_results.extend(results)
                
                category_score = sum(r.score for r in results)
                category_max = sum(r.max_score for r in results)
                total_score += category_score
                max_total_score += category_max
                
            except Exception as e:
                logger.error(f"Error in {category}: {e}")
        
        final_percentage = (total_score / max_total_score * 100) if max_total_score > 0 else 0
        grade = self.rubric_manager.get_grade(int(final_percentage))
        
        return {
            'total_score': total_score,
            'max_score': max_total_score,
            'percentage': final_percentage,
            'grade': grade,
            'detailed_results': {r.category: {
                'score': r.score,
                'max_score': r.max_score,
                'details': r.details,
                'evidence': r.evidence,
                'recommendations': r.recommendations
            } for r in all_results},
            'document_context': doc_analysis
        }
    
    def _calculate_confidence_interval(self, scores: List[float], confidence: float = 0.95) -> tuple:
        """Calculate confidence interval for scores"""
        if len(scores) < 2:
            return (scores[0], scores[0])
        
        import math
        import statistics
        mean = statistics.mean(scores)
        std_dev = statistics.stdev(scores)
        n = len(scores)
        
        # Simple approximation for 95% confidence interval
        margin = 1.96 * (std_dev / math.sqrt(n))
        return (mean - margin, mean + margin)


# Simplified evaluator classes for the new system
class LLMEvaluator(ABC):
    """Base class for LLM-powered evaluators"""
    
    def __init__(self, llm_client: LayeredAIClient, structure: Dict[str, Any]):
        self.llm_client = llm_client
        self.structure = structure
    
    @abstractmethod
    def get_llm_prompt(self) -> str:
        """Get the LLM prompt for this evaluation category"""
        pass
    
    def evaluate(self) -> List[EvaluationResult]:
        """Evaluate using LLM analysis"""
        prompt = self.get_llm_prompt()
        code_sample = self._get_analysis_content()
        
        try:
            response = self.llm_client.generate(prompt, code_sample, max_tokens=2000)
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return self._fallback_evaluation()
    
    def _get_analysis_content(self) -> str:
        """Get relevant content for analysis"""
        content = "=== PROJECT ANALYSIS ===\n"
        
        # Add document analysis context
        if 'llm_document_analysis' in self.structure:
            doc_analysis = self.structure['llm_document_analysis']
            content += "=== DOCUMENT UNDERSTANDING ===\n"
            if isinstance(doc_analysis, dict):
                content += f"Type: {doc_analysis.get('document_type', 'Unknown')}\n"
                content += f"Purpose: {doc_analysis.get('purpose', 'Not specified')}\n"
                content += f"Topics: {', '.join(doc_analysis.get('main_topics', []))}\n"
                content += f"Quality: {doc_analysis.get('quality_assessment', {})}\n\n"
        
        # Add both code and document content
        content += f"Files: {len(self.structure['files'])}\n"
        content += f"Languages: {', '.join(self.structure['languages'])}\n"
        content += f"Documentation files: {len(self.structure.get('doc_files_content', {}))}\n"
        content += f"Code files: {len(self.structure.get('code_files', {}))}\n\n"
        
        # Add sample content (both code and docs)
        if self.structure.get('code_files'):
            content += "=== CODE SAMPLES ===\n"
            for file_path, file_content in list(self.structure['code_files'].items())[:3]:
                content += f"\n--- {file_path} ---\n"
                lines = file_content.split('\n')[:50]
                content += '\n'.join(lines) + "\n"
        
        if self.structure.get('doc_files_content'):
            content += "\n=== DOCUMENT SAMPLES ===\n"
            for file_path, file_content in list(self.structure['doc_files_content'].items())[:3]:
                content += f"\n--- {file_path} ---\n"
                lines = file_content.split('\n')[:100]
                content += '\n'.join(lines) + "\n"
        
        return content
    
    def _parse_llm_response(self, response: str) -> List[EvaluationResult]:
        """Parse LLM response into evaluation results"""
        # Simple parsing - look for SCORE: pattern
        try:
            score_line = [line for line in response.split('\n') if 'SCORE:' in line.upper()]
            if score_line:
                score_text = score_line[0].split('SCORE:')[1].strip()
                if '/' in score_text:
                    score, max_score = score_text.split('/')
                    score = int(score.strip())
                    max_score = int(max_score.strip())
                else:
                    score = int(score_text.strip())
                    max_score = self._get_default_max_score()
            else:
                score, max_score = 0, self._get_default_max_score()
            
            evidence = self._extract_section(response, 'EVIDENCE:')
            recommendations = self._extract_section(response, 'RECOMMENDATIONS:')
            analysis = self._extract_section(response, 'ANALYSIS:')
            
            return [EvaluationResult(
                category=self._get_category_name(),
                subcategory="comprehensive",
                score=score,
                max_score=max_score,
                details=f"LLM evaluation: {score}/{max_score}",
                evidence=evidence,
                recommendations=recommendations,
                llm_analysis=analysis[0] if analysis else response[:500]
            )]
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._fallback_evaluation()
    
    def _extract_section(self, text: str, section_header: str) -> List[str]:
        """Extract bullet points from a section"""
        lines = text.split('\n')
        in_section = False
        items = []
        
        for line in lines:
            if section_header in line.upper():
                in_section = True
                continue
            elif in_section and line.strip().startswith('- '):
                items.append(line.strip()[2:])
            elif in_section and line.strip() and not line.strip().startswith('-'):
                break
        
        return items
    
    @abstractmethod
    def _get_category_name(self) -> str:
        """Get the category name for this evaluator"""
        pass
    
    @abstractmethod
    def _get_default_max_score(self) -> int:
        """Get default max score for this category"""
        pass
    
    @abstractmethod
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        """Fallback evaluation if LLM fails"""
        pass


class DocumentationLLMEvaluator(LLMEvaluator):
    """Enhanced documentation quality evaluation using LLM with document understanding"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating DOCUMENTATION QUALITY for a submission.

        Consider both standalone documents and code documentation.
        Use the document analysis context to adapt your evaluation approach.
        
        Focus on documentation_quality aspects:
        - README quality and completeness
        - Code comments and inline documentation  
        - API documentation clarity
        - Setup and installation instructions
        - Architecture documentation
        - Document structure and organization
        
        Provide specific, actionable feedback with concrete examples from the content.
        
        SCORE: [0-25]
        EVIDENCE:
        - [Specific positive findings with examples]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed documentation analysis]"""
    
    def _get_category_name(self) -> str:
        return "documentation_quality"
    
    def _get_default_max_score(self) -> int:
        return 25
    
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        return [EvaluationResult(
            category="documentation_quality", subcategory="comprehensive",
            score=10, max_score=25, details="Fallback evaluation",
            evidence=["Basic documentation present"], recommendations=["Improve documentation quality"]
        )]


class ContentQualityLLMEvaluator(LLMEvaluator):
    """Content quality evaluation for documented submissions"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating CONTENT QUALITY for a submission.

        Use the document analysis context to understand the submission type and adapt evaluation.
        
        Focus on content_quality aspects:
        - Clarity of writing and communication
        - Completeness of topic coverage
        - Technical accuracy of information
        - Appropriate depth and detail level
        - Supporting examples and evidence
        
        Provide specific feedback on content strengths and areas for improvement.
        
        SCORE: [0-30]
        EVIDENCE:
        - [Specific positive findings with examples]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed content analysis]"""
    
    def _get_category_name(self) -> str:
        return "content_quality"
    
    def _get_default_max_score(self) -> int:
        return 30
    
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        return [EvaluationResult(
            category="content_quality", subcategory="comprehensive",
            score=15, max_score=30, details="Fallback evaluation",
            evidence=["Content present"], recommendations=["Improve content quality"]
        )]


class PresentationLLMEvaluator(LLMEvaluator):
    """Presentation and formatting evaluation"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating PRESENTATION AND FORMAT quality.

        Analyze visual presentation, formatting, and overall appearance.
        Adapt based on submission type (documents vs code).
        
        Focus on presentation_format aspects:
        - Consistent formatting and styling
        - Visual aids (diagrams, charts, images)
        - Readability (font, spacing, layout)
        - Professional appearance and polish
        
        SCORE: [0-18]
        EVIDENCE:
        - [Specific positive findings]
        RECOMMENDATIONS:
        - [Specific improvements]
        ANALYSIS: [Detailed presentation analysis]"""
    
    def _get_category_name(self) -> str:
        return "presentation_format"
    
    def _get_default_max_score(self) -> int:
        return 18
    
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        return [EvaluationResult(
            category="presentation_format", subcategory="comprehensive",
            score=9, max_score=18, details="Fallback evaluation",
            evidence=["Basic formatting present"], recommendations=["Improve presentation"]
        )]


class RequirementsLLMEvaluator(LLMEvaluator):
    """Requirements compliance evaluation with LLM understanding"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating REQUIREMENTS COMPLIANCE.

        Use document analysis context to understand what requirements this submission addresses.
        
        Focus on requirements_compliance aspects:
        - All requirements addressed and covered
        - Adherence to given specifications
        - Completeness of requested deliverables
        - Following submission format and guidelines
        
        SCORE: [0-22]
        EVIDENCE:
        - [Specific requirement fulfillments]
        RECOMMENDATIONS:
        - [Missing requirements]
        ANALYSIS: [Requirements analysis]"""
    
    def _get_category_name(self) -> str:
        return "requirements_compliance"
    
    def _get_default_max_score(self) -> int:
        return 22
    
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        return [EvaluationResult(
            category="requirements_compliance", subcategory="comprehensive",
            score=11, max_score=22, details="Fallback evaluation",
            evidence=["Basic requirements met"], recommendations=["Clarify requirements coverage"]
        )]


# Simplified code evaluators
class ArchitectureLLMEvaluator(LLMEvaluator):
    def get_llm_prompt(self) -> str:
        return """Evaluate ARCHITECTURE DESIGN aspects.
        SCORE: [0-35]
        EVIDENCE: [Positive findings]
        RECOMMENDATIONS: [Improvements]
        ANALYSIS: [Technical analysis]"""
    
    def _get_category_name(self) -> str:
        return "architecture_design"
    
    def _get_default_max_score(self) -> int:
        return 35
    
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        return [EvaluationResult("architecture_design", "comprehensive", 17, 35, "Fallback", [], [])]


class CodeQualityLLMEvaluator(LLMEvaluator):
    def get_llm_prompt(self) -> str:
        return """Evaluate CODE QUALITY aspects.
        SCORE: [0-30]
        EVIDENCE: [Positive findings]
        RECOMMENDATIONS: [Improvements]
        ANALYSIS: [Quality analysis]"""
    
    def _get_category_name(self) -> str:
        return "code_quality"
    
    def _get_default_max_score(self) -> int:
        return 30
    
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        return [EvaluationResult("code_quality", "comprehensive", 15, 30, "Fallback", [], [])]


class FunctionalityLLMEvaluator(LLMEvaluator):
    def get_llm_prompt(self) -> str:
        return """Evaluate FUNCTIONALITY REQUIREMENTS.
        SCORE: [0-25]
        EVIDENCE: [Positive findings]
        RECOMMENDATIONS: [Improvements]
        ANALYSIS: [Functionality analysis]"""
    
    def _get_category_name(self) -> str:
        return "functionality_requirements"
    
    def _get_default_max_score(self) -> int:
        return 25
    
    def _fallback_evaluation(self) -> List[EvaluationResult]:
        return [EvaluationResult("functionality_requirements", "comprehensive", 12, 25, "Fallback", [], [])]


class RubricManager:
    """Manages evaluation rubric and scoring"""

    def __init__(self, rubric_path: Optional[str] = None):
        self.rubric = self._load_default_rubric() if not rubric_path else self._load_rubric(rubric_path)

    def _load_default_rubric(self) -> Dict[str, Any]:
        """Load enhanced rubric for hybrid code/document evaluation"""
        return {
            "repository_evaluation_rubric": {
                "metadata": {
                    "version": "4.0",
                    "total_points": 220,
                    "evaluation_type": "hybrid_code_document",
                    "description": "AI Jury System for Code and Document Evaluation"
                },
                "categories": {
                    "architecture_design": {"weight": 0.16, "max_points": 35},
                    "code_quality": {"weight": 0.14, "max_points": 30},
                    "functionality_requirements": {"weight": 0.11, "max_points": 25},
                    "documentation_quality": {"weight": 0.11, "max_points": 25},
                    "content_quality": {"weight": 0.14, "max_points": 30},
                    "presentation_format": {"weight": 0.08, "max_points": 18},
                    "requirements_compliance": {"weight": 0.10, "max_points": 22},
                    "testing_quality": {"weight": 0.08, "max_points": 18},
                    "devops_deployment": {"weight": 0.05, "max_points": 12},
                    "security_compliance": {"weight": 0.02, "max_points": 5}
                }
            }
        }

    def _load_rubric(self, rubric_path: str) -> Dict[str, Any]:
        """Load rubric from file"""
        try:
            with open(rubric_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load rubric from {rubric_path}: {e}")
            return self._load_default_rubric()

    def get_grade(self, percentage: int) -> str:
        """Convert percentage to letter grade"""
        if percentage >= 95: return "A+"
        elif percentage >= 90: return "A"
        elif percentage >= 85: return "A-"
        elif percentage >= 80: return "B+"
        elif percentage >= 75: return "B"
        elif percentage >= 70: return "B-"
        elif percentage >= 65: return "C+"
        elif percentage >= 60: return "C"
        elif percentage >= 55: return "C-"
        elif percentage >= 50: return "D"
        else: return "F"


def parse_provider_models(providers_str: str) -> Dict[str, List[str]]:
    """Parse provider:model1,model2 format into dictionary"""
    provider_models = {}
    
    for part in providers_str.split():
        part = part.strip()
        if ':' in part:
            provider, models_str = part.split(':', 1)
            models = [m.strip() for m in models_str.split(',')]
            provider_models[provider] = models
        else:
            # Just provider name, use default models
            provider_models[part] = []
    
    return provider_models


def format_multiround_report(results: Dict[str, Any]) -> str:
    """Format multi-round evaluation results"""
    lines = []
    
    lines.append("=" * 80)
    lines.append("🎯 AI JURY EVALUATION RESULTS")
    lines.append("=" * 80)
    lines.append(f"📁 Project: {results['project_name']}")
    lines.append(f"📊 Rounds: {results['rounds']} per model")
    lines.append(f"🤖 Total Evaluations: {results['total_evaluations']}")
    lines.append(f"📈 Final Score: {results['final_score']:.1f}/220 ({results['final_score']/220*100:.1f}%)")
    lines.append(f"🏆 Final Grade: {results['final_grade']}")
    
    # Show document analysis if available
    if 'document_analysis' in results and results['document_analysis']:
        doc_analysis = results['document_analysis']
        if isinstance(doc_analysis, dict):
            lines.append(f"\n📄 Document Type: {doc_analysis.get('document_type', 'Unknown')}")
            lines.append(f"🎯 Purpose: {doc_analysis.get('purpose', 'Not specified')}")
            lines.append(f"📊 Completeness: {doc_analysis.get('completeness', 'Unknown')}")
    
    lines.append("")
    
    # Model-Level Statistics
    lines.append("🤖 MODEL PERFORMANCE STATISTICS:")
    lines.append("-" * 80)
    for model_key, stats in results['model_results'].items():
        lines.append(f"{model_key:>25}: {stats['avg_score']:5.1f} ± {stats['std_deviation']:4.1f}")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append(f"💾 Evaluation ID: {results['multiround_id']}")
    lines.append("=" * 80)
    
    return '\n'.join(lines)


def show_multiround_history(db_path: str, limit: int = 5):
    """Show multi-round evaluation history"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get multiround evaluations
        if limit == 0:
            cursor.execute('''
                SELECT * FROM multiround_evaluations 
                ORDER BY created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT * FROM multiround_evaluations 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
        
        evaluations = cursor.fetchall()
        
        if not evaluations:
            print("📊 No multi-round evaluations found.")
            conn.close()
            return
        
        print("📊 AI JURY EVALUATION HISTORY")
        print("=" * 80)
        
        columns = [desc[0] for desc in cursor.description]
        
        for eval_row in evaluations:
            eval_dict = dict(zip(columns, eval_row))
            eval_id = eval_dict['id']
            
            print(f"\n🎯 EVALUATION #{eval_id}: {eval_dict['project_name']}")
            print(f"   Source: {eval_dict['source_path']}")
            final_score = eval_dict.get('final_score') or 0
            final_grade = eval_dict.get('final_grade') or 'N/A'
            print(f"   Final Score: {final_score:.1f}/220 ({final_score/220*100:.1f}%) - Grade: {final_grade}")
            print(f"   Rounds: {eval_dict['num_rounds']} | Providers: {eval_dict['providers']}")
            print(f"   Date: {eval_dict['evaluation_date'][:10]}")
            
            # Get provider statistics
            cursor.execute('''
                SELECT provider, avg_score, std_deviation, num_rounds 
                FROM provider_statistics WHERE multiround_id = ?
            ''', (eval_id,))
            
            provider_stats = cursor.fetchall()
            if provider_stats:
                print(f"   📊 Provider Performance:")
                for provider, avg_score, std_dev, rounds in provider_stats:
                    print(f"      {provider:>25}: {avg_score:5.1f} ± {std_dev:4.1f}")
        
        print(f"\n📈 Total evaluations found: {len(evaluations)}")
        print("=" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error reading history: {e}")


def main():
    parser = argparse.ArgumentParser(description='AI Jury Evaluation Engine v3.0')
    parser.add_argument('source', nargs='?', help='Source to evaluate (directory, zip, or git URL)')
    parser.add_argument('--type', choices=['auto', 'zip', 'git', 'directory'], default='auto')
    parser.add_argument('--rubric', help='Path to custom rubric JSON file')
    parser.add_argument('--multiround', action='store_true', help='Use multi-round evaluation with AI jury')
    parser.add_argument('--rounds', type=int, default=3, help='Number of evaluation rounds per model')
    parser.add_argument('--providers', default='claude:claude-3-5-sonnet-20241022 openai:gpt-4', 
                       help='Provider and model specification. Format: provider:model1,model2')
    parser.add_argument('--history', action='store_true', help='Show evaluation history')
    parser.add_argument('--limit', type=int, default=5, help='Number of history records')
    parser.add_argument('--db-path', default='aieval_results.db', help='Database path')

    args = parser.parse_args()

    if args.history:
        show_multiround_history(args.db_path, args.limit)
        return 0

    if not args.source:
        parser.error("source is required unless using --history")

    try:
        engine = AIEvalEngine(args.rubric)
        
        if args.multiround:
            provider_models = parse_provider_models(args.providers)
            print(f"🎯 Starting AI Jury evaluation...")
            results = engine.evaluate_multiround_with_models(args.source, args.type, args.rounds, provider_models)
            print("\n" + format_multiround_report(results))
        else:
            print("Single evaluation mode not implemented in v3 - use --multiround")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())