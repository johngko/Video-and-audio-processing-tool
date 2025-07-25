from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import subprocess
import time
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = '/app/uploads'
OUTPUT_FOLDER = '/app/output'
HISTORY_FILE = '/app/history.json'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'mp3', 'wav', 'ogg', 'flac', 'm4a'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 初始化历史记录
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump([], f)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_history():
    with open(HISTORY_FILE, 'r') as f:
        return json.load(f)

def add_history(task):
    history = get_history()
    history.append(task)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '无文件上传'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if file and allowed_file(file.filename):
        # 生成唯一文件名
        task_id = str(uuid.uuid4())
        filename = f"{task_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 记录任务状态
        task = {
            'task_id': task_id,
            'input_file': filename,
            'output_file': None,
            'status': 'uploaded',
            'type': 'video' if filename.rsplit('.', 1)[1].lower() in {'mp4', 'avi', 'mov', 'mkv', 'webm'} else 'audio',
            'process_type': None,
            'created_at': int(time.time())
        }
        
        add_history(task)
        
        return jsonify({'task_id': task_id})
    
    return jsonify({'error': '不支持的文件格式'}), 400

@app.route('/process', methods=['POST'])
def process_file():
    data = request.json
    task_id = data.get('task_id')
    process_type = data.get('process_type')
    
    if not task_id or not process_type:
        return jsonify({'error': '缺少参数'}), 400
    
    # 查找任务
    history = get_history()
    task_index = next((i for i, t in enumerate(history) if t['task_id'] == task_id), None)
    
    if task_index is None:
        return jsonify({'error': '任务不存在'}), 404
    
    task = history[task_index]
    input_path = os.path.join(UPLOAD_FOLDER, task['input_file'])
    
    # 更新任务状态
    history[task_index]['status'] = 'processing'
    history[task_index]['process_type'] = process_type
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)
    
    try:
        # 根据处理类型执行不同操作
        if process_type == 'convert':
            output_format = data.get('output_format', 'mp4')
            output_filename = f"{task_id}_output.{output_format}"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            # 执行格式转换
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg错误: {result.stderr}")
            
            history[task_index]['output_file'] = output_filename
        
        elif process_type == 'compress':
            quality = data.get('quality', 'medium')
            ext = task['input_file'].rsplit('.', 1)[1].lower()
            output_filename = f"{task_id}_compressed.{ext}"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            # 根据质量设置压缩参数
            crf = 28 if quality == 'medium' else 32 if quality == 'low' else 23
            
            # 执行压缩
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-crf', str(crf), '-preset', 'medium',
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg错误: {result.stderr}")
            
            history[task_index]['output_file'] = output_filename
        
        elif process_type == 'trim':
            start_time = data.get('start_time', '00:00:00')
            end_time = data.get('end_time', '')
            ext = task['input_file'].rsplit('.', 1)[1].lower()
            output_filename = f"{task_id}_trimmed.{ext}"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            # 执行剪辑
            cmd = ['ffmpeg', '-y', '-i', input_path]
            
            if start_time:
                cmd.extend(['-ss', start_time])
            if end_time:
                cmd.extend(['-to', end_time])
            
            cmd.append(output_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg错误: {result.stderr}")
            
            history[task_index]['output_file'] = output_filename
        
        else:
            raise Exception("不支持的处理类型")
        
        # 更新任务状态为完成
        history[task_index]['status'] = 'completed'
        history[task_index]['completed_at'] = int(time.time())
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
        
        return jsonify({'status': 'completed'})
    
    except Exception as e:
        # 更新任务状态为错误
        history[task_index]['status'] = 'error'
        history[task_index]['error_message'] = str(e)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>')
def get_status(task_id):
    history = get_history()
    task = next((t for t in history if t['task_id'] == task_id), None)
    
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify({
        'status': task['status'],
        'output_file': task.get('output_file'),
        'error': task.get('error_message')
    })

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

@app.route('/history')
def get_history_api():
    return jsonify(get_history())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)