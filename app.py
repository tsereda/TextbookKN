import os
import sqlite3
import logging
import numpy as np
from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer
import re

# Set matplotlib backend to avoid Tkinter issues
import matplotlib
matplotlib.use('Agg')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# SQLite database setup
DB_PATH = 'markdown_segments.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS segments
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             text TEXT NOT NULL,
             embedding BLOB NOT NULL)
        ''')
        conn.commit()

def add_to_db(segment, embedding):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO segments (text, embedding) VALUES (?, ?)',
                       (segment, embedding.tobytes()))
        conn.commit()

def segment_markdown(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Extract segments between ### markers
    segments = re.split(r'###\s*', content)
    # Remove empty segments and strip whitespace
    segments = [seg.strip() for seg in segments if seg.strip()]
    
    return segments

def get_segments_and_embeddings():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, text, embedding FROM segments')
        rows = cursor.fetchall()
    
    segments = []
    embeddings = []
    for row in rows:
        segments.append({'id': row[0], 'text': row[1]})
        embeddings.append(np.frombuffer(row[2], dtype=np.float32))
    
    return segments, np.array(embeddings)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def numpy_to_python(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_markdown():
    file_path = 'chapter1/output.md'
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'Markdown file not found'}), 404
    
    try:
        segments = segment_markdown(file_path)
        for segment in segments:
            embedding = model.encode(segment)
            add_to_db(segment, embedding)
        
        return jsonify({'message': f'Processed {len(segments)} segments', 'segments': segments})
    except Exception as e:
        logger.error(f"Error processing markdown: {e}")
        return jsonify({'error': 'Error processing markdown'}), 500

@app.route('/network_data')
def network_data():
    segments, embeddings = get_segments_and_embeddings()
    
    nodes = []
    edges = []
    
    for i, seg in enumerate(segments):
        similarities = []
        for j, other_seg in enumerate(segments):
            if i != j:
                similarity = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append((j, similarity))
        
        # Sort similarities and get top 5 for hover info
        top_similarities = sorted(similarities, key=lambda x: x[1], reverse=True)[:5]
        
        # Get the two most similar segments for edges
        two_most_similar = sorted(similarities, key=lambda x: x[1], reverse=True)[:2]
        
        nodes.append({
            'id': seg['id'],
            'label': seg['text'][:50],
            'title': seg['text'],  # Full text for hover
            'top_similarities': [
                {
                    'id': segments[j]['id'], 
                    'similarity': numpy_to_python(sim),
                    'is_connected': idx < 2  # True for the two most similar
                }
                for idx, (j, sim) in enumerate(top_similarities)
            ]
        })
        
        # Add edges for the two most similar segments
        for j, sim in two_most_similar:
            edges.append({
                'from': seg['id'],
                'to': segments[j]['id'],
                'value': numpy_to_python(sim)
            })
    
    return jsonify({'nodes': nodes, 'edges': edges})

@app.route('/clear_database', methods=['POST'])
def clear_database():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM segments')
            conn.commit()
        return jsonify({'message': 'Database cleared successfully'}), 200
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return jsonify({'error': 'Error clearing database'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)