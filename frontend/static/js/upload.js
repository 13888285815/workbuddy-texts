// 上传页面逻辑

let extractedQuestions = [];
let currentFilename = '';

// 上传区域
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');

uploadArea.addEventListener('click', () => fileInput.click());

// 拖拽上传
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#2980b9';
    uploadArea.style.backgroundColor = '#ecf0f1';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '#3498db';
    uploadArea.style.backgroundColor = 'white';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#3498db';
    uploadArea.style.backgroundColor = 'white';

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

// 处理文件上传
async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    document.getElementById('processingStatus').style.display = 'block';
    document.getElementById('resultSection').style.display = 'none';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            currentFilename = result.filename;
            extractedQuestions = result.questions || [];

            document.getElementById('extractedText').value = result.text;
            displayExtractedQuestions(extractedQuestions);

            document.getElementById('processingStatus').style.display = 'none';
            document.getElementById('resultSection').style.display = 'block';

            showMessage('文件识别成功！', 'success');
        } else {
            throw new Error(result.error || '识别失败');
        }
    } catch (error) {
        document.getElementById('processingStatus').style.display = 'none';
        showMessage('文件识别失败: ' + error.message, 'error');
    }
}

// 显示提取的题目
function displayExtractedQuestions(questions) {
    const list = document.getElementById('questionsList');
    list.innerHTML = '';

    if (questions.length === 0) {
        list.innerHTML = '<p>未能自动提取题目，请在原始文本中手动复制题目内容</p>';
        return;
    }

    questions.forEach((question, index) => {
        const div = document.createElement('div');
        div.className = 'question-item';
        div.innerHTML = `
            <strong>题目 ${index + 1}:</strong>
            <p>${question}</p>
            <button class="btn btn-primary btn-sm" onclick="saveQuestion(${index})">保存此题</button>
        `;
        list.appendChild(div);
    });
}

// 标签页切换
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;

        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        btn.classList.add('active');
        document.getElementById(tab + 'Tab').classList.add('active');
    });
});

// 保存单个题目
window.saveQuestion = function(index) {
    const question = extractedQuestions[index];
    document.getElementById('extractedText').value = question;
    showModal('saveModal');
}

// 保存所有题目
document.getElementById('saveQuestionsBtn').addEventListener('click', () => {
    const text = document.getElementById('extractedText').value.trim();
    if (!text) {
        showMessage('没有可保存的内容', 'error');
        return;
    }
    showModal('saveModal');
});

// 确认保存
document.getElementById('confirmSaveBtn').addEventListener('click', async () => {
    const content = document.getElementById('extractedText').value.trim();
    const questionType = document.getElementById('questionType').value;
    const difficulty = document.getElementById('difficulty').value;
    const tags = document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t);
    const answer = document.getElementById('answer').value.trim();

    if (!content) {
        showMessage('题目内容不能为空', 'error');
        return;
    }

    try {
        const result = await apiRequest('/questions', {
            method: 'POST',
            body: JSON.stringify({
                content,
                question_type: questionType,
                difficulty,
                tags,
                answer,
                source: currentFilename
            })
        });

        if (result.success) {
            showMessage('题目保存成功！', 'success');
            hideModal('saveModal');

            // 清空表单
            document.getElementById('tags').value = '';
            document.getElementById('answer').value = '';
        } else {
            throw new Error(result.error || '保存失败');
        }
    } catch (error) {
        showMessage('保存失败: ' + error.message, 'error');
    }
});

// 取消保存
document.getElementById('cancelSaveBtn').addEventListener('click', () => {
    hideModal('saveModal');
});

// 清空并重新上传
document.getElementById('clearBtn').addEventListener('click', () => {
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('extractedText').value = '';
    extractedQuestions = [];
    currentFilename = '';
    fileInput.value = '';
});
