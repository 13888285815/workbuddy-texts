"""
中国学校试卷题型和模板配置
支持数学、语文、英语、物理、化学、生物、政治、历史、地理等学科
"""
from typing import Dict, Any, List, Optional

# ===== 各学科题型定义 =====

MATH_QUESTION_TYPES = {
    '选择题': {
        'code': 'math_choice',
        'subject': '数学',
        'description': '四选一或五选一的选择题',
        'typical_score': 5.0,
        'has_options': True,
        'has_passage': False,
        'sub_types': ['集合', '函数', '三角函数', '数列', '概率统计', '向量', '不等式', '立体几何', '解析几何', '导数']
    },
    '填空题': {
        'code': 'math_fill',
        'subject': '数学',
        'description': '填写答案或表达式',
        'typical_score': 5.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['计算填空', '概念填空', '推理填空']
    },
    '解答题': {
        'code': 'math_solution',
        'subject': '数学',
        'description': '需要写出完整解题过程',
        'typical_score': 12.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['函数与导数', '数列', '解析几何', '立体几何', '概率统计', '不等式']
    },
    '证明题': {
        'code': 'math_proof',
        'subject': '数学',
        'description': '要求严格证明的题目',
        'typical_score': 12.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['几何证明', '代数证明', '不等式证明']
    },
}

CHINESE_QUESTION_TYPES = {
    '选择题': {
        'code': 'chinese_choice',
        'subject': '语文',
        'description': '字词音义、成语运用、病句辨析等',
        'typical_score': 3.0,
        'has_options': True,
        'has_passage': False,
        'sub_types': ['字音', '字形', '词语运用', '成语', '病句辨析', '标点', '修辞', '文学常识', '文言文断句']
    },
    '文言文阅读': {
        'code': 'chinese_classical',
        'subject': '语文',
        'description': '文言文阅读理解与翻译',
        'typical_score': 19.0,
        'has_options': True,
        'has_passage': True,
        'sub_types': ['实词虚词', '句式', '翻译', '内容理解', '断句']
    },
    '古诗词鉴赏': {
        'code': 'chinese_poetry',
        'subject': '语文',
        'description': '古诗词理解和赏析',
        'typical_score': 9.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['意象分析', '手法鉴赏', '情感理解', '名句默写']
    },
    '现代文阅读': {
        'code': 'chinese_modern_reading',
        'subject': '语文',
        'description': '现代文阅读理解',
        'typical_score': 17.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['论述类', '实用类', '文学类', '信息筛选', '内容概括', '手法分析', '探究题']
    },
    '语言文字运用': {
        'code': 'chinese_language_use',
        'subject': '语文',
        'description': '语言表达和运用题',
        'typical_score': 5.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['仿写', '压缩语段', '扩展语句', '图文转换', '得体', '连贯']
    },
    '作文': {
        'code': 'chinese_writing',
        'subject': '语文',
        'description': '根据材料或题目写作文',
        'typical_score': 60.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['材料作文', '命题作文', '话题作文', '任务驱动型']
    },
    '名篇名句默写': {
        'code': 'chinese_dictation',
        'subject': '语文',
        'description': '古诗文默写',
        'typical_score': 6.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['理解性默写', '情景默写']
    },
}

ENGLISH_QUESTION_TYPES = {
    '选择题': {
        'code': 'english_choice',
        'subject': '英语',
        'description': '语法、词汇、情景对话等单选题',
        'typical_score': 1.0,
        'has_options': True,
        'has_passage': False,
        'sub_types': ['语法', '词汇', '情景交际', '固定搭配']
    },
    '完形填空': {
        'code': 'english_cloze',
        'subject': '英语',
        'description': '在短文中选词填空',
        'typical_score': 1.5,
        'has_options': True,
        'has_passage': True,
        'sub_types': ['记叙文', '说明文', '议论文']
    },
    '阅读理解': {
        'code': 'english_reading',
        'subject': '英语',
        'description': '阅读文章后回答问题',
        'typical_score': 2.0,
        'has_options': True,
        'has_passage': True,
        'sub_types': ['细节理解', '主旨大意', '推理判断', '词义猜测']
    },
    '语法填空': {
        'code': 'english_grammar_fill',
        'subject': '英语',
        'description': '根据语法规则填空',
        'typical_score': 1.5,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['有提示词', '无提示词']
    },
    '短文改错': {
        'code': 'english_error_correction',
        'subject': '英语',
        'description': '找出并改正短文中的错误',
        'typical_score': 1.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': []
    },
    '书面表达': {
        'code': 'english_writing',
        'subject': '英语',
        'description': '根据要求写英语短文',
        'typical_score': 25.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['书信', '邮件', '通知', '演讲稿', '记叙文', '议论文']
    },
}

PHYSICS_QUESTION_TYPES = {
    '选择题': {
        'code': 'physics_choice',
        'subject': '物理',
        'description': '物理概念和计算的选择题',
        'typical_score': 4.0,
        'has_options': True,
        'has_passage': False,
        'sub_types': ['力学', '电磁学', '热学', '光学', '原子物理', '多选', '单选']
    },
    '实验题': {
        'code': 'physics_experiment',
        'subject': '物理',
        'description': '实验原理、操作和数据处理',
        'typical_score': 8.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['力学实验', '电学实验', '光学实验']
    },
    '计算题': {
        'code': 'physics_calculation',
        'subject': '物理',
        'description': '需要完整计算过程的题目',
        'typical_score': 16.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['力学', '电磁学', '综合']
    },
}

CHEMISTRY_QUESTION_TYPES = {
    '选择题': {
        'code': 'chemistry_choice',
        'subject': '化学',
        'description': '化学概念和计算的选择题',
        'typical_score': 3.0,
        'has_options': True,
        'has_passage': False,
        'sub_types': ['基本概念', '元素化合物', '有机化学', '化学实验', '化学计算']
    },
    '实验题': {
        'code': 'chemistry_experiment',
        'subject': '化学',
        'description': '实验操作、现象描述和数据处理',
        'typical_score': 15.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['制备实验', '性质实验', '定量实验']
    },
    '推断题': {
        'code': 'chemistry_inference',
        'subject': '化学',
        'description': '根据条件推断物质或反应',
        'typical_score': 12.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['无机推断', '有机推断']
    },
    '计算题': {
        'code': 'chemistry_calculation',
        'subject': '化学',
        'description': '化学计算题',
        'typical_score': 10.0,
        'has_options': False,
        'has_passage': False,
        'sub_types': ['物质的量', '化学平衡', '电化学', '溶液']
    },
}

BIOLOGY_QUESTION_TYPES = {
    '选择题': {
        'code': 'biology_choice',
        'subject': '生物',
        'description': '生物学概念选择题',
        'typical_score': 2.0,
        'has_options': True,
        'has_passage': False,
        'sub_types': ['细胞', '遗传', '进化', '生态', '调节', '分子']
    },
    '非选择题': {
        'code': 'biology_non_choice',
        'subject': '生物',
        'description': '填空、实验设计等非选择题',
        'typical_score': 10.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['填空', '实验设计', '遗传推断', '曲线分析']
    },
}

# 文综/理综通用
SOCIAL_STUDIES_TYPES = {
    '选择题': {
        'code': 'social_choice',
        'subject': '文综',
        'description': '政治/历史/地理选择题',
        'typical_score': 4.0,
        'has_options': True,
        'has_passage': False,
        'sub_types': []
    },
    '材料分析题': {
        'code': 'social_material',
        'subject': '文综',
        'description': '根据材料回答问题',
        'typical_score': 12.0,
        'has_options': False,
        'has_passage': True,
        'sub_types': ['政治材料题', '历史材料题', '地理综合题']
    },
}

# ===== 合并所有题型 =====
ALL_QUESTION_TYPES = {}
ALL_QUESTION_TYPES.update(MATH_QUESTION_TYPES)
ALL_QUESTION_TYPES.update(CHINESE_QUESTION_TYPES)
ALL_QUESTION_TYPES.update(ENGLISH_QUESTION_TYPES)
ALL_QUESTION_TYPES.update(PHYSICS_QUESTION_TYPES)
ALL_QUESTION_TYPES.update(CHEMISTRY_QUESTION_TYPES)
ALL_QUESTION_TYPES.update(BIOLOGY_QUESTION_TYPES)
ALL_QUESTION_TYPES.update(SOCIAL_STUDIES_TYPES)

# 按学科分组
SUBJECT_TYPES = {
    '数学': list(MATH_QUESTION_TYPES.keys()),
    '语文': list(CHINESE_QUESTION_TYPES.keys()),
    '英语': list(ENGLISH_QUESTION_TYPES.keys()),
    '物理': list(PHYSICS_QUESTION_TYPES.keys()),
    '化学': list(CHEMISTRY_QUESTION_TYPES.keys()),
    '生物': list(BIOLOGY_QUESTION_TYPES.keys()),
    '政治': ['选择题', '材料分析题'],
    '历史': ['选择题', '材料分析题'],
    '地理': ['选择题', '综合题'],
}

# ===== 通用题型列表（用于AI解析时无法确定学科时的默认分类） =====
GENERIC_QUESTION_TYPES = [
    '选择题', '填空题', '判断题', '解答题', '计算题',
    '证明题', '实验题', '阅读理解', '作文', '简答题',
    '论述题', '材料分析题', '翻译', '改错题', '连线题',
    '推断题', '操作题', '应用题',
]


# ===== 预设试卷模板 =====

PRESET_TEMPLATES = [
    {
        'name': '高中数学模拟试卷',
        'description': '适用于高中数学考试，标准高考格式',
        'category': '数学',
        'total_score': 150.0,
        'paper_size': 'A3',
        'structure': {
            'header': {
                'title': '高中数学模拟考试',
                'subtitle': '时间：120分钟  满分：150分',
                'instructions': '注意事项：\n1. 本试卷分第I卷（选择题）和第II卷（非选择题）两部分。\n2. 答题前，请将姓名、考号填写在答题卡上。\n3. 所有答案必须填写在答题卡上。'
            },
            'sections': [
                {
                    'title': '一、选择题（本大题共12小题，每小题5分，共60分）',
                    'type': '选择题',
                    'count': 12,
                    'score_per_item': 5.0,
                    'total_score': 60.0,
                    'description': '在每小题给出的四个选项中，只有一项是符合题目要求的',
                },
                {
                    'title': '二、填空题（本大题共4小题，每小题5分，共20分）',
                    'type': '填空题',
                    'count': 4,
                    'score_per_item': 5.0,
                    'total_score': 20.0,
                },
                {
                    'title': '三、解答题（本大题共6小题，共70分）',
                    'type': '解答题',
                    'count': 6,
                    'score_per_item': 12.0,
                    'total_score': 70.0,
                    'description': '解答应写出文字说明、证明过程或演算步骤',
                },
            ]
        }
    },
    {
        'name': '高中语文模拟试卷',
        'description': '适用于高中语文考试，标准高考格式',
        'category': '语文',
        'total_score': 150.0,
        'paper_size': 'A3',
        'structure': {
            'header': {
                'title': '高中语文模拟考试',
                'subtitle': '时间：150分钟  满分：150分',
                'instructions': '注意事项：\n1. 本试卷共10页。答题前，考生务必将自己的姓名、考号填写在答题卡上。\n2. 作答时，将答案写在答题卡上。写在本试卷上无效。'
            },
            'sections': [
                {
                    'title': '一、现代文阅读（35分）',
                    'type': '现代文阅读',
                    'count': 3,
                    'score_per_item': 17.0,
                    'total_score': 35.0,
                },
                {
                    'title': '二、古诗文阅读（35分）',
                    'type': '文言文阅读',
                    'count': 3,
                    'score_per_item': 19.0,
                    'total_score': 35.0,
                },
                {
                    'title': '三、语言文字运用（20分）',
                    'type': '语言文字运用',
                    'count': 5,
                    'score_per_item': 4.0,
                    'total_score': 20.0,
                },
                {
                    'title': '四、写作（60分）',
                    'type': '作文',
                    'count': 1,
                    'score_per_item': 60.0,
                    'total_score': 60.0,
                    'description': '请根据要求写作文，不少于800字',
                },
            ]
        }
    },
    {
        'name': '初中数学期末试卷',
        'description': '适用于初中数学期末考试',
        'category': '数学',
        'total_score': 120.0,
        'paper_size': 'A3',
        'structure': {
            'header': {
                'title': '初中数学期末考试',
                'subtitle': '时间：120分钟  满分：120分',
            },
            'sections': [
                {
                    'title': '一、选择题（本大题共10小题，每小题3分，共30分）',
                    'type': '选择题',
                    'count': 10,
                    'score_per_item': 3.0,
                    'total_score': 30.0,
                },
                {
                    'title': '二、填空题（本大题共6小题，每小题3分，共18分）',
                    'type': '填空题',
                    'count': 6,
                    'score_per_item': 3.0,
                    'total_score': 18.0,
                },
                {
                    'title': '三、解答题（本大题共7小题，共72分）',
                    'type': '解答题',
                    'count': 7,
                    'score_per_item': 10.0,
                    'total_score': 72.0,
                    'description': '解答应写出文字说明、证明过程或演算步骤',
                },
            ]
        }
    },
    {
        'name': '初中英语期末试卷',
        'description': '适用于初中英语期末考试',
        'category': '英语',
        'total_score': 120.0,
        'paper_size': 'A3',
        'structure': {
            'header': {
                'title': '初中英语期末考试',
                'subtitle': '时间：120分钟  满分：120分',
            },
            'sections': [
                {
                    'title': '一、听力部分（共20分）',
                    'type': '选择题',
                    'count': 20,
                    'score_per_item': 1.0,
                    'total_score': 20.0,
                },
                {
                    'title': '二、单项选择（共15分）',
                    'type': '选择题',
                    'count': 15,
                    'score_per_item': 1.0,
                    'total_score': 15.0,
                },
                {
                    'title': '三、完形填空（共10分）',
                    'type': '完形填空',
                    'count': 10,
                    'score_per_item': 1.0,
                    'total_score': 10.0,
                },
                {
                    'title': '四、阅读理解（共30分）',
                    'type': '阅读理解',
                    'count': 15,
                    'score_per_item': 2.0,
                    'total_score': 30.0,
                },
                {
                    'title': '五、词汇运用（共10分）',
                    'type': '语法填空',
                    'count': 10,
                    'score_per_item': 1.0,
                    'total_score': 10.0,
                },
                {
                    'title': '六、书面表达（共15分）',
                    'type': '书面表达',
                    'count': 1,
                    'score_per_item': 15.0,
                    'total_score': 15.0,
                },
            ]
        }
    },
    {
        'name': '高中理综模拟试卷',
        'description': '适用于高中理科综合考试',
        'category': '理综',
        'total_score': 300.0,
        'paper_size': 'A3',
        'structure': {
            'header': {
                'title': '理科综合能力测试',
                'subtitle': '时间：150分钟  满分：300分',
            },
            'sections': [
                {
                    'title': '一、选择题（共21小题，每小题6分，共126分）',
                    'type': '选择题',
                    'count': 21,
                    'score_per_item': 6.0,
                    'total_score': 126.0,
                },
                {
                    'title': '二、非选择题（共11小题，共174分）',
                    'type': '实验题',
                    'count': 11,
                    'score_per_item': 15.0,
                    'total_score': 174.0,
                    'description': '包括实验题、计算题和推断题',
                },
            ]
        }
    },
]


def get_question_type_info(question_type: str) -> Dict[str, Any]:
    """获取题型信息"""
    return ALL_QUESTION_TYPES.get(question_type, {})


def get_all_question_types() -> List[str]:
    """获取所有支持的题型列表（去重）"""
    return list(dict.fromkeys(ALL_QUESTION_TYPES.keys()))


def get_question_types_by_subject(subject: str) -> List[str]:
    """根据学科获取题型列表"""
    return SUBJECT_TYPES.get(subject, [])


def get_template_by_name(name: str):
    """根据名称获取模板"""
    for template in PRESET_TEMPLATES:
        if template['name'] == name:
            return template
    return None


def get_all_templates():
    """获取所有预设模板"""
    return PRESET_TEMPLATES
