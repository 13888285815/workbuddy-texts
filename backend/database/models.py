"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Table, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

# 题目-标签关联表（多对多）
question_tag_association = Table(
    'question_tag_association',
    Base.metadata,
    Column('question_id', Integer, ForeignKey('questions.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

# 题库-题目关联表（多对多）
questionbank_question_association = Table(
    'questionbank_question_association',
    Base.metadata,
    Column('questionbank_id', Integer, ForeignKey('question_banks.id')),
    Column('question_id', Integer, ForeignKey('questions.id'))
)

# 试卷-题目关联表（多对多，带顺序）
class ExamPaperQuestion(Base):
    __tablename__ = 'exam_paper_questions'

    id = Column(Integer, primary_key=True)
    exam_paper_id = Column(Integer, ForeignKey('exam_papers.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    order_index = Column(Integer)  # 题目在试卷中的顺序
    score = Column(Float, default=0.0)  # 该题分数

    question = relationship("Question")


class Question(Base):
    """题目表"""
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)  # 题目内容
    question_type = Column(String(50))  # 题型：选择题、填空题、解答题等
    difficulty = Column(String(20))  # 难度：简单、中等、困难
    answer = Column(Text)  # 答案
    analysis = Column(Text)  # 解析
    source = Column(String(200))  # 来源（文件名等）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    tags = relationship("Tag", secondary=question_tag_association, back_populates="questions")
    question_banks = relationship("QuestionBank", secondary=questionbank_question_association, back_populates="questions")

    def __repr__(self):
        return f"<Question(id={self.id}, type={self.question_type})>"


class Tag(Base):
    """标签表"""
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)  # 标签名称
    tag_type = Column(String(50))  # 标签类型：knowledge_point（知识点）、category（类别）等
    description = Column(Text)  # 标签描述
    created_at = Column(DateTime, default=datetime.now)

    # 关联关系
    questions = relationship("Question", secondary=question_tag_association, back_populates="tags")

    def __repr__(self):
        return f"<Tag(name={self.name}, type={self.tag_type})>"


class QuestionBank(Base):
    """题库表"""
    __tablename__ = 'question_banks'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)  # 题库名称
    description = Column(Text)  # 题库描述
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    questions = relationship("Question", secondary=questionbank_question_association, back_populates="question_banks")

    def __repr__(self):
        return f"<QuestionBank(name={self.name})>"


class ExamPaper(Base):
    """试卷表"""
    __tablename__ = 'exam_papers'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)  # 试卷名称
    paper_size = Column(String(10), default='A4')  # 试卷尺寸：A4、A3
    total_score = Column(Float, default=100.0)  # 总分
    description = Column(Text)  # 试卷说明
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    paper_questions = relationship("ExamPaperQuestion", backref="exam_paper", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExamPaper(name={self.name}, size={self.paper_size})>"
