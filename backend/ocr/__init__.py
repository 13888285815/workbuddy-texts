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

        def __init__(self, use_gpu=False, lang='en'):
            self.use_gpu = use_gpu
            self.lang = lang
            self._available = False
            self._error = _ocr_error_msg

        def process_file(self, file_path):
            return {
                'success': False,
                'error': f'OCR功能暂不可用（依赖库加载失败）。请检查 numpy 版本兼容性。',
                'text': '',
                'avg_confidence': 0.0
            }

        def process_image(self, image_path, use_both=True):
            return self.process_file(image_path)

        def process_pdf(self, pdf_path, dpi=300):
            return self.process_file(pdf_path)

        def extract_questions_from_text(self, text):
            """从文本提取题目（不需要OCR）"""
            import re
            questions = []
            lines = text.split('\n')
            current_question = []
            question_patterns = [
                r'^\d+\.',
                r'^Question\s+\d+',
                r'^Q\d+',
                r'^\(\d+\)',
                r'^一、|^二、|^三、|^四、|^五、',
                r'^（\d+）',
            ]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                is_new_question = any(re.match(pattern, line) for pattern in question_patterns)
                if is_new_question and current_question:
                    questions.append('\n'.join(current_question))
                    current_question = [line]
                else:
                    current_question.append(line)
            if current_question:
                questions.append('\n'.join(current_question))
            return questions


__all__ = ['OCRProcessor', '_ocr_available', '_ocr_error_msg']
