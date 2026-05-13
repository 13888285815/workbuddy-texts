"""
OCR文本识别处理模块
支持图片和PDF文件的文本提取
中文优先识别，兼容中英文混合试卷
"""
import os
import re
from typing import List, Dict, Any
from paddleocr import PaddleOCR
from PIL import Image
import pdfplumber
from pdf2image import convert_from_path
import cv2
import numpy as np


def _detect_chinese_ratio(text: str) -> float:
    """检测文本中中文字符的比例"""
    if not text.strip():
        return 0.0
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(re.sub(r'\s', '', text))
    return chinese_chars / total_chars if total_chars > 0 else 0.0


class OCRProcessor:
    """OCR处理器 — 中文优先"""

    def __init__(self, use_gpu=False, lang='ch'):
        """
        初始化OCR处理器
        :param use_gpu: 是否使用GPU加速
        :param lang: 语言模式 'ch'=中文(默认，也支持英文), 'en'=纯英文
        """
        # 中文模型 — PaddleOCR中文模型本身支持中英文混合
        self.ocr_ch = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            use_gpu=use_gpu,
            show_log=False
        )

        # 英文模型 — 仅在纯英文场景使用
        self.ocr_en = None  # 延迟加载，避免不必要的内存占用
        self._en_initialized = False

        self.lang = lang
        # 默认使用中文模型
        self.ocr = self.ocr_ch

    def _ensure_en_ocr(self):
        """延迟加载英文OCR模型"""
        if not self._en_initialized:
            self.ocr_en = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                use_gpu=False,
                show_log=False
            )
            self._en_initialized = True

    def process_image(self, image_path: str, lang: str = None) -> Dict[str, Any]:
        """
        处理图片文件，提取文本
        :param image_path: 图片路径
        :param lang: 强制指定语言 'ch'/'en'，None则自动检测
        :return: 识别结果字典
        """
        try:
            # 第一步：用中文模型识别（支持中英文混合）
            result_ch = self.ocr_ch.ocr(image_path, cls=True)

            text_lines_ch = []
            boxes_ch = []
            confidences_ch = []

            if result_ch and result_ch[0]:
                for line in result_ch[0]:
                    box = line[0]
                    text = line[1][0]
                    confidence = line[1][1]
                    text_lines_ch.append(text)
                    boxes_ch.append(box)
                    confidences_ch.append(confidence)

            full_text_ch = '\n'.join(text_lines_ch)
            avg_conf_ch = sum(confidences_ch) / len(confidences_ch) if confidences_ch else 0

            # 如果强制指定英文，或自动检测发现几乎没有中文
            use_en = False
            if lang == 'en':
                use_en = True
            elif lang is None:
                chinese_ratio = _detect_chinese_ratio(full_text_ch)
                # 中文比例极低且置信度不高时，尝试英文模型
                if chinese_ratio < 0.05 and avg_conf_ch < 0.80:
                    use_en = True

            if use_en:
                self._ensure_en_ocr()
                result_en = self.ocr_en.ocr(image_path, cls=True)

                text_lines_en = []
                boxes_en = []
                confidences_en = []

                if result_en and result_en[0]:
                    for line in result_en[0]:
                        text_lines_en.append(line[1][0])
                        boxes_en.append(line[0])
                        confidences_en.append(line[1][1])

                full_text_en = '\n'.join(text_lines_en)
                avg_conf_en = sum(confidences_en) / len(confidences_en) if confidences_en else 0

                # 选择置信度更高的结果
                if avg_conf_en > avg_conf_ch:
                    return {
                        'success': True,
                        'text': full_text_en,
                        'text_lines': text_lines_en,
                        'boxes': boxes_en,
                        'confidences': confidences_en,
                        'total_lines': len(text_lines_en),
                        'avg_confidence': avg_conf_en,
                        'detected_lang': 'en'
                    }

            return {
                'success': True,
                'text': full_text_ch,
                'text_lines': text_lines_ch,
                'boxes': boxes_ch,
                'confidences': confidences_ch,
                'total_lines': len(text_lines_ch),
                'avg_confidence': avg_conf_ch,
                'detected_lang': 'ch'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }

    def process_pdf(self, pdf_path: str, dpi=300, lang: str = None) -> Dict[str, Any]:
        """
        处理PDF文件，提取文本
        :param pdf_path: PDF文件路径
        :param dpi: 转换图片的DPI
        :param lang: 强制指定语言
        :return: 识别结果字典
        """
        try:
            all_text = []
            all_pages_data = []

            # 方法1：先尝试直接提取PDF中的文本（更快）
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        all_text.append(text)
                        all_pages_data.append({
                            'page': page_num,
                            'text': text,
                            'method': 'direct_extraction'
                        })

            # 方法2：如果直接提取失败或文本太少，使用OCR
            if not all_text or sum(len(t) for t in all_text) < 50:
                all_text = []
                all_pages_data = []

                images = convert_from_path(pdf_path, dpi=dpi)

                for page_num, image in enumerate(images, 1):
                    img_array = np.array(image)

                    # 使用中文模型OCR（默认支持中英文混合）
                    result = self.ocr_ch.ocr(img_array, cls=True)

                    page_text_lines = []
                    if result and result[0]:
                        for line in result[0]:
                            text = line[1][0]
                            page_text_lines.append(text)

                    page_text = '\n'.join(page_text_lines)
                    all_text.append(page_text)

                    all_pages_data.append({
                        'page': page_num,
                        'text': page_text,
                        'lines': page_text_lines,
                        'method': 'ocr'
                    })

            full_text = '\n\n'.join(all_text)

            return {
                'success': True,
                'text': full_text,
                'pages': all_pages_data,
                'total_pages': len(all_pages_data)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }

    def process_file(self, file_path: str, lang: str = None) -> Dict[str, Any]:
        """
        自动识别文件类型并处理
        :param file_path: 文件路径
        :param lang: 强制指定语言 'ch'/'en'
        :return: 识别结果
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': '文件不存在'
            }

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            return self.process_pdf(file_path, lang=lang)
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
            return self.process_image(file_path, lang=lang)
        else:
            return {
                'success': False,
                'error': f'不支持的文件格式: {ext}'
            }

    def extract_questions_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取题目 — 支持中国各类试卷格式
        :param text: 文本内容
        :return: 题目列表，每项包含 content, question_number, section_title
        """
        questions = []
        lines = text.split('\n')

        current_question = []
        current_section = ''
        question_num = 0

        # ===== 大题标题模式 =====
        section_patterns = [
            r'^[一二三四五六七八九十]+[、．.]\s*',           # 一、选择题  二．填空题
            r'^第[一二三四五六七八九十]+[部分大题]',          # 第一部分  第二大题
            r'^[（(]\s*[一二三四五六七八九十]+\s*[)）]\s*',  # （一）选择题
            r'^Part\s+[IVX]+\s*',                            # Part I / Part IV
            r'^Section\s+[A-Z]\s*',                          # Section A
        ]

        # ===== 主要题号模式（独立成题） =====
        main_question_patterns = [
            r'^\d+[、．.]\s*',              # 1、  1．  1.
            r'^第\d+题\s*',                 # 第1题
            r'^\d+\s*[．.]\s{1,}',          # 1．  1. (带空格，排除1.5这类数字)
            r'^Question\s+\d+',             # Question 1
            r'^Q\d+[\.\:]',                 # Q1. / Q1:
        ]

        # ===== 子题号模式（解答题的小问，合并到主题目） =====
        sub_question_patterns = [
            r'^（\d+）\s*',                 # （1）（2）
            r'^\(\d+\)\s*',                 # (1)(2)
        ]

        # ===== 选项模式 =====
        option_patterns = [
            r'^[A-D][、．.\s]',             # A. B. C. D. / A、B、
            r'^[①②③④⑤⑥]',                 # ①②③④
            r'^\([A-D]\)\s*',               # (A) (B) (C) (D)
        ]

        # ===== 试卷标题/元信息模式（跳过不作为题目） =====
        skip_patterns = [
            r'.*模拟考试$',                  # xx模拟考试
            r'.*期末考试$',                  # xx期末考试
            r'^时间[：:]',                   # 时间：120分钟
            r'^满分[：:]',                   # 满分：150分
            r'^注意事项',                    # 注意事项
            r'^第\s*\d+\s*页',              # 第1页
            r'^姓名',                       # 姓名
            r'^班级',                       # 班级
            r'^考号',                       # 考号
            r'^学校',                       # 学校
        ]

        section_re = re.compile('|'.join(section_patterns))
        main_question_re = re.compile('|'.join(main_question_patterns))
        sub_question_re = re.compile('|'.join(sub_question_patterns))
        option_re = re.compile('|'.join(option_patterns))
        skip_re = re.compile('|'.join(skip_patterns))

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 跳过试卷标题和元信息
            if skip_re.match(stripped):
                continue

            # 检查是否是大题标题
            if section_re.match(stripped):
                # 保存当前小题
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

            # 检查是否是子题号（解答题的小问，合并到当前题）
            is_sub_question = bool(sub_question_re.match(stripped))

            # 检查是否是主要题目编号（但不是选项行）
            is_main_question = bool(main_question_re.match(stripped)) and not option_re.match(stripped)

            if is_main_question and current_question:
                # 保存上一题
                question_num += 1
                questions.append({
                    'content': '\n'.join(current_question),
                    'question_number': question_num,
                    'section_title': current_section
                })
                current_question = [stripped]
            else:
                # 子题号和选项都追加到当前题目
                current_question.append(stripped)

        # 保存最后一题
        if current_question:
            question_num += 1
            questions.append({
                'content': '\n'.join(current_question),
                'question_number': question_num,
                'section_title': current_section
            })

        return questions
