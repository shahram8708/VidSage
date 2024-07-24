from flask import Flask, render_template, request, jsonify
import os
import time
import google.generativeai as genai
import logging
import markdown

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

genai.configure(api_key=os.environ.get('API_KEY'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = os.path.join('uploads', file.filename)
    file.save(filename)

    try:
        file_data, video_file = upload_and_process_video(filename)
        custom_input = request.form.get('customInput', '')
        response = generate_content(file_data, custom_input)
        delete_file(file_data)

        markdown_content = response.text
        html_content = markdown.markdown(markdown_content)
        
        return jsonify({'summary': html_content})
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({'error': 'Failed to generate response. Please try again.'}), 500

def upload_and_process_video(video_file_name):
    print(f"Uploading file...")
    video_file = genai.upload_file(path=video_file_name)
    print(f"Completed upload: {video_file.uri}")

    while video_file.state.name == "PROCESSING":
        print('.', end='', flush=True)
        time.sleep(10) 
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(f"File processing failed: {video_file.state.name}")

    file = genai.get_file(name=video_file.name)
    print(f"Retrieved file '{file.display_name}' as: {video_file.uri}")

    return file, video_file

def generate_content(file, prompt):
    print("Making LLM inference request...")
    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

    response = model.generate_content([file, prompt], request_options={"timeout": 600})
    print(response.text)
    return response

def delete_file(file):
    print(f'Deleting file {file.uri}')
    genai.delete_file(file.name)
    print(f'Deleted file {file.uri}')

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)
