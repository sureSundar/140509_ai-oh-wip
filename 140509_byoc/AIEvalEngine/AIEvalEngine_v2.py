#!/usr/bin/env python3
"""
Enhanced AI EvalEngine v2 with Layered AI Services and Complete Persistence
A comprehensive tool for evaluating software repositories using Claude -> OpenAI -> Ollama fallback.
"""

import json
import os
import zipfile
import tempfile
import shutil
import subprocess
import re
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import logging
from datetime import datetime
import time
import sqlite3
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AIEVALENGINE")


@dataclass
class EvaluationResult:
    """Data class for storing evaluation results"""
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
    """Data class for project metadata"""
    name: str
    type: str
    languages: List[str]
    frameworks: List[str]
    size_loc: int
    file_count: int
    has_tests: bool
    has_docs: bool
    has_ci: bool


class LayeredAIClient:
    """Client for layered AI services with fallback: Claude -> OpenAI -> Ollama"""
    
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
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result['content'][0]['text']
    
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
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
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
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', '').strip()


class EvaluationDatabase:
    """Enhanced SQLite database for storing complete evaluation results"""
    
    def __init__(self, db_path: str = "aieval_results.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables for complete rubric storage"""
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
    
    def save_evaluation(self, source_path: str, source_type: str, results: Dict[str, Any], rubric: Dict[str, Any] = None) -> int:
        """Save complete evaluation results including full rubric scores to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata = results['metadata']
        summary = results['evaluation_summary']
        
        # Insert main evaluation record
        cursor.execute('''
            INSERT INTO evaluations (
                source_path, source_type, project_name, project_type,
                languages, frameworks, total_score, max_score,
                percentage, grade, evaluation_date, llm_model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            source_path, source_type, metadata['name'], metadata['type'],
            ','.join(metadata['languages']), ','.join(metadata['frameworks']),
            summary['total_score'], summary['max_score'], summary['percentage'],
            summary['grade'], summary['evaluation_date'], summary.get('llm_model', 'layered_ai')
        ))
        
        evaluation_id = cursor.lastrowid
        
        # Save rubric configuration if provided
        if rubric:
            rubric_meta = rubric.get('repository_evaluation_rubric', {}).get('metadata', {})
            cursor.execute('''
                INSERT INTO rubric_configs (
                    evaluation_id, rubric_version, total_points, evaluation_type, rubric_json
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                evaluation_id, rubric_meta.get('version', ''), rubric_meta.get('total_points', 0),
                rubric_meta.get('evaluation_type', ''), json.dumps(rubric)
            ))
        
        # Save category scores with weights
        if 'category_scores' in results:
            for category, score_info in results['category_scores'].items():
                weight = 0.0
                if rubric:
                    rubric_category = rubric.get('repository_evaluation_rubric', {}).get('categories', {}).get(category, {})
                    weight = rubric_category.get('weight', 0.0)
                
                cursor.execute('''
                    INSERT INTO category_scores (
                        evaluation_id, category, total_score, max_score, percentage, weight
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    evaluation_id, category, score_info['score'], score_info['max_score'],
                    score_info['percentage'], weight
                ))
        
        # Insert detailed subcategory results with percentages
        for result in results['detailed_results']:
            percentage = (result['score'] / result['max_score'] * 100) if result['max_score'] > 0 else 0
            cursor.execute('''
                INSERT INTO evaluation_details (
                    evaluation_id, category, subcategory, score, max_score,
                    percentage, details, evidence, recommendations, llm_analysis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                evaluation_id, result['category'], result['subcategory'],
                result['score'], result['max_score'], percentage, result['details'],
                ','.join(result['evidence']), ','.join(result['recommendations']),
                result.get('llm_analysis', '')
            ))
        
        conn.commit()
        conn.close()
        
        return evaluation_id
    
    def get_evaluation_history(self, limit: int = 10, source_filter: str = None) -> List[Dict[str, Any]]:
        """Get recent evaluation history with complete rubric breakdown"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if source_filter:
            if limit:
                cursor.execute('''
                    SELECT * FROM evaluations 
                    WHERE source_path LIKE ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (f'%{source_filter}%', limit))
            else:
                cursor.execute('''
                    SELECT * FROM evaluations 
                    WHERE source_path LIKE ?
                    ORDER BY created_at DESC
                ''', (f'%{source_filter}%',))
        else:
            if limit:
                cursor.execute('''
                    SELECT * FROM evaluations 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT * FROM evaluations 
                    ORDER BY created_at DESC
                ''')
        
        columns = [description[0] for description in cursor.description]
        evaluations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Get detailed breakdown for each evaluation
        for evaluation in evaluations:
            eval_id = evaluation['id']
            
            # Get category scores
            cursor.execute('''
                SELECT category, total_score, max_score, percentage, weight 
                FROM category_scores WHERE evaluation_id = ? ORDER BY weight DESC
            ''', (eval_id,))
            category_columns = ['category', 'total_score', 'max_score', 'percentage', 'weight']
            evaluation['category_breakdown'] = [dict(zip(category_columns, row)) for row in cursor.fetchall()]
            
            # Get subcategory scores
            cursor.execute('''
                SELECT category, subcategory, score, max_score, percentage 
                FROM evaluation_details WHERE evaluation_id = ? ORDER BY category, subcategory
            ''', (eval_id,))
            sub_columns = ['category', 'subcategory', 'score', 'max_score', 'percentage']
            evaluation['subcategory_breakdown'] = [dict(zip(sub_columns, row)) for row in cursor.fetchall()]
            
            # Get rubric info
            cursor.execute('''
                SELECT rubric_version, total_points, evaluation_type 
                FROM rubric_configs WHERE evaluation_id = ?
            ''', (eval_id,))
            rubric_info = cursor.fetchone()
            if rubric_info:
                evaluation['rubric_info'] = {
                    'version': rubric_info[0],
                    'total_points': rubric_info[1], 
                    'evaluation_type': rubric_info[2]
                }
        
        conn.close()
        return evaluations
    
    def save_multiround_evaluation(self, source_path: str, source_type: str, project_name: str, 
                                 num_rounds: int, providers: List[str]) -> int:
        """Save multi-round evaluation master record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO multiround_evaluations 
            (source_path, source_type, project_name, num_rounds, providers, evaluation_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (source_path, source_type, project_name, num_rounds, 
              ','.join(providers), datetime.now().isoformat()))
        
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


class RepositoryProcessor:
    """Handles repository extraction and analysis"""

    def __init__(self):
        self.temp_dir = None
        self.project_root = None

    def process_zip(self, zip_path: str) -> str:
        """Extract zip file and return project root path"""
        self.temp_dir = tempfile.mkdtemp()

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)

        # Find the actual project root (handle nested folders)
        items = os.listdir(self.temp_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(self.temp_dir, items[0])):
            self.project_root = os.path.join(self.temp_dir, items[0])
        else:
            self.project_root = self.temp_dir

        return self.project_root

    def process_git_repo(self, repo_url: str) -> str:
        """Clone git repository and return project root path"""
        self.temp_dir = tempfile.mkdtemp()

        try:
            subprocess.run(['git', 'clone', repo_url, self.temp_dir],
                           check=True, capture_output=True)
            self.project_root = self.temp_dir
            return self.project_root
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to clone repository: {e}")
            
    def process_directory(self, dir_path: str) -> str:
        """Process local directory and return project root path"""
        if not os.path.exists(dir_path):
            raise Exception(f"Directory does not exist: {dir_path}")
        
        if not os.path.isdir(dir_path):
            raise Exception(f"Path is not a directory: {dir_path}")
            
        self.project_root = os.path.abspath(dir_path)
        return self.project_root

    def analyze_structure(self, project_path: str) -> Dict[str, Any]:
        """Analyze project structure and return metadata"""
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
                doc_summary += f"\n... (truncated, total lines: {len(content.split('\n'))})"
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
            # Use the existing LLM client
            if hasattr(self, 'llm_client'):
                llm_client = self.llm_client
            else:
                llm_client = LayeredAIClient()
            
            response = llm_client.generate(analysis_prompt, doc_summary, max_tokens=3000)
            
            # Parse JSON response
            import json
            try:
                analysis = json.loads(response.strip())
                return analysis
            except json.JSONDecodeError:
                # Fallback if LLM doesn't return valid JSON
                return {
                    'document_analysis': response,
                    'analysis_method': 'llm_text_response'
                }
                
        except Exception as e:
            logger.warning(f"LLM document analysis failed: {e}")
            return {'document_analysis': 'LLM analysis unavailable'}

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
            try:
                config_path = os.path.join(project_path, config_file)
                with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    for framework, indicators in framework_indicators.items():
                        if any(indicator.lower() in content for indicator in indicators):
                            detected_frameworks.add(framework)
            except:
                continue

        # Check code files for import patterns
        for file_path, content in structure['code_files'].items():
            content_lower = content.lower()
            for framework, indicators in framework_indicators.items():
                if any(indicator.lower() in content_lower for indicator in indicators):
                    detected_frameworks.add(framework)

        structure['frameworks'] = detected_frameworks

    def get_code_sample(self, structure: Dict[str, Any], max_files: int = 5) -> str:
        """Get representative code sample for LLM analysis"""
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

        # Add sample code files
        code_sample += "=== CODE SAMPLES ===\n"

        # Prioritize important files
        important_patterns = ['main.py', 'app.py',
                              'index.js', 'server.js', '__init__.py', 'models.py']
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
            # Limit content to first 100 lines to stay within context
            lines = content.split('\n')[:100]
            code_sample += '\n'.join(lines)
            if len(content.split('\n')) > 100:
                tmp_len = len(content.split("\n"))
                code_sample += f"""\n... (truncated, total lines: {tmp_len})"""
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
                    tmp_len = len(content.split("\n"))
                    code_sample += f"""\n... (truncated, total lines: {tmp_len})"""
                code_sample += "\n"

        return code_sample

    def cleanup(self):
        """Clean up temporary directories"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class RubricManager:
    """Manages evaluation rubric and scoring"""

    def __init__(self, rubric_path: Optional[str] = None):
        self.rubric = self._load_default_rubric() if not rubric_path else self._load_rubric(rubric_path)

    def _load_default_rubric(self) -> Dict[str, Any]:
        """Load the default rubric configuration"""
        return {
            "repository_evaluation_rubric": {
                "metadata": {
                    "version": "1.0",
                    "total_points": 100,
                    "evaluation_type": "project_repository"
                },
                "categories": {
                    "architecture_design": {
                        "weight": 0.25,
                        "max_points": 25,
                        "subcategories": {
                            "modularity": {"points": 8},
                            "coupling_cohesion": {"points": 7},
                            "design_patterns": {"points": 5},
                            "scalability": {"points": 5}
                        }
                    },
                    "functionality_requirements": {
                        "weight": 0.20,
                        "max_points": 20,
                        "subcategories": {
                            "feature_completeness": {"points": 8},
                            "business_logic": {"points": 6},
                            "api_design": {"points": 6}
                        }
                    },
                    "code_quality": {
                        "weight": 0.20,
                        "max_points": 20,
                        "subcategories": {
                            "consistency": {"points": 6},
                            "readability": {"points": 5},
                            "maintainability": {"points": 5},
                            "documentation": {"points": 4}
                        }
                    },
                    "testing_quality": {
                        "weight": 0.15,
                        "max_points": 15,
                        "subcategories": {
                            "test_coverage": {"points": 6},
                            "test_quality": {"points": 5},
                            "test_strategy": {"points": 4}
                        }
                    },
                    "devops_deployment": {
                        "weight": 0.10,
                        "max_points": 10,
                        "subcategories": {
                            "containerization": {"points": 3},
                            "ci_cd": {"points": 3},
                            "configuration": {"points": 2},
                            "monitoring": {"points": 2}
                        }
                    },
                    "performance_security": {
                        "weight": 0.10,
                        "max_points": 10,
                        "subcategories": {
                            "performance": {"points": 5},
                            "security": {"points": 5}
                        }
                    }
                },
                "grading_scale": {
                    "A": {"min": 90, "max": 100},
                    "B": {"min": 80, "max": 89},
                    "C": {"min": 70, "max": 79},
                    "D": {"min": 60, "max": 69},
                    "F": {"min": 0, "max": 59}
                }
            }
        }

    def _load_rubric(self, rubric_path: str) -> Dict[str, Any]:
        """Load rubric from JSON file"""
        with open(rubric_path, 'r') as f:
            return json.load(f)

    def get_total_points(self) -> int:
        """Get total possible points"""
        return self.rubric["repository_evaluation_rubric"]["metadata"]["total_points"]

    def get_grade(self, score: int) -> str:
        """Convert numeric score to letter grade"""
        scale = self.rubric["repository_evaluation_rubric"]["grading_scale"]
        for grade, range_info in scale.items():
            if range_info["min"] <= score <= range_info["max"]:
                return grade
        return "F"


class LLMEvaluator(ABC):
    """Base class for LLM-powered evaluators"""

    def __init__(self, project_path: str, structure: Dict[str, Any], llm_client):
        self.project_path = project_path
        self.structure = structure
        self.llm_client = llm_client

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this evaluator"""
        pass

    @abstractmethod
    def create_evaluation_prompt(self, code_sample: str) -> str:
        """Create the evaluation prompt"""
        pass

    @abstractmethod
    def parse_llm_response(self, response: str, max_score: int) -> Tuple[int, List[str], List[str]]:
        """Parse LLM response into score, evidence, and recommendations"""
        pass

    def evaluate_with_llm(self, subcategory: str, max_score: int, code_sample: str) -> EvaluationResult:
        """Evaluate using LLM analysis"""
        system_prompt = self.get_system_prompt()
        evaluation_prompt = self.create_evaluation_prompt(code_sample)

        logger.info(f"Evaluating {subcategory} with LLM...")

        # Get LLM response
        llm_response = self.llm_client.generate(
            prompt=evaluation_prompt,
            system_prompt=system_prompt,
            max_tokens=1500
        )

        # Parse response
        score, evidence, recommendations = self.parse_llm_response(
            llm_response, max_score)

        return EvaluationResult(
            category=self.category_name,
            subcategory=subcategory,
            score=score,
            max_score=max_score,
            details=f"LLM-evaluated {subcategory}: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations,
            llm_analysis=llm_response
        )


class ArchitectureLLMEvaluator(LLMEvaluator):
    """LLM-powered architecture evaluator"""

    def __init__(self, project_path: str, structure: Dict[str, Any], llm_client):
        super().__init__(project_path, structure, llm_client)
        self.category_name = "architecture_design"

    def get_system_prompt(self) -> str:
        return """You are an expert software architect and code reviewer. Your task is to evaluate software architecture and design quality. 
        
        You must analyze code structure, design patterns, modularity, coupling, and scalability considerations.
        
        Provide specific, actionable feedback with concrete examples from the code. Always format your response as:
        
        SCORE: [0-X]
        EVIDENCE:
        - [Specific positive findings with examples]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed technical analysis]"""

    def create_evaluation_prompt(self, code_sample: str) -> str:
        return f"""Analyze this software project's architecture and design quality:
        
        {code_sample}
        
        Evaluate the following aspects:
        
        1. MODULARITY (0-8 points):
        - Separation of concerns
        - Single responsibility principle
        - Clear module boundaries
        - File organization and structure
        1. COUPLING & COHESION (0-7 points):
        - Dependencies between modules
        - Interface design
        - Code organization
        - Circular dependencies
        1. DESIGN PATTERNS (0-5 points):
        - Appropriate pattern usage
        - Implementation quality
        - Pattern consistency
        - Anti-pattern avoidance
        1. SCALABILITY (0-5 points):
        - Performance considerations
        - Resource management
        - Async operations
        - Database optimization
        
        Provide specific scores for each aspect and overall assessment. Focus on concrete examples from the code."""

    def parse_llm_response(self, response: str, max_score: int) -> Tuple[int, List[str], List[str]]:
        """Parse LLM response for architecture evaluation"""
        try:
            # Extract score
            score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else max_score // 2
            score = min(score, max_score)  # Cap at max score

            # Extract evidence
            evidence_section = re.search(r'EVIDENCE:(.*?)(?:RECOMMENDATIONS:|ANALYSIS:|$)', response,
                                         re.DOTALL | re.IGNORECASE)
            evidence = []
            if evidence_section:
                evidence_text = evidence_section.group(1).strip()
                evidence = [line.strip('- ').strip() for line in evidence_text.split('\n')
                            if line.strip() and line.strip().startswith('-')]

            # Extract recommendations
            rec_section = re.search(
                r'RECOMMENDATIONS:(.*?)(?:ANALYSIS:|$)', response, re.DOTALL | re.IGNORECASE)
            recommendations = []
            if rec_section:
                rec_text = rec_section.group(1).strip()
                recommendations = [line.strip('- ').strip() for line in rec_text.split('\n')
                                   if line.strip() and line.strip().startswith('-')]

            # Limit to 5 items each
            return score, evidence[:5], recommendations[:5]

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return max_score // 2, ["LLM analysis completed"], ["Review architecture design"]

    def evaluate(self) -> List[EvaluationResult]:
        """Evaluate architecture using LLM"""
        repo_processor = RepositoryProcessor()
        code_sample = repo_processor.get_code_sample(self.structure)

        # For architecture, we'll do a comprehensive evaluation
        results = []

        # Combined architecture evaluation
        total_max_score = 25  # Sum of all architecture subcategory points
        result = self.evaluate_with_llm(
            "architecture_comprehensive", total_max_score, code_sample)

        # Break down the result into subcategories
        modularity_score = min(8, result.score * 8 // total_max_score)
        coupling_score = min(7, result.score * 7 // total_max_score)
        patterns_score = min(5, result.score * 5 // total_max_score)
        scalability_score = min(5, result.score * 5 // total_max_score)

        results.append(EvaluationResult(
            category="architecture_design",
            subcategory="modularity",
            score=modularity_score,
            max_score=8,
            details=f"Modularity assessment: {modularity_score}/8",
            evidence=result.evidence,
            recommendations=result.recommendations,
            llm_analysis=result.llm_analysis
        ))

        results.append(EvaluationResult(
            category="architecture_design",
            subcategory="coupling_cohesion",
            score=coupling_score,
            max_score=7,
            details=f"Coupling & cohesion assessment: {coupling_score}/7",
            evidence=result.evidence,
            recommendations=result.recommendations,
            llm_analysis=result.llm_analysis
        ))

        results.append(EvaluationResult(
            category="architecture_design",
            subcategory="design_patterns",
            score=patterns_score,
            max_score=5,
            details=f"Design patterns assessment: {patterns_score}/5",
            evidence=result.evidence,
            recommendations=result.recommendations,
            llm_analysis=result.llm_analysis
        ))

        results.append(EvaluationResult(
            category="architecture_design",
            subcategory="scalability",
            score=scalability_score,
            max_score=5,
            details=f"Scalability assessment: {scalability_score}/5",
            evidence=result.evidence,
            recommendations=result.recommendations,
            llm_analysis=result.llm_analysis
        ))

        return results


class CodeQualityLLMEvaluator(LLMEvaluator):

    def __init__(self, project_path: str, structure: Dict[str, Any], llm_client):
        super().__init__(project_path, structure, llm_client)
        self.category_name = "code_quality"

    def get_system_prompt(self) -> str:
        return """You are an expert code reviewer focused on code quality, maintainability, and best practices.
        
        Analyze code for consistency, readability, maintainability, and documentation quality.
        
        Look for:
        - Naming conventions and consistency
        - Code organization and structure
        - Comment quality and documentation
        - DRY principle adherence
        - Function/method size and complexity
        - Readability and clarity
        
        Always format your response as:
        SCORE: [0-X]
        EVIDENCE:
        - [Specific positive findings]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed assessment]"""

    def create_evaluation_prompt(self, code_sample: str) -> str:
        return f"""Analyze this code for quality, maintainability, and best practices:
        
        {code_sample}
        
        Evaluate these aspects:
        
        1. CONSISTENCY (0-6 points):
        - Naming conventions across files
        - Code style uniformity
        - Error handling patterns
        - Import/export consistency
        1. READABILITY (0-5 points):
        - Clear and meaningful names
        - Appropriate code comments
        - Logical code organization
        - Self-documenting code
        1. MAINTAINABILITY (0-5 points):
        - DRY principle adherence
        - Function/method size
        - Code complexity
        - Refactoring readiness
        1. DOCUMENTATION (0-4 points):
        - README quality
        - Code comments
        - API documentation
        - Setup instructions
        
        Provide specific examples from the code and actionable recommendations."""

    def parse_llm_response(self, response: str, max_score: int) -> Tuple[int, List[str], List[str]]:
        """Parse LLM response for code quality evaluation"""
        try:
            # Extract score
            score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else max_score // 2
            score = min(score, max_score)

            # Extract evidence
            evidence_section = re.search(r'EVIDENCE:(.*?)(?:RECOMMENDATIONS:|ANALYSIS:|$)', response,
                                         re.DOTALL | re.IGNORECASE)
            evidence = []
            if evidence_section:
                evidence_text = evidence_section.group(1).strip()
                evidence = [line.strip('- ').strip() for line in evidence_text.split('\n')
                            if line.strip() and line.strip().startswith('-')]

            # Extract recommendations
            rec_section = re.search(r'RECOMMENDATIONS:(.*?)(?:ANALYSIS:|$)', response,
                                    re.DOTALL | re.IGNORECASE)
            recommendations = []
            if rec_section:
                rec_text = rec_section.group(1).strip()
                recommendations = [line.strip('- ').strip() for line in rec_text.split('\n')
                                   if line.strip() and line.strip().startswith('-')]

            return score, evidence[:5], recommendations[:5]

        except Exception as e:
            logger.error(f"Error parsing code quality LLM response: {e}")
            return max_score // 2, ["Code quality analysis completed"], ["Improve code quality"]

    def evaluate(self) -> List[EvaluationResult]:
        """Evaluate code quality using LLM"""
        repo_processor = RepositoryProcessor()
        code_sample = repo_processor.get_code_sample(self.structure)

        results = []
        total_max_score = 20  # Sum of code quality subcategory points

        result = self.evaluate_with_llm(
            "code_quality_comprehensive", total_max_score, code_sample)

        # Break down into subcategories
        consistency_score = min(6, result.score * 6 // total_max_score)
        readability_score = min(5, result.score * 5 // total_max_score)
        maintainability_score = min(5, result.score * 5 // total_max_score)
        documentation_score = min(4, result.score * 4 // total_max_score)

        results.extend([
            EvaluationResult(
                category="code_quality",
                subcategory="consistency",
                score=consistency_score,
                max_score=6,
                details=f"Consistency assessment: {consistency_score}/6",
                evidence=result.evidence,
                recommendations=result.recommendations,
                llm_analysis=result.llm_analysis
            ),
            EvaluationResult(
                category="code_quality",
                subcategory="readability",
                score=readability_score,
                max_score=5,
                details=f"Readability assessment: {readability_score}/5",
                evidence=result.evidence,
                recommendations=result.recommendations,
                llm_analysis=result.llm_analysis
            ),
            EvaluationResult(
                category="code_quality",
                subcategory="maintainability",
                score=maintainability_score,
                max_score=5,
                details=f"Maintainability assessment: {maintainability_score}/5",
                evidence=result.evidence,
                recommendations=result.recommendations,
                llm_analysis=result.llm_analysis
            ),
            EvaluationResult(
                category="code_quality",
                subcategory="documentation",
                score=documentation_score,
                max_score=4,
                details=f"Documentation assessment: {documentation_score}/4",
                evidence=result.evidence,
                recommendations=result.recommendations,
                llm_analysis=result.llm_analysis
            )
        ])

        return results


class FunctionalityLLMEvaluator(LLMEvaluator):
    """LLM-powered functionality evaluator"""

    def __init__(self, project_path: str, structure: Dict[str, Any], llm_client):
        super().__init__(project_path, structure, llm_client)
        self.category_name = "functionality_requirements"

    def get_system_prompt(self) -> str:
        return """You are an expert software analyst evaluating feature completeness and implementation quality.
        
        Analyze the codebase to assess:
        - Feature completeness and implementation
        - Business logic correctness
        - API design and consistency
        - Error handling and edge cases
        - User experience considerations
        
        Format your response as:
        SCORE: [0-X]
        EVIDENCE:
        - [Specific implementation strengths]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed functionality assessment]"""

    def create_evaluation_prompt(self, code_sample: str) -> str:
        return f"""Analyze this project's functionality and feature implementation:
        
        {code_sample}
        
        Evaluate these aspects:
        
        1. FEATURE COMPLETENESS (0-8 points):
        - Implemented vs expected features
        - Core functionality working
        - Feature integration quality
        - User workflow completeness
        1. BUSINESS LOGIC (0-6 points):
        - Domain logic implementation
        - Business rules enforcement
        - Data validation
        - Edge case handling
        1. API DESIGN (0-6 points):
        - RESTful principles (if applicable)
        - Consistent structure
        - Error responses
        - Input/output formats
        
        Look for evidence of working features, proper validation, and complete implementations."""

    def parse_llm_response(self, response: str, max_score: int) -> Tuple[int, List[str], List[str]]:
        """Parse LLM response for functionality evaluation"""
        try:
            score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else max_score // 2
            score = min(score, max_score)

            evidence_section = re.search(r'EVIDENCE:(.*?)(?:RECOMMENDATIONS:|ANALYSIS:|$)', response,
                                         re.DOTALL | re.IGNORECASE)
            evidence = []
            if evidence_section:
                evidence_text = evidence_section.group(1).strip()
                evidence = [line.strip('- ').strip() for line in evidence_text.split('\n')
                            if line.strip() and line.strip().startswith('-')]

            rec_section = re.search(
                r'RECOMMENDATIONS:(.*?)(?:ANALYSIS:|$)', response, re.DOTALL | re.IGNORECASE)
            recommendations = []
            if rec_section:
                rec_text = rec_section.group(1).strip()
                recommendations = [line.strip('- ').strip() for line in rec_text.split('\n')
                                   if line.strip() and line.strip().startswith('-')]

            return score, evidence[:5], recommendations[:5]

        except Exception as e:
            logger.error(f"Error parsing functionality LLM response: {e}")
            return max_score // 2, ["Functionality analysis completed"], ["Improve feature implementation"]

    def evaluate(self) -> List[EvaluationResult]:
        """Evaluate functionality using LLM"""
        repo_processor = RepositoryProcessor()
        code_sample = repo_processor.get_code_sample(self.structure)

        results = []
        total_max_score = 20  # Sum of functionality subcategory points

        result = self.evaluate_with_llm(
            "functionality_comprehensive", total_max_score, code_sample)

        # Break down into subcategories
        completeness_score = min(8, result.score * 8 // total_max_score)
        business_logic_score = min(6, result.score * 6 // total_max_score)
        api_design_score = min(6, result.score * 6 // total_max_score)

        results.extend([
            EvaluationResult(
                category="functionality_requirements",
                subcategory="feature_completeness",
                score=completeness_score,
                max_score=8,
                details=f"Feature completeness: {completeness_score}/8",
                evidence=result.evidence,
                recommendations=result.recommendations,
                llm_analysis=result.llm_analysis
            ),
            EvaluationResult(
                category="functionality_requirements",
                subcategory="business_logic",
                score=business_logic_score,
                max_score=6,
                details=f"Business logic: {business_logic_score}/6",
                evidence=result.evidence,
                recommendations=result.recommendations,
                llm_analysis=result.llm_analysis
            ),
            EvaluationResult(
                category="functionality_requirements",
                subcategory="api_design",
                score=api_design_score,
                max_score=6,
                details=f"API design: {api_design_score}/6",
                evidence=result.evidence,
                recommendations=result.recommendations,
                llm_analysis=result.llm_analysis
            )
        ])

        return results


class TestingQualityEvaluator:
    """Traditional evaluator for testing (less dependent on LLM)"""

    def __init__(self, project_path: str, structure: Dict[str, Any]):
        self.project_path = project_path
        self.structure = structure

    def evaluate(self) -> List[EvaluationResult]:
        results = []

        results.append(self._evaluate_test_coverage())
        results.append(self._evaluate_test_quality())
        results.append(self._evaluate_test_strategy())

        return results

    def _evaluate_test_coverage(self) -> EvaluationResult:
        """Evaluate test coverage"""
        score = 0
        max_score = 6
        evidence = []
        recommendations = []

        test_files = self.structure['test_files']
        code_files = [f for f in self.structure['files']
                      if f.endswith(('.py', '.js', '.java', '.ts')) and
                      not any(pattern in f.lower() for pattern in ['test_', '_test', 'spec_'])]

        if not test_files:
            recommendations.append("Add comprehensive test suite")
            return EvaluationResult(
                category="testing_quality",
                subcategory="test_coverage",
                score=0,
                max_score=max_score,
                details="No tests found",
                evidence=evidence,
                recommendations=recommendations
            )

        # Calculate test ratio
        test_ratio = len(test_files) / max(len(code_files), 1)

        if test_ratio >= 0.8:
            score += 4
            evidence.append(
                f"Excellent test coverage ratio: {len(test_files)} tests for {len(code_files)} source files")
        elif test_ratio >= 0.5:
            score += 3
            evidence.append(
                f"Good test coverage ratio: {len(test_files)} tests for {len(code_files)} source files")
        elif test_ratio >= 0.3:
            score += 2
            evidence.append("Reasonable test coverage")
        else:
            score += 1
            recommendations.append("Increase test coverage")

        # Check for different test types
        has_unit_tests = any('unit' in f.lower() for f in test_files)
        has_integration_tests = any('integration' in f.lower()
                                    for f in test_files)
        has_e2e_tests = any('e2e' in f.lower()
                            or 'end-to-end' in f.lower() for f in test_files)

        test_types_count = sum(
            [has_unit_tests, has_integration_tests, has_e2e_tests])
        score += min(test_types_count, 2)

        if test_types_count >= 2:
            evidence.append(
                "Multiple test types present (unit, integration, e2e)")
        elif test_types_count == 1:
            evidence.append("Basic test types present")
            recommendations.append(
                "Add more test types (unit, integration, e2e)")

        return EvaluationResult(
            category="testing_quality",
            subcategory="test_coverage",
            score=score,
            max_score=max_score,
            details=f"Test coverage score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )

    def _evaluate_test_quality(self) -> EvaluationResult:
        """Evaluate test quality"""
        score = 0
        max_score = 5
        evidence = []
        recommendations = []

        if not self.structure['test_files']:
            return EvaluationResult(
                category="testing_quality",
                subcategory="test_quality",
                score=0,
                max_score=max_score,
                details="No tests to evaluate",
                evidence=[],
                recommendations=["Add test suite"]
            )

        # Check test organization
        test_dirs = set(os.path.dirname(f)
                        for f in self.structure['test_files'] if '/' in f)
        if test_dirs:
            score += 2
            evidence.append("Tests are well organized in directories")

        # Check for test configuration
        test_configs = [f for f in self.structure['config_files']
                        if any(test_indicator in f.lower()
                               for test_indicator in ['test', 'jest', 'pytest', 'mocha', 'karma'])]
        if test_configs:
            score += 2
            evidence.append(
                f"Test configuration present: {', '.join(test_configs)}")

        # Check for test utilities/helpers
        has_test_utils = any('util' in f.lower() or 'helper' in f.lower()
                             for f in self.structure['test_files'])
        if has_test_utils:
            score += 1
            evidence.append("Test utilities/helpers present")

        return EvaluationResult(
            category="testing_quality",
            subcategory="test_quality",
            score=score,
            max_score=max_score,
            details=f"Test quality score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )

    def _evaluate_test_strategy(self) -> EvaluationResult:
        """Evaluate testing strategy"""
        score = 0
        max_score = 4
        evidence = []
        recommendations = []

        if not self.structure['test_files']:
            return EvaluationResult(
                category="testing_quality",
                subcategory="test_strategy",
                score=0,
                max_score=max_score,
                details="No testing strategy evident",
                evidence=[],
                recommendations=["Develop comprehensive testing strategy"]
            )

        # Check for test types
        test_types = []
        if any('unit' in f.lower() for f in self.structure['test_files']):
            test_types.append('unit')
        if any('integration' in f.lower() for f in self.structure['test_files']):
            test_types.append('integration')
        if any('e2e' in f.lower() or 'end-to-end' in f.lower() for f in self.structure['test_files']):
            test_types.append('e2e')

        score += min(len(test_types), 3)
        if test_types:
            evidence.append(f"Test types present: {', '.join(test_types)}")

        # Check for test data management
        if any('fixture' in f.lower() or 'mock' in f.lower() or 'stub' in f.lower() for f in
               self.structure['test_files']):
            score += 1
            evidence.append("Test data management present")

        return EvaluationResult(
            category="testing_quality",
            subcategory="test_strategy",
            score=score,
            max_score=max_score,
            details=f"Test strategy score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )


class DevOpsEvaluator:
    """Traditional evaluator for DevOps aspects"""

    def __init__(self, project_path: str, structure: Dict[str, Any]):
        self.project_path = project_path
        self.structure = structure

    def evaluate(self) -> List[EvaluationResult]:
        results = []

        results.append(self._evaluate_containerization())
        results.append(self._evaluate_ci_cd())
        results.append(self._evaluate_configuration())
        results.append(self._evaluate_monitoring())

        return results

    def _evaluate_containerization(self) -> EvaluationResult:
        """Evaluate containerization"""
        score = 0
        max_score = 3
        evidence = []
        recommendations = []

        # Check for Docker files
        docker_files = [f for f in self.structure['files']
                        if 'dockerfile' in f.lower()]
        compose_files = [f for f in self.structure['files']
                         if 'docker-compose' in f.lower()]

        if docker_files:
            score += 2
            evidence.append(f"Dockerfile present: {', '.join(docker_files)}")

            # Check if it's optimized (multi-stage, etc.) - simplified check
            dockerfile_path = os.path.join(self.project_path, docker_files[0])
            try:
                with open(dockerfile_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    if 'as builder' in content or 'from' in content.count('from') > 1:
                        score += 1
                        evidence.append("Multi-stage Docker build detected")
            except:
                pass
        else:
            recommendations.append("Add Dockerfile for containerization")

        if compose_files:
            evidence.append(
                f"Docker Compose present: {', '.join(compose_files)}")

        return EvaluationResult(
            category="devops_deployment",
            subcategory="containerization",
            score=score,
            max_score=max_score,
            details=f"Containerization score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )

    def _evaluate_ci_cd(self) -> EvaluationResult:
        """Evaluate CI/CD setup"""
        score = 0
        max_score = 3
        evidence = []
        recommendations = []

        # Check for CI/CD files
        ci_patterns = ['.github/workflows', '.gitlab-ci',
                       'jenkinsfile', '.travis', 'azure-pipelines']
        ci_files = []

        for file_path in self.structure['files']:
            if any(pattern in file_path.lower() for pattern in ci_patterns):
                ci_files.append(file_path)

        if ci_files:
            score += 3
            evidence.append(
                f"CI/CD configuration present: {', '.join(ci_files[:3])}")
        else:
            recommendations.append("Add CI/CD pipeline configuration")

        return EvaluationResult(
            category="devops_deployment",
            subcategory="ci_cd",
            score=score,
            max_score=max_score,
            details=f"CI/CD score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )

    def _evaluate_configuration(self) -> EvaluationResult:
        """Evaluate configuration management"""
        score = 0
        max_score = 2
        evidence = []
        recommendations = []

        # Check for environment files
        env_files = [f for f in self.structure['files'] if '.env' in f.lower()]
        config_files = [
            f for f in self.structure['config_files'] if 'config' in f.lower()]

        if env_files or config_files:
            score += 2
            evidence.append("Configuration externalization present")
            if env_files:
                evidence.append(f"Environment files: {', '.join(env_files)}")
        else:
            recommendations.append(
                "Externalize configuration using environment variables")

        return EvaluationResult(
            category="devops_deployment",
            subcategory="configuration",
            score=score,
            max_score=max_score,
            details=f"Configuration score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )

    def _evaluate_monitoring(self) -> EvaluationResult:
        """Evaluate monitoring and logging"""
        score = 0
        max_score = 2
        evidence = []
        recommendations = []

        # Check for logging implementation (simplified)
        has_logging = False
        for file_path, content in self.structure['code_files'].items():
            if any(log_term in content.lower() for log_term in ['logging', 'logger', 'log.', 'console.log']):
                has_logging = True
                break

        if has_logging:
            score += 1
            evidence.append("Logging implementation detected")
        else:
            recommendations.append("Implement proper logging strategy")

        # Check for health endpoints or monitoring
        has_health = any('health' in content.lower() or '/status' in content.lower()
                         for content in self.structure['code_files'].values())

        if has_health:
            score += 1
            evidence.append("Health check endpoints detected")
        else:
            recommendations.append("Add health check endpoints")

        return EvaluationResult(
            category="devops_deployment",
            subcategory="monitoring",
            score=score,
            max_score=max_score,
            details=f"Monitoring score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )


class PerformanceSecurityEvaluator:
    """Traditional evaluator for performance and security"""

    def __init__(self, project_path: str, structure: Dict[str, Any]):
        self.project_path = project_path
        self.structure = structure

    def evaluate(self) -> List[EvaluationResult]:
        results = []

        results.append(self._evaluate_performance())
        results.append(self._evaluate_security())

        return results

    def _evaluate_performance(self) -> EvaluationResult:
        """Evaluate performance considerations"""
        score = 0
        max_score = 5
        evidence = []
        recommendations = []

        # Check for async/await patterns
        has_async = False
        for content in self.structure['code_files'].values():
            if any(async_term in content.lower() for async_term in ['async', 'await', 'asyncio', 'promise']):
                has_async = True
                break

        if has_async:
            score += 2
            evidence.append("Async/concurrent patterns detected")
        else:
            recommendations.append("Consider implementing async operations")

        # Check for caching
        has_caching = False
        for content in self.structure['code_files'].values():
            if any(cache_term in content.lower() for cache_term in ['cache', 'redis', 'memcached', '@cache']):
                has_caching = True
                break

        if has_caching:
            score += 2
            evidence.append("Caching mechanisms detected")
        else:
            recommendations.append("Implement caching for better performance")

        # Check for database optimization indicators
        has_db_optimization = False
        for content in self.structure['code_files'].values():
            if any(db_term in content.lower() for db_term in ['index', 'optimize', 'query', 'select_related', 'prefetch']):
                has_db_optimization = True
                break

        if has_db_optimization:
            score += 1
            evidence.append("Database optimization considerations present")
        else:
            recommendations.append("Consider database optimization strategies")

        return EvaluationResult(
            category="performance_security",
            subcategory="performance",
            score=score,
            max_score=max_score,
            details=f"Performance score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )

    def _evaluate_security(self) -> EvaluationResult:
        """Evaluate security considerations"""
        score = 0
        max_score = 5
        evidence = []
        recommendations = []

        # Check for input validation
        has_validation = False
        for content in self.structure['code_files'].values():
            if any(val_term in content.lower() for val_term in ['validate', 'sanitize', 'escape', 'validator']):
                has_validation = True
                break

        if has_validation:
            score += 2
            evidence.append("Input validation patterns detected")
        else:
            recommendations.append("Implement comprehensive input validation")

        # Check for authentication/authorization
        has_auth = False
        for content in self.structure['code_files'].values():
            if any(auth_term in content.lower() for auth_term in ['auth', 'login', 'jwt', 'token', 'session']):
                has_auth = True
                break

        if has_auth:
            score += 2
            evidence.append("Authentication/authorization implementation detected")
        else:
            recommendations.append("Implement authentication and authorization")

        # Check for security headers/HTTPS
        has_security_config = False
        for content in self.structure['code_files'].values():
            if any(sec_term in content.lower() for sec_term in ['https', 'ssl', 'csrf', 'cors', 'security']):
                has_security_config = True
                break

        if has_security_config:
            score += 1
            evidence.append("Security configuration present")
        else:
            recommendations.append("Configure security headers and HTTPS")

        return EvaluationResult(
            category="performance_security",
            subcategory="security",
            score=score,
            max_score=max_score,
            details=f"Security score: {score}/{max_score}",
            evidence=evidence,
            recommendations=recommendations
        )


class DocumentationLLMEvaluator(LLMEvaluator):
    """Enhanced documentation quality evaluation using LLM"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating DOCUMENTATION QUALITY for a project submission.

        Analyze the documentation files (.md, .txt, .pdf, .docx, README files, etc.) and code comments.
        
        Focus on documentation_quality aspects:
        - README quality and completeness
        - Code comments and inline documentation  
        - API documentation clarity
        - Setup and installation instructions
        - Architecture documentation
        - Document structure and organization
        
        You must analyze documentation structure, completeness, clarity, and technical accuracy.
        
        Provide specific, actionable feedback with concrete examples from the documentation.
        
        SCORE: [0-25]
        EVIDENCE:
        - [Specific positive findings with examples]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed documentation analysis]"""


class ContentQualityLLMEvaluator(LLMEvaluator):
    """Content quality evaluation for documented submissions"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating CONTENT QUALITY for a documented submission.

        Analyze the written content quality across all documentation files.
        
        Focus on content_quality aspects:
        - Clarity of writing and communication
        - Completeness of topic coverage
        - Technical accuracy of information
        - Appropriate depth and detail level
        - Supporting examples and evidence
        
        You must analyze writing quality, technical correctness, and information completeness.
        
        Provide specific feedback on content strengths and areas for improvement.
        
        SCORE: [0-30]
        EVIDENCE:
        - [Specific positive findings with examples]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed content analysis]"""


class PresentationLLMEvaluator(LLMEvaluator):
    """Presentation and formatting evaluation"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating PRESENTATION AND FORMAT quality for a submission.

        Analyze the visual presentation, formatting, and overall appearance.
        
        Focus on presentation_format aspects:
        - Consistent formatting and styling
        - Visual aids (diagrams, charts, images)
        - Readability (font, spacing, layout)
        - Professional appearance and polish
        
        You must analyze visual presentation, formatting consistency, and professional appearance.
        
        Provide specific feedback on presentation strengths and formatting issues.
        
        SCORE: [0-18]
        EVIDENCE:
        - [Specific positive findings with examples]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed presentation analysis]"""


class RequirementsLLMEvaluator(LLMEvaluator):
    """Requirements compliance evaluation"""
    
    def get_llm_prompt(self) -> str:
        return """You are evaluating REQUIREMENTS COMPLIANCE for a submission.

        Analyze how well the submission meets specified requirements and guidelines.
        
        Focus on requirements_compliance aspects:
        - All requirements addressed and covered
        - Adherence to given specifications
        - Completeness of requested deliverables
        - Following submission format and guidelines
        
        You must analyze requirement coverage, specification adherence, and submission compliance.
        
        Provide specific feedback on requirement fulfillment and compliance gaps.
        
        SCORE: [0-22]
        EVIDENCE:
        - [Specific positive findings with examples]
        RECOMMENDATIONS:
        - [Specific improvement suggestions]
        ANALYSIS: [Detailed requirements analysis]"""


class AIEvalEngine:
    """Main evaluation engine with layered AI integration"""

    def __init__(self, rubric_path: Optional[str] = "AIEVAL-Rubric.json"):
        self.rubric_manager = RubricManager(rubric_path)
        self.repo_processor = RepositoryProcessor()
        self.llm_client = LayeredAIClient()
        self.database = EvaluationDatabase()

        # Initialize evaluators with LLM integration
        self.llm_evaluators = {
            'architecture_design': ArchitectureLLMEvaluator,
            'code_quality': CodeQualityLLMEvaluator,
            'functionality_requirements': FunctionalityLLMEvaluator,
            'documentation_quality': DocumentationLLMEvaluator,
            'content_quality': ContentQualityLLMEvaluator,
            'presentation_format': PresentationLLMEvaluator,
            'requirements_compliance': RequirementsLLMEvaluator,
        }

        # Traditional evaluators (less dependent on LLM)
        self.traditional_evaluators = {
            'testing_quality': TestingQualityEvaluator,
            'devops_deployment': DevOpsEvaluator,
            'performance_security': PerformanceSecurityEvaluator,
        }

    def evaluate_repository(self, source: str, source_type: str = 'auto') -> Dict[str, Any]:
        """
        Evaluate a repository using layered AI services
        
        Args:
            source: Path to zip file, git repository URL, or local directory
            source_type: 'zip', 'git', 'directory', or 'auto' for auto-detection
            
        Returns:
            Comprehensive evaluation results
        """
        try:
            # Process repository
            if source_type == 'auto':
                if source.startswith(('http', 'git@')):
                    source_type = 'git'
                elif source.endswith('.zip'):
                    source_type = 'zip'
                elif os.path.isdir(source):
                    source_type = 'directory'
                else:
                    source_type = 'zip'  # Default assumption

            if source_type == 'zip':
                project_path = self.repo_processor.process_zip(source)
            elif source_type == 'git':
                project_path = self.repo_processor.process_git_repo(source)
            elif source_type == 'directory':
                project_path = self.repo_processor.process_directory(source)
            else:
                raise ValueError(
                    "Invalid source_type. Use 'zip', 'git', 'directory', or 'auto'")

            logger.info(f"Processing repository at: {project_path}")

            # Analyze structure
            structure = self.repo_processor.analyze_structure(project_path)

            logger.info(
                f"Found {len(structure['files'])} files, {len(structure['languages'])} languages: {', '.join(structure['languages'])}")

            # Create project metadata
            metadata = ProjectMetadata(
                name=os.path.basename(project_path),
                type=self._detect_project_type(structure),
                languages=list(structure['languages']),
                frameworks=list(structure['frameworks']),
                size_loc=len(structure['files']),
                file_count=len(structure['files']),
                has_tests=len(structure['test_files']) > 0,
                has_docs=len(structure['doc_files']) > 0,
                has_ci=any('ci' in f.lower() or 'github' in f.lower() or 'gitlab' in f.lower()
                           for f in structure['files'])
            )

            # Run evaluations
            all_results = []
            total_score = 0
            max_total_score = 0

            # LLM-powered evaluations
            for category, evaluator_class in self.llm_evaluators.items():
                logger.info(f"Running LLM evaluation for {category}...")
                try:
                    evaluator = evaluator_class(
                        project_path, structure, self.llm_client)
                    results = evaluator.evaluate()
                    all_results.extend(results)

                    category_score = sum(r.score for r in results)
                    category_max = sum(r.max_score for r in results)
                    total_score += category_score
                    max_total_score += category_max

                    logger.info(f"{category}: {category_score}/{category_max}")

                    # Add delay to avoid overwhelming services
                    time.sleep(1)

                except Exception as e:
                    logger.error(
                        f"Error in LLM evaluation for {category}: {e}")
                    # Continue with other evaluations

            # Traditional evaluations
            for category, evaluator_class in self.traditional_evaluators.items():
                logger.info(
                    f"Running traditional evaluation for {category}...")
                try:
                    evaluator = evaluator_class(project_path, structure)
                    results = evaluator.evaluate()
                    all_results.extend(results)

                    category_score = sum(r.score for r in results)
                    category_max = sum(r.max_score for r in results)
                    total_score += category_score
                    max_total_score += category_max

                    logger.info(f"{category}: {category_score}/{category_max}")

                except Exception as e:
                    logger.error(f"Error in evaluation for {category}: {e}")
                    # Continue with other evaluations

            # Calculate final grade
            final_percentage = (total_score / max_total_score *
                                100) if max_total_score > 0 else 0
            grade = self.rubric_manager.get_grade(int(final_percentage))

            logger.info(
                f"Final evaluation: {total_score}/{max_total_score} ({final_percentage:.1f}%) - Grade: {grade}")

            # Generate report
            report = self._generate_report(
                metadata, all_results, total_score, max_total_score, grade)
            
            # Save to database with complete rubric scores
            evaluation_id = self.database.save_evaluation(source, source_type, report, self.rubric_manager.rubric)
            report['evaluation_id'] = evaluation_id
            logger.info(f"Evaluation saved to database with ID: {evaluation_id}")

            return report

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise
        finally:
            # Cleanup
            self.repo_processor.cleanup()

    def evaluate_multiround(self, source: str, source_type: str = 'auto', 
                          rounds: int = 3, providers: List[str] = None) -> Dict[str, Any]:
        """
        Perform multi-round evaluation with multiple AI providers and statistical analysis
        
        Args:
            source: Path to repository/documentation
            source_type: Type of source ('auto', 'zip', 'git', 'directory')
            rounds: Number of evaluation rounds per provider
            providers: List of providers to use ['claude', 'openai'] (default: both)
        """
        import statistics
        import time
        
        if providers is None:
            providers = ['claude', 'openai']
        
        print(f"🎯 Starting {rounds}-round evaluation with providers: {', '.join(providers)}")
        
        # Process repository once
        try:
            metadata, structure = self.repo_processor.process_repository(source, source_type)
            project_name = metadata.name
            
            # Create multi-round evaluation record
            multiround_id = self.database.save_multiround_evaluation(
                source, source_type, project_name, rounds, providers)
            
            provider_results = {}
            all_round_data = []
            
            # Run evaluation rounds for each provider
            for provider in providers:
                print(f"\n🤖 Running {rounds} rounds with {provider.upper()}...")
                provider_scores = []
                provider_rounds = []
                
                for round_num in range(1, rounds + 1):
                    print(f"   Round {round_num}/{rounds}...", end=" ")
                    start_time = time.time()
                    
                    # Set specific model for this provider
                    if provider == 'claude':
                        self.llm_client.force_provider = 'claude'
                    elif provider == 'openai':
                        self.llm_client.force_provider = 'openai'
                    
                    # Run single evaluation
                    round_result = self._evaluate_single_round(metadata, structure)
                    eval_time = time.time() - start_time
                    
                    # Save round to database
                    round_id = self.database.save_evaluation_round(
                        multiround_id, provider, round_num, 
                        self.llm_client.last_successful_model or provider,
                        round_result, eval_time)
                    
                    provider_scores.append(round_result['total_score'])
                    provider_rounds.append(round_result)
                    all_round_data.append({
                        'provider': provider,
                        'round': round_num,
                        'score': round_result['total_score'],
                        'result': round_result
                    })
                    
                    print(f"Score: {round_result['total_score']:.1f}")
                
                # Calculate provider statistics
                if len(provider_scores) > 1:
                    stats = {
                        'avg_score': statistics.mean(provider_scores),
                        'min_score': min(provider_scores),
                        'max_score': max(provider_scores),
                        'std_deviation': statistics.stdev(provider_scores),
                        'variance': statistics.variance(provider_scores),
                        'confidence_interval': self._calculate_confidence_interval(provider_scores),
                        'num_rounds': len(provider_scores)
                    }
                else:
                    stats = {
                        'avg_score': provider_scores[0],
                        'min_score': provider_scores[0],
                        'max_score': provider_scores[0],
                        'std_deviation': 0.0,
                        'variance': 0.0,
                        'confidence_interval': (provider_scores[0], provider_scores[0]),
                        'num_rounds': 1
                    }
                
                provider_results[provider] = stats
                self.database.save_provider_statistics(multiround_id, provider, stats)
                
                print(f"   {provider.upper()} Average: {stats['avg_score']:.1f} ± {stats['std_deviation']:.1f}")
            
            # Calculate final overall score
            overall_avg = statistics.mean([stats['avg_score'] for stats in provider_results.values()])
            final_grade = self.rubric_manager.get_grade(int(overall_avg))
            
            # Finalize multiround evaluation
            self.database.finalize_multiround_evaluation(multiround_id, overall_avg, final_grade)
            
            # Reset provider forcing
            self.llm_client.force_provider = None
            
            return {
                'multiround_id': multiround_id,
                'source': source,
                'project_name': project_name,
                'rounds': rounds,
                'providers': providers,
                'provider_results': provider_results,
                'final_score': overall_avg,
                'final_grade': final_grade,
                'all_rounds': all_round_data,
                'metadata': metadata._asdict()
            }
            
        except Exception as e:
            logger.error(f"Multi-round evaluation failed: {e}")
            raise
        finally:
            self.repo_processor.cleanup()
            self.llm_client.force_provider = None

    def evaluate_multiround_with_models(self, source: str, source_type: str = 'auto', 
                                       rounds: int = 3, provider_models: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """
        Perform multi-round evaluation with specific models per provider
        
        Args:
            source: Path to repository/documentation
            source_type: Type of source ('auto', 'zip', 'git', 'directory')
            rounds: Number of evaluation rounds per model
            provider_models: Dict with provider names as keys and model lists as values
                           e.g., {'claude': ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'],
                                  'openai': ['gpt-4', 'gpt-4o'],
                                  'ollama': ['llama3.1', 'gemma2']}
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
        
        # Process repository once
        try:
            metadata, structure = self.repo_processor.process_repository(source, source_type)
            project_name = metadata.name
            
            # Create multi-round evaluation record
            providers_list = list(provider_models.keys())
            multiround_id = self.database.save_multiround_evaluation(
                source, source_type, project_name, rounds, providers_list)
            
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
                    
                    # Run single evaluation
                    round_result = self._evaluate_single_round(metadata, structure)
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
            
            # Reset provider forcing
            self.llm_client.force_provider = None
            self.llm_client.force_model = None
            
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
                'metadata': metadata._asdict()
            }
            
        except Exception as e:
            logger.error(f"Multi-round evaluation failed: {e}")
            raise
        finally:
            self.repo_processor.cleanup()
            self.llm_client.force_provider = None
            self.llm_client.force_model = None

    def _evaluate_single_round(self, metadata, structure) -> Dict[str, Any]:
        """Perform a single evaluation round"""
        all_results = []
        total_score = 0
        max_total_score = 0
        
        # Run all evaluations for this round
        for category, evaluator_class in {**self.llm_evaluators, **self.traditional_evaluators}.items():
            try:
                if category in self.llm_evaluators:
                    evaluator = evaluator_class(self.llm_client, structure)
                else:
                    evaluator = evaluator_class(structure)
                
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
            'detailed_results': {r.category: r._asdict() for r in all_results}
        }
    
    def _calculate_confidence_interval(self, scores: List[float], confidence: float = 0.95) -> tuple:
        """Calculate confidence interval for scores"""
        if len(scores) < 2:
            return (scores[0], scores[0])
        
        import math
        mean = statistics.mean(scores)
        std_dev = statistics.stdev(scores)
        n = len(scores)
        
        # Using t-distribution for small samples
        from scipy import stats as scipy_stats
        try:
            t_val = scipy_stats.t.ppf((1 + confidence) / 2, n - 1)
            margin = t_val * (std_dev / math.sqrt(n))
            return (mean - margin, mean + margin)
        except ImportError:
            # Fallback to simple standard deviation if scipy not available
            margin = 1.96 * (std_dev / math.sqrt(n))  # Approximate 95% CI
            return (mean - margin, mean + margin)

    def _detect_project_type(self, structure: Dict[str, Any]) -> str:
        """Detect project type based on structure"""
        files = [f.lower() for f in structure['files']]

        # Web application indicators
        if any(f in files for f in ['app.py', 'main.py', 'server.js', 'index.js']) or 'django' in structure['frameworks']:
            return 'web_application'
        # CLI tool indicators
        elif any('cli' in f or 'command' in f for f in files) or any(
                'argparse' in content for content in structure['code_files'].values()):
            return 'cli_tool'
        # Library indicators
        elif any(f in files for f in ['setup.py', 'package.json', '__init__.py']) and not any(
                f in files for f in ['app.py', 'main.py']):
            return 'library_framework'
        # Microservice indicators
        elif any('docker' in f for f in files) and len(structure['languages']) <= 2:
            return 'microservice'
        else:
            return 'application'

    def _generate_report(self, metadata: ProjectMetadata, results: List[EvaluationResult],
                         total_score: int, max_total_score: int, grade: str) -> Dict[str, Any]:
        """Generate comprehensive evaluation report"""

        # Group results by category
        categories = {}
        for result in results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        # Calculate category scores
        category_scores = {}
        for category, category_results in categories.items():
            category_score = sum(r.score for r in category_results)
            category_max = sum(r.max_score for r in category_results)
            category_scores[category] = {
                'score': category_score,
                'max_score': category_max,
                'percentage': (category_score / category_max * 100) if category_max > 0 else 0,
                'details': [asdict(r) for r in category_results]
            }

        # Collect strengths and recommendations
        strengths = []
        recommendations = []
        llm_insights = []

        for result in results:
            strengths.extend(result.evidence)
            recommendations.extend(result.recommendations)
            if result.llm_analysis:
                llm_insights.append(
                    f"[{result.category}/{result.subcategory}] {result.llm_analysis}")

        return {
            'metadata': asdict(metadata),
            'evaluation_summary': {
                'total_score': total_score,
                'max_score': max_total_score,
                'percentage': (total_score / max_total_score * 100) if max_total_score > 0 else 0,
                'grade': grade,
                'evaluation_date': datetime.now().isoformat(),
                'llm_model': 'layered_ai'
            },
            'category_scores': category_scores,
            'strengths': list(set(strengths)),
            'recommendations': list(set(recommendations)),
            'llm_insights': llm_insights,
            'detailed_results': [asdict(r) for r in results]
        }


def show_detailed_history(db_path: str = "aieval_results.db", limit: int = None, source_filter: str = None):
    """Display evaluation history with complete rubric breakdown tables"""
    
    db = EvaluationDatabase(db_path)
    evaluations = db.get_evaluation_history(limit, source_filter)
    
    if not evaluations:
        print("📊 No evaluation history found.")
        return
    
    print("📊 DETAILED EVALUATION HISTORY WITH COMPLETE RUBRIC BREAKDOWN")
    print("=" * 90)
    
    for evaluation in evaluations:
        eval_id = evaluation['id']
        
        print(f"\n🎯 EVALUATION #{eval_id}: {evaluation['project_name']}")
        print(f"   Source: {evaluation['source_path']}")
        print(f"   Overall: {evaluation['total_score']}/{evaluation['max_score']} ({evaluation['percentage']:.1f}%) - Grade: {evaluation['grade']}")
        print(f"   Date: {evaluation['evaluation_date'][:10]} | AI: {evaluation['llm_model']}")
        
        if 'rubric_info' in evaluation:
            rubric = evaluation['rubric_info']
            print(f"   Rubric: v{rubric['version']} ({rubric['total_points']} points)")
        
        # Category scores table
        if 'category_breakdown' in evaluation and evaluation['category_breakdown']:
            print(f"\n   📊 CATEGORY SCORES:")
            print(f"   {'Category':<25} | {'Score':<8} | {'%':<6} | {'Weight'}")
            print(f"   {'-'*25}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}")
            
            for cat in evaluation['category_breakdown']:
                print(f"   {cat['category']:<25} | {cat['total_score']:2}/{cat['max_score']:2}   | {cat['percentage']:5.1f}% | {cat['weight']:.2f}")
        
        # Subcategory details table
        if 'subcategory_breakdown' in evaluation and evaluation['subcategory_breakdown']:
            print(f"\n   🔍 SUBCATEGORY BREAKDOWN:")
            print(f"   {'Category.Subcategory':<35} | {'Score':<8} | {'%':<6}")
            print(f"   {'-'*35}-+-{'-'*8}-+-{'-'*6}")
            
            for sub in evaluation['subcategory_breakdown']:
                full_name = f"{sub['category']}.{sub['subcategory']}"
                print(f"   {full_name:<35} | {sub['score']:2}/{sub['max_score']:2}   | {sub['percentage']:5.1f}%")
        
        print("\n" + "="*90)


def main():
    """CLI interface for Enhanced AI EvalEngine"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Enhanced AI EvalEngine - Repository Evaluation System with Layered AI')
    parser.add_argument(
        'source', nargs='?', help='Path to zip file, git repository URL, or local directory')
    parser.add_argument('--type', choices=['zip', 'git', 'directory', 'auto'], default='auto',
                        help='Source type (default: auto-detect)')
    parser.add_argument('--rubric', help='Path to custom rubric JSON file')
    parser.add_argument(
        '--output', help='Output file for results (default: stdout)')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--history', action='store_true',
                        help='Show detailed evaluation history with complete rubric breakdown')
    parser.add_argument('--source-filter', help='Filter history by source path (use with --history)')
    parser.add_argument('--limit', type=int, default=5, help='Number of history records to show (default: 5, use 0 for all)')
    parser.add_argument('--rounds', type=int, default=3, help='Number of evaluation rounds per provider (default: 3)')
    parser.add_argument('--providers', default='claude,openai', 
                       help='Provider and model specification. Format: provider:model1,model2 or just provider. '
                            'Example: claude:claude-3-5-sonnet-20241022,claude-3-haiku-20240307 openai:gpt-4,gpt-4o ollama:llama3.1')
    parser.add_argument('--multiround', action='store_true', help='Use multi-round evaluation with statistical analysis')
    parser.add_argument('--db-path', default='aieval_results.db',
                        help='Path to SQLite database (default: aieval_results.db)')

    args = parser.parse_args()

    # Show history if requested
    if args.history:
        limit = None if args.limit == 0 else args.limit
        show_detailed_history(args.db_path, limit=limit, source_filter=args.source_filter)
        return 0
    
    # Check if source is provided when not showing history
    if not args.source:
        parser.error("source is required unless using --history")

    # Initialize engine
    try:
        engine = AIEvalEngine(args.rubric)
        engine.database = EvaluationDatabase(args.db_path)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    try:
        if args.multiround:
            provider_models = parse_provider_models(args.providers)
            print(f"🎯 Starting multi-round evaluation with {args.rounds} rounds...")
            results = engine.evaluate_multiround_with_models(args.source, args.type, args.rounds, provider_models)
        else:
            print(f"🚀 Starting evaluation with layered AI services...")
            results = engine.evaluate_repository(args.source, args.type)

        # Output results
        if args.format == 'json':
            output = json.dumps(results, indent=2)
        else:
            if args.multiround:
                output = format_multiround_report(results)
            else:
                output = format_text_report(results)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✅ Results written to {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


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
    """Format multi-round evaluation results as human-readable text report"""
    lines = []
    
    # Header
    lines.append("=" * 80)
    lines.append("🎯 MULTI-ROUND AI EVALUATION RESULTS")
    lines.append("=" * 80)
    lines.append(f"📁 Project: {results['project_name']}")
    lines.append(f"📊 Rounds: {results['rounds']} per model")
    lines.append(f"🤖 Total Evaluations: {results['total_evaluations']}")
    lines.append(f"📈 Final Score: {results['final_score']:.1f}/100 ({results['final_score']:.1f}%)")
    lines.append(f"🏆 Final Grade: {results['final_grade']}")
    lines.append("")
    
    # Model-Level Statistics
    lines.append("🤖 MODEL PERFORMANCE STATISTICS:")
    lines.append("-" * 80)
    for model_key, stats in results['model_results'].items():
        lines.append(f"{model_key:>25}: {stats['avg_score']:5.1f} ± {stats['std_deviation']:4.1f} "
                    f"(range: {stats['min_score']:.1f}-{stats['max_score']:.1f})")
        lines.append(f"{'':>25}  CI: {stats['confidence_interval'][0]:.1f}-{stats['confidence_interval'][1]:.1f}")
    
    lines.append("")
    
    # Provider-Level Aggregates
    lines.append("📊 PROVIDER AVERAGES:")
    lines.append("-" * 60)
    for provider, provider_data in results['provider_results'].items():
        lines.append(f"{provider.upper():>8}: {provider_data['avg_score']:5.1f} (across {len(provider_data['models'])} models)")
        lines.append(f"{'':>8}  Models: {', '.join(provider_data['models'])}")
    
    lines.append("")
    
    # Round-by-Round Results
    lines.append("🔍 DETAILED ROUND RESULTS:")
    lines.append("-" * 80)
    
    # Group by model
    unique_models = list(set(f"{r['provider']}:{r['model']}" for r in results['all_rounds']))
    for model_key in sorted(unique_models):
        lines.append(f"\n{model_key.upper()} ROUNDS:")
        model_rounds = [r for r in results['all_rounds'] if f"{r['provider']}:{r['model']}" == model_key]
        
        for round_data in model_rounds:
            round_num = round_data['round']
            score = round_data['score']
            grade = round_data['result']['grade']
            lines.append(f"  Round {round_num}: {score:.1f}/100 ({score:.1f}%) - Grade: {grade}")
    
    lines.append("")
    lines.append("=" * 80)
    lines.append(f"💾 Multi-round evaluation ID: {results['multiround_id']}")
    lines.append("=" * 80)
    
    return '\n'.join(lines)

def format_text_report(results: Dict[str, Any]) -> str:
    """Format results as human-readable text report"""
    lines = []

    # Header
    lines.append("=" * 70)
    lines.append("🤖 AI EVALENGINE - LAYERED AI REPOSITORY EVALUATION")
    lines.append("=" * 70)
    lines.append("")

    # Metadata
    metadata = results['metadata']
    lines.append(f"📁 Project: {metadata['name']}")
    lines.append(f"🏷️  Type: {metadata['type']}")
    lines.append(
        f"💻 Languages: {', '.join(metadata['languages']) if metadata['languages'] else 'None detected'}")
    lines.append(
        f"🔧 Frameworks: {', '.join(metadata['frameworks']) if metadata['frameworks'] else 'None detected'}")
    lines.append(f"📊 Files: {metadata['file_count']}")
    lines.append(f"🧪 Has Tests: {'✅' if metadata['has_tests'] else '❌'}")
    lines.append(f"📚 Has Docs: {'✅' if metadata['has_docs'] else '❌'}")
    lines.append("")

    # Summary
    summary = results['evaluation_summary']
    lines.append(
        f"🎯 OVERALL SCORE: {summary['total_score']}/{summary['max_score']} ({summary['percentage']:.1f}%)")
    lines.append(f"🏆 GRADE: {summary['grade']}")
    lines.append(f"🤖 LLM Model: {summary['llm_model']}")
    lines.append(f"📊 Evaluation ID: {results.get('evaluation_id', 'N/A')}")
    lines.append("")

    # Category breakdown
    lines.append("📋 CATEGORY BREAKDOWN:")
    lines.append("-" * 50)
    for category, score_info in results['category_scores'].items():
        category_name = category.replace('_', ' ').title()
        lines.append(
            f"{category_name}: {score_info['score']}/{score_info['max_score']} ({score_info['percentage']:.1f}%)")
    lines.append("")

    # Strengths
    if results['strengths']:
        lines.append("✅ KEY STRENGTHS:")
        for strength in results['strengths'][:6]:  # Top 6
            lines.append(f"  • {strength}")
        lines.append("")

    # Recommendations
    if results['recommendations']:
        lines.append("🔧 IMPROVEMENT RECOMMENDATIONS:")
        for rec in results['recommendations'][:6]:  # Top 6
            lines.append(f"  • {rec}")
        lines.append("")

    # LLM Insights (if available)
    if results.get('llm_insights'):
        lines.append("🧠 LLM ANALYSIS INSIGHTS:")
        lines.append("-" * 50)
        for insight in results['llm_insights'][:2]:  # Show first 2 insights
            # Truncate long insights
            if len(insight) > 300:
                insight = insight[:300] + "..."
            lines.append(f"  {insight}")
            lines.append("")

    lines.append("=" * 70)
    lines.append("💡 Powered by Layered AI: Claude → OpenAI → Ollama")
    lines.append("=" * 70)

    return "\n".join(lines)


if __name__ == "__main__":
    exit(main())