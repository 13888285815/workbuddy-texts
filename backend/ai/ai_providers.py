"""
AI提供商基类和具体实现
支持 DeepSeek、通义千问、SiliconFlow、Gemini、Claude 和 Ollama 本地推理
中文优先，支持中国各学科试卷识别
所有云端 Provider 均有免费额度，超时控制在 50 秒内
"""
import os
import time
import json as _json
import re as _re
import urllib.request
import urllib.error
import threading
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


# ===== 全局超时控制 =====
DEFAULT_TIMEOUT = 50  # 秒，单次 AI 调用最大时长（留 10 秒给降级）


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

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型详细信息（子类可覆盖）"""
        return {
            'provider': self.get_provider_name(),
            'free_tier': True,
        }

    @staticmethod
    def _parse_json_response(response_text: str) -> Any:
        """通用 JSON 响应解析，兼容各种格式"""
        # 1. 尝试提取 ```json ... ``` 块
        json_match = _re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            return _json.loads(json_match.group(1))
        # 2. 尝试提取 ``` ... ``` 块
        code_match = _re.search(r'```\s*([\s\S]*?)\s*```', response_text)
        if code_match:
            return _json.loads(code_match.group(1))
        # 3. 直接解析
        return _json.loads(response_text)

    @staticmethod
    def _parse_json_array(response_text: str) -> List:
        """解析 JSON 数组响应，带多种 fallback"""
        try:
            return AIProvider._parse_json_response(response_text)
        except (_json.JSONDecodeError, ValueError):
            pass
        # fallback: 提取 [...] 块
        array_match = _re.search(r'\[[\s\S]*\]', response_text)
        if array_match:
            try:
                return _json.loads(array_match.group(0))
            except _json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def _parse_json_object(response_text: str) -> Dict:
        """解析 JSON 对象响应，带多种 fallback"""
        try:
            return AIProvider._parse_json_response(response_text)
        except (_json.JSONDecodeError, ValueError):
            pass
        # fallback: 提取 {...} 块
        obj_match = _re.search(r'\{[\s\S]*\}', response_text)
        if obj_match:
            try:
                return _json.loads(obj_match.group(0))
            except _json.JSONDecodeError:
                pass
        return {}

    @staticmethod
    def _parse_ocr_correction(response_text: str, ocr_text: str) -> Dict[str, Any]:
        """通用 OCR 纠正结果解析"""
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
                    corrections = [c.strip('- ').strip() for c in corrections_text.split('\n')
                                   if c.strip() and c.strip() != '-']
            else:
                corrected_text = parts.strip()

        return {
            'corrected_text': corrected_text,
            'corrections': corrections,
            'ai_confidence': ai_confidence,
        }

    def _call_with_timeout(self, func, timeout: int = DEFAULT_TIMEOUT, *args, **kwargs):
        """带超时的调用包装，超时返回 None"""
        result = [None]
        error = [None]

        def _worker():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # 超时
            return None, TimeoutError(f"AI调用超时({timeout}秒)")
        if error[0]:
            return None, error[0]
        return result[0], None


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


# ===== OpenAI 兼容 API 基类 =====
# DeepSeek、通义千问、SiliconFlow 都兼容 OpenAI Chat API 格式

class OpenAICompatProvider(AIProvider):
    """OpenAI 兼容 API 基类，所有使用 OpenAI 格式的云端 Provider 继承此类"""

    # 子类需要覆盖以下属性
    PROVIDER_NAME = "OpenAICompat"
    DEFAULT_BASE_URL = ""
    DEFAULT_MODEL = ""
    API_KEY_ENV = ""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None):
        self.api_key = api_key or os.getenv(self.API_KEY_ENV, '')
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self.model = model or self.DEFAULT_MODEL
        self._available = False
        self._check_available()

    def _check_available(self):
        """检查 API Key 是否已配置"""
        if self.api_key and self.api_key != f'your_{self.API_KEY_ENV.lower()}_here':
            self._available = True
            print(f"✅ {self.PROVIDER_NAME} 可用 (模型: {self.model})")
        else:
            print(f"⚠️ {self.PROVIDER_NAME} 不可用 (请设置 {self.API_KEY_ENV})")

    def is_available(self) -> bool:
        return self._available

    def get_provider_name(self) -> str:
        return self.PROVIDER_NAME

    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': self.PROVIDER_NAME,
            'model': self.model,
            'free_tier': True,
            'base_url': self.base_url,
        }

    def _chat(self, messages: List[Dict], max_tokens: int = 4000,
              temperature: float = 0.3) -> Optional[str]:
        """调用 OpenAI 兼容的 Chat API"""
        try:
            payload = _json.dumps({
                'model': self.model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'stream': False,
            }).encode('utf-8')

            req = urllib.request.Request(
                f'{self.base_url}/chat/completions',
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}',
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                result = _json.loads(resp.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            print(f"{self.PROVIDER_NAME} API 错误 {e.code}: {body[:300]}")
            return None
        except Exception as e:
            print(f"{self.PROVIDER_NAME} 调用失败: {e}")
            return None

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': f'{self.PROVIDER_NAME}不可用', 'corrected_text': ocr_text}

        prompt = OCR_CORRECT_PROMPT.format(
            confidence=f"{confidence:.2%}",
            ocr_text=ocr_text
        )
        response_text = self._chat([{"role": "user", "content": prompt}], max_tokens=4000)
        if response_text is None:
            return {'success': False, 'error': f'{self.PROVIDER_NAME}生成失败', 'corrected_text': ocr_text}

        parsed = self._parse_ocr_correction(response_text, ocr_text)
        return {
            'success': True,
            'corrected_text': parsed['corrected_text'],
            'original_text': ocr_text,
            'corrections': parsed['corrections'],
            'ai_confidence': parsed['ai_confidence'],
            'ocr_confidence': confidence,
            'provider': self.PROVIDER_NAME
        }

    def parse_questions(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': f'{self.PROVIDER_NAME}不可用', 'questions': []}

        prompt = QUESTION_PARSE_PROMPT.format(text=text)
        response_text = self._chat([{"role": "user", "content": prompt}], max_tokens=8000)
        if response_text is None:
            return {'success': False, 'error': f'{self.PROVIDER_NAME}生成失败', 'questions': []}

        questions = self._parse_json_array(response_text)
        return {
            'success': True,
            'questions': questions,
            'total_questions': len(questions),
            'provider': self.PROVIDER_NAME
        }

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': f'{self.PROVIDER_NAME}不可用'}

        prompt = QUESTION_ANALYZE_PROMPT.format(question=question_text)
        response_text = self._chat([{"role": "user", "content": prompt}], max_tokens=2000)
        if response_text is None:
            return {'success': False, 'error': f'{self.PROVIDER_NAME}生成失败'}

        analysis = self._parse_json_object(response_text)
        return {'success': True, 'provider': self.PROVIDER_NAME, **analysis}


# ===== DeepSeek Provider =====

class DeepSeekProvider(OpenAICompatProvider):
    """
    DeepSeek AI 提供商
    免费额度：注册送 500 万 tokens，中文能力极强
    获取 API Key：https://platform.deepseek.com/api_keys
    """
    PROVIDER_NAME = "DeepSeek"
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"  # deepseek-chat = DeepSeek-V3，免费可用
    API_KEY_ENV = "DEEPSEEK_API_KEY"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': self.PROVIDER_NAME,
            'model': self.model,
            'free_tier': True,
            'free_quota': '注册送500万tokens',
            'get_key': 'https://platform.deepseek.com/api_keys',
        }


# ===== 通义千问 Provider =====

class QwenProvider(OpenAICompatProvider):
    """
    通义千问 AI 提供商（阿里云 DashScope）
    免费额度：开通即送 100 万 tokens 免费额度，qwen-turbo 模型免费
    获取 API Key：https://dashscope.console.aliyun.com/apiKey
    """
    PROVIDER_NAME = "Qwen"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = "qwen-turbo"  # qwen-turbo 免费且速度快
    API_KEY_ENV = "DASHSCOPE_API_KEY"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': self.PROVIDER_NAME,
            'model': self.model,
            'free_tier': True,
            'free_quota': 'qwen-turbo 永久免费，其他模型送100万tokens',
            'get_key': 'https://dashscope.console.aliyun.com/apiKey',
        }


# ===== SiliconFlow Provider =====

class SiliconFlowProvider(OpenAICompatProvider):
    """
    硅基流动 AI 提供商
    免费额度：注册送 2000 万 tokens，提供 Qwen/DeepSeek/GLM 等多种免费模型
    获取 API Key：https://cloud.siliconflow.cn/account/ak
    """
    PROVIDER_NAME = "SiliconFlow"
    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # 免费 7B 模型
    API_KEY_ENV = "SILICONFLOW_API_KEY"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': self.PROVIDER_NAME,
            'model': self.model,
            'free_tier': True,
            'free_quota': '注册送2000万tokens，多种免费模型',
            'get_key': 'https://cloud.siliconflow.cn/account/ak',
            'free_models': [
                'Qwen/Qwen2.5-7B-Instruct',
                'Qwen/Qwen2.5-72B-Instruct',
                'deepseek-ai/DeepSeek-V3',
                'THUDM/glm-4-9b-chat',
            ],
        }


# ===== Gemini Provider (升级) =====

class GeminiProvider(AIProvider):
    """
    Google Gemini AI 提供商
    免费额度：Gemini 2.0 Flash 免费，每分钟 15 次请求
    获取 API Key：https://aistudio.google.com/app/apikey
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.client = None
        self.model_name = 'gemini-2.0-flash'  # 免费 + 快速

        if self.api_key and self.api_key != 'your_google_api_key_here':
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
                print(f"✅ Gemini 可用 (模型: {self.model_name})")
            except Exception as e:
                print(f"初始化Gemini客户端失败: {e}")
                self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def get_provider_name(self) -> str:
        return "Gemini"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': 'Gemini',
            'model': self.model_name,
            'free_tier': True,
            'free_quota': 'Gemini 2.0 Flash 免费，15 RPM',
            'get_key': 'https://aistudio.google.com/app/apikey',
        }

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Gemini不可用', 'corrected_text': ocr_text}

        try:
            prompt = OCR_CORRECT_PROMPT.format(
                confidence=f"{confidence:.2%}",
                ocr_text=ocr_text
            )

            response = self.client.generate_content(prompt)
            response_text = response.text

            parsed = self._parse_ocr_correction(response_text, ocr_text)
            return {
                'success': True,
                'corrected_text': parsed['corrected_text'],
                'original_text': ocr_text,
                'corrections': parsed['corrections'],
                'ai_confidence': parsed['ai_confidence'],
                'ocr_confidence': confidence,
                'provider': 'Gemini'
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'corrected_text': ocr_text}

    def parse_questions(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Gemini不可用', 'questions': []}

        try:
            prompt = QUESTION_PARSE_PROMPT.format(text=text)
            response = self.client.generate_content(prompt)
            response_text = response.text

            questions = self._parse_json_array(response_text)
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

            analysis = self._parse_json_object(response_text)
            return {'success': True, 'provider': 'Gemini', **analysis}

        except Exception as e:
            return {'success': False, 'error': str(e)}


# ===== Claude Provider =====

class ClaudeProvider(AIProvider):
    """Claude AI 提供商（付费，作为高端选项保留）"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = None

        if self.api_key and self.api_key != 'your_anthropic_api_key_here':
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                print("✅ Claude 可用")
            except Exception as e:
                print(f"初始化Claude客户端失败: {e}")
                self.client = None

    def is_available(self) -> bool:
        return self.client is not None

    def get_provider_name(self) -> str:
        return "Claude"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': 'Claude',
            'model': 'claude-3-5-sonnet-20241022',
            'free_tier': False,
        }

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        if not self.is_available():
            return {'success': False, 'error': 'Claude不可用', 'corrected_text': ocr_text}

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
            parsed = self._parse_ocr_correction(response_text, ocr_text)

            return {
                'success': True,
                'corrected_text': parsed['corrected_text'],
                'original_text': ocr_text,
                'corrections': parsed['corrections'],
                'ai_confidence': parsed['ai_confidence'],
                'ocr_confidence': confidence,
                'provider': 'Claude'
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'corrected_text': ocr_text}

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
            questions = self._parse_json_array(response_text)

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
            analysis = self._parse_json_object(response_text)
            return {'success': True, 'provider': 'Claude', **analysis}

        except Exception as e:
            return {'success': False, 'error': str(e)}


# ===== Ollama Provider (升级) =====

class OllamaProvider(AIProvider):
    """
    Ollama 本地推理提供商 — 无需 API Key，完全免费
    推荐模型：qwen2.5:7b (4.4GB，中文能力好) 或 qwen2.5:14b (9GB，更强)
    """

    # 模型优先级列表（从大到小，优先选择更强的中文模型）
    PREFERRED_MODELS = [
        'qwen2.5:14b', 'qwen2.5:7b', 'qwen2.5:3b', 'qwen2.5:1.5b',
        'qwen3:8b', 'qwen3:4b', 'qwen3:1.7b',
        'chatglm3:6b', 'chatglm4:9b',
        'yi:34b', 'yi:6b',
    ]

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model or os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
        self.base_url = (base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')).rstrip('/')
        self._available = False
        self._installed_models = []
        self._check_available()

    def _check_available(self):
        """检查 Ollama 服务是否运行且模型可用"""
        try:
            req = urllib.request.Request(f'{self.base_url}/api/tags', method='GET')
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read().decode('utf-8'))
                self._installed_models = [m.get('name', '') for m in data.get('models', [])]
                matched = any(m == self.model or m.startswith(self.model.split(':')[0]) for m in self._installed_models)
                if matched:
                    self._available = True
                    print(f"✅ Ollama 本地模型可用: {self.model}")
                else:
                    available_list = ', '.join(self._installed_models[:5]) if self._installed_models else '(无模型)'
                    print(f"⚠️ Ollama 模型 {self.model} 未找到。可用模型: {available_list}")
                    if self._installed_models:
                        # 按优先级选择最佳的已安装中文模型
                        best = None
                        for pref in self.PREFERRED_MODELS:
                            for m in self._installed_models:
                                if m.startswith(pref.split(':')[0]):
                                    best = m
                                    break
                            if best:
                                break
                        if not best:
                            best = self._installed_models[0]
                        self.model = best
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

    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': 'Ollama',
            'model': self.model,
            'free_tier': True,
            'free_quota': '完全免费，本地推理',
            'installed_models': self._installed_models[:10],
            'recommended_pull': 'ollama pull qwen2.5:7b (4.4GB，推荐)',
        }

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
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
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

        parsed = self._parse_ocr_correction(response_text, ocr_text)
        return {
            'success': True,
            'corrected_text': parsed['corrected_text'],
            'original_text': ocr_text,
            'corrections': parsed['corrections'],
            'ai_confidence': parsed['ai_confidence'],
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

        questions = self._parse_json_array(response_text)
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

        analysis = self._parse_json_object(response_text)
        if not analysis:
            return {'success': False, 'error': 'JSON解析失败', 'raw_response': response_text[:500]}
        return {'success': True, 'provider': 'Ollama', **analysis}


# ===== 导出所有 Provider =====

ALL_PROVIDERS = {
    'deepseek': DeepSeekProvider,
    'qwen': QwenProvider,
    'siliconflow': SiliconFlowProvider,
    'gemini': GeminiProvider,
    'claude': ClaudeProvider,
    'ollama': OllamaProvider,
}

# auto 模式优先级：免费云端模型优先，本地兜底
AUTO_PRIORITY = ['deepseek', 'qwen', 'siliconflow', 'gemini', 'claude', 'ollama']
