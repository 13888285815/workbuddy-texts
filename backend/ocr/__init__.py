"""
OCR模块 - 支持 graceful fallback
如果PaddleOCR无法加载，将提供模拟版本
"""
import warnings

_ocr_available = False
_ocr_error_msg = ""

try:
    from .ocr_processor import OCRProcessor
    _ocr_available = True
except (ImportError, AttributeError, Exception) as e:
    _ocr_error_msg = str(e)
    warnings.warn(f"PaddleOCR加载失败: {e}，OCR功能将不可用")

    class OCRProcessor:
        """模拟OCR处理器（当PaddleOCR不可用时）"""

        def __init__(self, use_gpu=False, lang='ch'):
            self.use_gpu = use_gpu
            self.lang = lang
            self._available = False
            self._error = _ocr_error_msg

        def process_file(self, file_path, lang=None):
            return {
                'success': False,
                'error': f'OCR功能暂不可用（依赖库加载失败）。请检查 numpy 版本兼容性。',
                'text': '',
                'avg_confidence': 0.0
            }

        def process_image(self, image_path, lang=None):
            return self.process_file(image_path, lang=lang)

        def process_pdf(self, pdf_path, dpi=300, lang=None):
            return self.process_file(pdf_path, lang=lang)

        def extract_questions_from_text(self, text):
            """从文本提取题目（中文试卷格式）"""
            import re
            questions = []
            lines = text.split('\n')
            current_question = []
            current_section = ''
            question_num = 0

            section_patterns = [
                r'^[一二三四五六七八九十]+[、．.]\s*',
                r'^第[一二三四五六七八九十]+[部分大题]',
            ]
            question_patterns = [
                r'^\d+[、．.]\s*',
                r'^（\d+）\s*',
                r'^\(\d+\)\s*',
                r'^第\d+题\s*',
                r'^Question\s+\d+',
            ]
            option_patterns = [
                r'^[A-D][、．.\s]',
                r'^[①②③④⑤⑥]',
            ]

            section_re = re.compile('|'.join(section_patterns))
            question_re = re.compile('|'.join(question_patterns))
            option_re = re.compile('|'.join(option_patterns))

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if section_re.match(stripped):
                    if current_question:
                        question_num += 1
                        questions.append({
                            'content': '\n'.join(current_question),
                            'question_number': question_num,
                            'section_title': current_section
                        })
                        current_question = []
                    current_section = stripped
                    continue
                is_new_question = question_re.match(stripped) and not option_re.match(stripped)
                if is_new_question and current_question:
                    question_num += 1
                    questions.append({
                        'content': '\n'.join(current_question),
                        'question_number': question_num,
                        'section_title': current_section
                    })
                    current_question = [stripped]
                else:
                    current_question.append(stripped)
            if current_question:
                question_num += 1
                questions.append({
                    'content': '\n'.join(current_question),
                    'question_number': question_num,
                    'section_title': current_section
                })
            return questions


__all__ = ['OCRProcessor', '_ocr_available', '_ocr_error_msg']
