"""
AI辅助识别和纠正模块
使用Claude API进行OCR结果纠正和智能题目解析
"""
import os
from typing import Dict, Any, List, Optional
import anthropic


class AIAssistant:
    """AI助手，用于OCR纠正和题目解析"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化AI助手
        :param api_key: Anthropic API密钥，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = None

        if self.api_key:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"初始化Claude客户端失败: {e}")
                self.client = None

    def is_available(self) -> bool:
        """检查AI助手是否可用"""
        return self.client is not None

    def correct_ocr_text(self, ocr_text: str, confidence: float = 0.0) -> Dict[str, Any]:
        """
        使用AI纠正OCR识别的文本
        :param ocr_text: OCR识别的原始文本
        :param confidence: OCR识别的平均置信度
        :return: 纠正结果
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用，请配置ANTHROPIC_API_KEY环境变量',
                'corrected_text': ocr_text,
                'original_text': ocr_text
            }

        try:
            prompt = f"""Please correct the following text that was extracted using OCR. The text is primarily English with some Chinese descriptions. The OCR confidence is {confidence:.2%}.

Common OCR errors to watch for:
- Confusing similar characters (0/O, 1/l/I, 5/S, etc.)
- Missing or extra spaces
- Mathematical symbols and equations
- Special characters

Original OCR text:
---
{ocr_text}
---

Please provide:
1. The corrected text (fix obvious OCR errors but preserve the original structure)
2. A brief list of corrections made
3. Your confidence level (high/medium/low) in the corrections

Format your response as:
CORRECTED TEXT:
[corrected text here]

CORRECTIONS MADE:
- [list of corrections]

CONFIDENCE: [high/medium/low]"""

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = message.content[0].text

            # 解析响应
            corrected_text = ocr_text
            corrections = []
            ai_confidence = 'medium'

            if 'CORRECTED TEXT:' in response_text:
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
                'ocr_confidence': confidence
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'corrected_text': ocr_text,
                'original_text': ocr_text
            }

    def parse_questions(self, text: str) -> Dict[str, Any]:
        """
        使用AI智能解析和提取题目
        :param text: 文本内容
        :return: 解析结果
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用',
                'questions': []
            }

        try:
            prompt = f"""Please analyze the following text and extract individual questions. This text may contain exam questions in English with some Chinese descriptions.

Text to analyze:
---
{text}
---

For each question found, please provide:
1. The complete question text
2. Question type (multiple_choice, true_false, short_answer, essay, fill_in_blank, calculation, etc.)
3. Difficulty level (easy, medium, hard)
4. Any answer choices (for multiple choice questions)
5. Key knowledge points/topics (as tags)

Format your response as a JSON array:
```json
[
  {{
    "question_number": 1,
    "content": "question text here",
    "question_type": "multiple_choice",
    "difficulty": "medium",
    "choices": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "tags": ["algebra", "equations"],
    "notes": "any additional notes"
  }},
  ...
]
```

If no clear questions are found, return an empty array []."""

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = message.content[0].text

            # 提取JSON部分
            import json
            import re

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
                questions = json.loads(json_str)
            else:
                # 尝试直接解析整个响应
                questions = json.loads(response_text)

            return {
                'success': True,
                'questions': questions,
                'total_questions': len(questions)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'questions': []
            }

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """
        分析单个题目，提取详细信息
        :param question_text: 题目文本
        :return: 分析结果
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用'
            }

        try:
            prompt = f"""Please analyze the following question and provide detailed information:

Question:
---
{question_text}
---

Please provide:
1. Question type (multiple_choice, true_false, short_answer, essay, fill_in_blank, calculation, etc.)
2. Difficulty level (easy, medium, hard) with brief reasoning
3. Main knowledge points/topics (as tags)
4. Subject area (if identifiable)
5. If it's a multiple choice question, list the choices
6. Any suggested answer or solution approach (if obvious from the question)

Format your response as JSON:
```json
{{
  "question_type": "type",
  "difficulty": "level",
  "difficulty_reasoning": "why this difficulty",
  "tags": ["tag1", "tag2"],
  "subject": "subject name",
  "choices": ["A. ...", "B. ..."] or null,
  "suggested_answer": "answer if obvious" or null,
  "notes": "any additional observations"
}}
```"""

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = message.content[0].text

            # 提取JSON
            import json
            import re

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
                analysis = json.loads(json_str)
            else:
                analysis = json.loads(response_text)

            return {
                'success': True,
                **analysis
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def batch_correct_questions(self, questions: List[str]) -> Dict[str, Any]:
        """
        批量纠正和分析题目
        :param questions: 题目列表
        :return: 纠正和分析结果
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'AI助手不可用',
                'questions': questions
            }

        results = []
        for idx, question in enumerate(questions):
            try:
                # 分析每个题目
                analysis = self.analyze_question(question)
                if analysis['success']:
                    results.append({
                        'original': question,
                        'analysis': analysis,
                        'index': idx
                    })
                else:
                    results.append({
                        'original': question,
                        'error': analysis.get('error'),
                        'index': idx
                    })
            except Exception as e:
                results.append({
                    'original': question,
                    'error': str(e),
                    'index': idx
                })

        return {
            'success': True,
            'questions': results,
            'total': len(results)
        }
