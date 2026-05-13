"""
AI提供商基类和具体实现
支持Claude、Gemini API 和 Ollama 本地推理
中文优先，支持中国各学科试卷识别
"""
import os
import json as _json
import re as _re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """AI提供商基类"""

    @abstractmethod
    def is_available(self) -> bool:
        """检查提供商是否可用"""
        pass

    @abstractmethod
    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        """纠正OCR文本"""
        pass

    @abstractmethod
    def parse_questions(self, text: str) -> Dict[str, Any]:
        """解析题目"""
        pass

    @abstractmethod
    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """分析单个题目"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        pass


# ===== 通用中文提示词 =====

OCR_CORRECT_PROMPT = """请纠正以下OCR识别文本中的错误。这是中国试卷的扫描识别结果，以中文为主，可能包含英文、数学公式等。

常见OCR错误：
- 中文字符混淆：已/己、人/入、干/千、日/曰等
- 数字和符号：0/O、1/l/I、5/S、+/t等
- 数学符号丢失或误识别：分数线、根号、积分号、等于号等
- 括号不匹配：中英文括号混用
- 空格和换行错乱

OCR置信度：{confidence}

原始OCR文本：
---
{ocr_text}
---

请提供：
1. 纠正后的文本（修正明显OCR错误，保留原始结构和格式）
2. 修正列表
3. 纠正置信度（高/中/低）

格式：
【纠正文本】
[纠正后的文本]

【修正列表】
- [修正1：原文→纠正]
- [修正2：原文→纠正]

【置信度】[高/中/低]"""

QUESTION_PARSE_PROMPT = """请分析以下文本，提取其中的所有试题。这是中国学校的试卷内容，可能来自数学、语文、英语、物理、化学、生物、政治、历史、地理等学科。

文本内容：
---
{text}
---

请按以下中国常见题型进行识别和分类：

【数学】选择题、填空题、解答题、证明题、计算题
【语文】选择题、填空题、阅读理解、文言文阅读、古诗词鉴赏、语言文字运用、作文
【英语】选择题、完形填空、阅读理解、语法填空、短文改错、书面表达
【物理】选择题、实验题、计算题、填空题
【化学】选择题、实验题、计算题、填空题、推断题
【生物】选择题、非选择题(填空/实验)
【政治/历史/地理】选择题、非选择题(简答/论述/材料分析)

请返回JSON数组，每道题包含：
- question_number: 题号(如 1, 2, 3)
- content: 题目内容(完整文本)
- question_type: 题型(如"选择题"、"填空题"、"解答题"等)
- subject: 学科(如"数学"、"语文"、"英语"等，不确定填"通用")
- difficulty: 难度("简单"/"中等"/"困难")
- choices: 选项列表(如有，格式如["A. xxx", "B. xxx", "C. xxx", "D. xxx"])
- answer: 答案(如有)
- section_title: 所属大题标题(如"一、选择题")
- tags: 知识点标签(如["二次函数", "最值问题"])

如果没有识别到试题，返回空数组 []
只返回JSON，不要其他内容。"""

QUESTION_ANALYZE_PROMPT = """请分析这道题目，返回JSON格式的详细信息。

题目：{question}

请返回：
{{
    "question_type": "题型(选择题/填空题/解答题等)",
    "subject": "学科(数学/语文/英语/物理/化学等)",
    "difficulty": "难度(简单/中等/困难)",
    "difficulty_reasoning": "难度判断理由",
    "knowledge_points": ["知识点1", "知识点2"],
    "choices": ["A. ...", "B. ..."] (如有选项),
    "suggested_answer": "参考答案",
    "analysis": "解题思路",
    "tags": ["标签1", "标签2"]
}}

只返回JSON，不要其他内容。"""


class ClaudeProvider(AIProvider):
    """Claude AI提供商"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = None

        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"初始化Claude客户端失败: {e}")
                self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def get_provider_name(self) -> str:
        return "Claude"

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        if not self.is_available():
            return {
                'success': False,
                'error': 'Claude不可用',
                'corrected_text': ocr_text
            }

        try:
            prompt = OCR_CORRECT_PROMPT.format(
                confidence=f"{confidence:.2%}",
                ocr_text=ocr_text
            )

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # 解析中文格式响应
            corrected_text = ocr_text
            corrections = []
            ai_confidence = 'medium'

            if '【纠正文本】' in response_text:
                parts = response_text.split('【纠正文本】')[1]
                if '【修正列表】' in parts:
                    corrected_text = parts.split('【修正列表】')[0].strip()
                    corrections_part = parts.split('【修正列表】')[1]
                    if '【置信度】' in corrections_part:
                        corrections_text = corrections_part.split('【置信度】')[0].strip()
                        conf_text = corrections_part.split('【置信度】')[1].strip()
                        # 映射中文置信度
                        if '高' in conf_text:
                            ai_confidence = 'high'
                        elif '低' in conf_text:
                            ai_confidence = 'low'
                        else:
                            ai_confidence = 'medium'
                        corrections = [c.strip('- ').strip() for c in corrections_text.split('\n') if c.strip() and c.strip() != '-']
                else:
                    corrected_text = parts.strip()
            # 兼容旧格式
            elif 'CORRECTED TEXT:' in response_text:
                parts = response_text.split('CORRECTED TEXT:')[1]
                if 'CORRECTIONS MADE:' in parts:
                    corrected_text = parts.split('CORRECTIONS MADE:')[0].strip()
                    corrections_part = parts.split('CORRECTIONS MADE:')[1]
                    if 'CONFIDENCE:' in corrections_part:
                        corrections_text = corrections_part.split('CONFIDENCE:')[0].strip()
                        ai_confidence = corrections_part.split('CONFIDENCE:')[1].strip().lower()
                        corrections = [c.strip('- ').strip() for c in corrections_text.split('\n') if c.strip()]
                else:
                    corrected_text = parts.strip()

            return {
                'success': True,
                'corrected_text': corrected_text,
                'original_text': ocr_text,
                'corrections': corrections,
                'ai_confidence': ai_confidence,
                'ocr_confidence': confidence,
                'provider': 'Claude'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'corrected_text': ocr_text
            }

    def parse_questions(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Claude不可用', 'questions': []}

        try:
            prompt = QUESTION_PARSE_PROMPT.format(text=text)

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            import json
            import re

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
                questions = json.loads(json_str)
            else:
                questions = json.loads(response_text)

            return {
                'success': True,
                'questions': questions,
                'total_questions': len(questions),
                'provider': 'Claude'
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'questions': []}

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Claude不可用'}

        try:
            prompt = QUESTION_ANALYZE_PROMPT.format(question=question_text)

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            import json
            import re

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                analysis = json.loads(response_text)

            return {'success': True, 'provider': 'Claude', **analysis}

        except Exception as e:
            return {'success': False, 'error': str(e)}


class GeminiProvider(AIProvider):
    """Google Gemini AI提供商"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.client = None

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel('gemini-1.5-pro')
            except Exception as e:
                print(f"初始化Gemini客户端失败: {e}")
                self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def get_provider_name(self) -> str:
        return "Gemini"

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        if not self.is_available():
            return {
                'success': False,
                'error': 'Gemini不可用',
                'corrected_text': ocr_text
            }

        try:
            prompt = OCR_CORRECT_PROMPT.format(
                confidence=f"{confidence:.2%}",
                ocr_text=ocr_text
            )

            response = self.client.generate_content(prompt)
            response_text = response.text

            corrected_text = ocr_text
            corrections = []
            ai_confidence = 'medium'

            if '【纠正文本】' in response_text:
                parts = response_text.split('【纠正文本】')[1]
                if '【修正列表】' in parts:
                    corrected_text = parts.split('【修正列表】')[0].strip()
                    corrections_part = parts.split('【修正列表】')[1]
                    if '【置信度】' in corrections_part:
                        corrections_text = corrections_part.split('【置信度】')[0].strip()
                        conf_text = corrections_part.split('【置信度】')[1].strip()
                        if '高' in conf_text:
                            ai_confidence = 'high'
                        elif '低' in conf_text:
                            ai_confidence = 'low'
                        else:
                            ai_confidence = 'medium'
                        corrections = [c.strip('- ').strip() for c in corrections_text.split('\n') if c.strip() and c.strip() != '-']
                else:
                    corrected_text = parts.strip()

            return {
                'success': True,
                'corrected_text': corrected_text,
                'original_text': ocr_text,
                'corrections': corrections,
                'ai_confidence': ai_confidence,
                'ocr_confidence': confidence,
                'provider': 'Gemini'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'corrected_text': ocr_text
            }

    def parse_questions(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Gemini不可用', 'questions': []}

        try:
            prompt = QUESTION_PARSE_PROMPT.format(text=text)

            response = self.client.generate_content(prompt)
            response_text = response.text

            import json
            import re

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                questions = json.loads(json_match.group(1))
            else:
                array_match = re.search(r'\[[\s\S]*\]', response_text)
                if array_match:
                    questions = json.loads(array_match.group(0))
                else:
                    questions = []

            return {
                'success': True,
                'questions': questions,
                'total_questions': len(questions),
                'provider': 'Gemini'
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'questions': []}

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Gemini不可用'}

        try:
            prompt = QUESTION_ANALYZE_PROMPT.format(question=question_text)

            response = self.client.generate_content(prompt)
            response_text = response.text

            import json
            import re

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                obj_match = re.search(r'\{[\s\S]*\}', response_text)
                if obj_match:
                    analysis = json.loads(obj_match.group(0))
                else:
                    analysis = {}

            return {'success': True, 'provider': 'Gemini', **analysis}

        except Exception as e:
            return {'success': False, 'error': str(e)}


class OllamaProvider(AIProvider):
    """Ollama 本地推理提供商 — 无需 API Key"""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model or os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')
        self.base_url = (base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')).rstrip('/')
        self._available = False
        self._check_available()

    def _check_available(self):
        """检查 Ollama 服务是否运行且模型可用"""
        try:
            req = urllib.request.Request(f'{self.base_url}/api/tags', method='GET')
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read().decode('utf-8'))
                models = [m.get('name', '') for m in data.get('models', [])]
                matched = any(m == self.model or m.startswith(self.model.split(':')[0]) for m in models)
                if matched:
                    self._available = True
                    print(f"✅ Ollama 本地模型可用: {self.model}")
                else:
                    available_list = ', '.join(models[:5]) if models else '(无模型)'
                    print(f"⚠️ Ollama 模型 {self.model} 未找到。可用模型: {available_list}")
                    if models:
                        # 优先选择更大的中文模型
                        preferred_order = [m for m in models if any(k in m for k in ['qwen', 'chatglm', 'chinese', 'yi'])]
                        self.model = preferred_order[0] if preferred_order else models[0]
                        self._available = True
                        print(f"   → 自动切换到: {self.model}")
        except urllib.error.URLError:
            print("⚠️ Ollama 服务未运行 (请执行: ollama serve)")
        except Exception as e:
            print(f"⚠️ Ollama 检查失败: {e}")

    def is_available(self) -> bool:
        return self._available

    def get_provider_name(self) -> str:
        return "Ollama"

    def _generate(self, prompt: str, max_tokens: int = 4000) -> Optional[str]:
        """调用 Ollama API 生成文本"""
        try:
            payload = _json.dumps({
                'model': self.model,
                'prompt': prompt,
                'stream': False,
                'options': {'num_predict': max_tokens}
            }).encode('utf-8')
            req = urllib.request.Request(
                f'{self.base_url}/api/generate',
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = _json.loads(resp.read().decode('utf-8'))
                return result.get('response', '')
        except Exception as e:
            print(f"Ollama 生成失败: {e}")
            return None

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Ollama不可用', 'corrected_text': ocr_text}

        prompt = OCR_CORRECT_PROMPT.format(
            confidence=f"{confidence:.2%}",
            ocr_text=ocr_text
        )

        response_text = self._generate(prompt, max_tokens=4000)
        if response_text is None:
            return {'success': False, 'error': 'Ollama生成失败', 'corrected_text': ocr_text}

        corrected_text = ocr_text
        corrections = []
        ai_confidence = 'medium'

        if '【纠正文本】' in response_text:
            parts = response_text.split('【纠正文本】')[1]
            if '【修正列表】' in parts:
                corrected_text = parts.split('【修正列表】')[0].strip()
                corrections_part = parts.split('【修正列表】')[1]
                if '【置信度】' in corrections_part:
                    corrections_text = corrections_part.split('【置信度】')[0].strip()
                    conf_text = corrections_part.split('【置信度】')[1].strip()
                    if '高' in conf_text:
                        ai_confidence = 'high'
                    elif '低' in conf_text:
                        ai_confidence = 'low'
                    else:
                        ai_confidence = 'medium'
                    corrections = [c.strip('- ').strip() for c in corrections_text.split('\n') if c.strip() and c.strip() != '-']
            else:
                corrected_text = parts.strip()

        return {
            'success': True,
            'corrected_text': corrected_text,
            'original_text': ocr_text,
            'corrections': corrections,
            'ai_confidence': ai_confidence,
            'ocr_confidence': confidence,
            'provider': 'Ollama'
        }

    def parse_questions(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Ollama不可用', 'questions': []}

        prompt = QUESTION_PARSE_PROMPT.format(text=text)

        response_text = self._generate(prompt, max_tokens=8000)
        if response_text is None:
            return {'success': False, 'error': 'Ollama生成失败', 'questions': []}

        questions = []
        try:
            json_match = _re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                questions = _json.loads(json_match.group(1))
            else:
                array_match = _re.search(r'\[[\s\S]*\]', response_text)
                if array_match:
                    questions = _json.loads(array_match.group(0))
        except _json.JSONDecodeError:
            pass

        return {
            'success': True,
            'questions': questions,
            'total_questions': len(questions),
            'provider': 'Ollama'
        }

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Ollama不可用'}

        prompt = QUESTION_ANALYZE_PROMPT.format(question=question_text)

        response_text = self._generate(prompt, max_tokens=2000)
        if response_text is None:
            return {'success': False, 'error': 'Ollama生成失败'}

        try:
            json_match = _re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                analysis = _json.loads(json_match.group(1))
            else:
                obj_match = _re.search(r'\{[\s\S]*\}', response_text)
                if obj_match:
                    analysis = _json.loads(obj_match.group(0))
                else:
                    analysis = {}
            return {'success': True, 'provider': 'Ollama', **analysis}
        except _json.JSONDecodeError:
            return {'success': False, 'error': 'JSON解析失败', 'raw_response': response_text[:500]}
