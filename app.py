"""
题库系统主应用
"""
import os
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json

from backend.database import DatabaseManager
from backend.ocr import OCRProcessor
from backend.api import QuestionManager, TagManager, ExamGenerator
from backend.export import WordExporter

# 创建Flask应用
app = Flask(__name__,
            template_folder='frontend/templates',
            static_folder='frontend/static')
CORS(app)

# 配置
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'frontend/static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化组件
db_manager = DatabaseManager('question_bank.db')
db_manager.init_db()

ocr_processor = OCRProcessor(use_gpu=False)
question_manager = QuestionManager(db_manager)
tag_manager = TagManager(db_manager)
exam_generator = ExamGenerator(db_manager)
word_exporter = WordExporter()

# 允许的文件类型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp'}


def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========== 路由定义 ==========

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/upload', methods=['GET'])
def upload_page():
    """上传页面"""
    return render_template('upload.html')


@app.route('/questions', methods=['GET'])
def questions_page():
    """题目管理页面"""
    return render_template('questions.html')


@app.route('/exam', methods=['GET'])
def exam_page():
    """组卷页面"""
    return render_template('exam.html')


# ========== API接口 ==========

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件并进行OCR识别"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件格式'}), 400

    try:
        # 保存文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # OCR识别
        result = ocr_processor.process_file(filepath)

        if result['success']:
            # 尝试提取题目
            text = result.get('text', '')
            questions = ocr_processor.extract_questions_from_text(text)

            return jsonify({
                'success': True,
                'text': text,
                'questions': questions,
                'filename': filename
            })
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions', methods=['GET'])
def get_questions():
    """获取题目列表"""
    try:
        # 获取查询参数
        tag_names = request.args.getlist('tags')
        question_type = request.args.get('type')
        difficulty = request.args.get('difficulty')
        keyword = request.args.get('keyword')

        if any([tag_names, question_type, difficulty, keyword]):
            questions = question_manager.search_questions(
                tag_names=tag_names if tag_names else None,
                question_type=question_type,
                difficulty=difficulty,
                keyword=keyword
            )
        else:
            questions = question_manager.get_all_questions(limit=100)

        return jsonify({'success': True, 'questions': questions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions/<int:question_id>', methods=['GET'])
def get_question(question_id):
    """获取单个题目详情"""
    try:
        question = question_manager.get_question(question_id)
        if question:
            return jsonify({'success': True, 'question': question})
        else:
            return jsonify({'success': False, 'error': '题目不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions', methods=['POST'])
def create_question():
    """创建题目"""
    try:
        data = request.json
        question_id = question_manager.create_question(
            content=data.get('content'),
            question_type=data.get('question_type'),
            difficulty=data.get('difficulty'),
            answer=data.get('answer'),
            analysis=data.get('analysis'),
            source=data.get('source'),
            tags=data.get('tags', [])
        )
        return jsonify({'success': True, 'question_id': question_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """更新题目"""
    try:
        data = request.json
        success = question_manager.update_question(question_id, **data)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """删除题目"""
    try:
        success = question_manager.delete_question(question_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tags', methods=['GET'])
def get_tags():
    """获取标签列表"""
    try:
        tag_type = request.args.get('type')
        tags = tag_manager.get_all_tags(tag_type)
        return jsonify({'success': True, 'tags': tags})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tags', methods=['POST'])
def create_tag():
    """创建标签"""
    try:
        data = request.json
        tag_id = tag_manager.create_tag(
            name=data.get('name'),
            tag_type=data.get('type', 'knowledge_point'),
            description=data.get('description')
        )
        return jsonify({'success': True, 'tag_id': tag_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/exam/papers', methods=['GET'])
def get_exam_papers():
    """获取试卷列表"""
    try:
        papers = exam_generator.get_all_exam_papers()
        return jsonify({'success': True, 'papers': papers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/exam/papers/<int:paper_id>', methods=['GET'])
def get_exam_paper(paper_id):
    """获取试卷详情"""
    try:
        paper = exam_generator.get_exam_paper(paper_id)
        if paper:
            return jsonify({'success': True, 'paper': paper})
        else:
            return jsonify({'success': False, 'error': '试卷不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/exam/generate', methods=['POST'])
def generate_exam():
    """生成试卷"""
    try:
        data = request.json
        method = data.get('method', 'selection')

        if method == 'selection':
            # 根据选定题目生成
            paper_id = exam_generator.generate_paper_by_selection(
                name=data.get('name'),
                question_ids=data.get('question_ids'),
                scores=data.get('scores'),
                paper_size=data.get('paper_size', 'A4'),
                description=data.get('description')
            )
        else:
            # 根据条件自动生成
            paper_id = exam_generator.generate_paper_by_criteria(
                name=data.get('name'),
                tag_names=data.get('tags'),
                question_type=data.get('question_type'),
                difficulty=data.get('difficulty'),
                count=data.get('count', 10),
                paper_size=data.get('paper_size', 'A4'),
                total_score=data.get('total_score', 100.0)
            )

        return jsonify({'success': True, 'paper_id': paper_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/exam/export/<int:paper_id>', methods=['GET'])
def export_exam(paper_id):
    """导出试卷为Word文档"""
    try:
        # 获取试卷数据
        paper = exam_generator.get_exam_paper(paper_id)
        if not paper:
            return jsonify({'success': False, 'error': '试卷不存在'}), 404

        # 获取参数
        show_answers = request.args.get('answers', 'false').lower() == 'true'
        show_analysis = request.args.get('analysis', 'false').lower() == 'true'

        # 生成文档
        output_filename = f"exam_{paper_id}.docx"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        word_exporter.create_exam_document(
            exam_data=paper,
            output_path=output_path,
            show_answers=show_answers,
            show_analysis=show_analysis
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{paper['name']}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/questions/export', methods=['POST'])
def export_questions():
    """导出题库为Word文档"""
    try:
        data = request.json
        question_ids = data.get('question_ids', [])

        # 获取题目数据
        session = db_manager.get_session()
        from backend.database import Question
        questions = session.query(Question).filter(Question.id.in_(question_ids)).all()

        questions_data = [{
            'content': q.content,
            'question_type': q.question_type,
            'difficulty': q.difficulty,
            'answer': q.answer,
            'tags': [tag.name for tag in q.tags]
        } for q in questions]

        session.close()

        # 生成文档
        output_filename = "question_bank.docx"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        word_exporter.export_question_bank(
            questions=questions_data,
            output_path=output_path,
            title=data.get('title', '题库')
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
