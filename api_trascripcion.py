from flask import Flask, jsonify, request
from utils import limpiar_text, construir_uri
from flask_cors import CORS, cross_origin
from langchain_community.document_loaders import YoutubeLoader
from models import YoutubeTranscription, db
import os
from datetime import datetime
import openai
from openai_utils import call_chatgpt, system_content_create_html_from_transcription, system_content_anonymize_transcription,system_content_anonymize_titulo

openai.api_key=os.environ['OPENAI_KEY']

app = Flask(__name__)
CORS(app, support_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://{os.environ["DB_USER"]}:{os.environ["DB_PASSWORD"]}@localhost:5432/{os.environ["DB_NAME"]}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)

# Create the tables within the app context
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET'])
def home():
    return '''<h1>Transcripción de Videos de YouTube</h1>
<p>API para transcribir videos de YouTube a texto utilizando el ID del video.</p>'''

@app.route('/api/v1/transcribe', methods=['POST'])
def transcribe():
    # Obtener el ID del video de YouTube del cuerpo de la petición
    video_id = request.json.get('video_id', None)
    if not video_id:
        return jsonify({'error': 'falta el id_video'})
    
    existing_transcription = YoutubeTranscription.query.get(video_id)
    if existing_transcription:
        pass
        #return jsonify({'error': 'La transcripción ya existe'}), 409
    
    fecha_creacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    loader= YoutubeLoader(video_id, add_video_info= True, language= ['es'])
    documents = loader.load()
    
    text = ' '.join([doc.page_content for doc in documents])
    title = documents[0].metadata['title'] if 'title' in documents[0].metadata else 'Sin título'
    title_anonymized = call_chatgpt(title,system_content_anonymize_titulo)
    imagen = documents[0].metadata['thumbnail_url'] if 'thumbnail_url' in documents[0].metadata else None
    
    uri = construir_uri(title_anonymized)
    cleaned_text = limpiar_text(text)[0]
    text_anonymized = call_chatgpt(cleaned_text,system_content_anonymize_transcription,temperature=0.2)
    content_html = call_chatgpt(text_anonymized, system_content_create_html_from_transcription)
    transcription = YoutubeTranscription(
        id=video_id, titulo=title_anonymized, contenido_transcription=text_anonymized,
        imagen=imagen, uri=uri, fecha_inicio=fecha_creacion, contenido_html=content_html
    )
    db.session.add(transcription)
    db.session.commit()
    
    return jsonify({'title': title_anonymized,'transcription':text_anonymized, 'content_html': content_html})

@app.route("/api/v1/youtube_transcription", methods=['GET'])
def get_youtube_transcription():
    youtube_trascriptions = YoutubeTranscription.query.all()
    lista_vacia = [{'id': t.id, 'title': t.titulo, 'contenido_transcription': t.contenido_transcription} for t in youtube_trascriptions]
    return jsonify({'items': lista_vacia})


@app.route('/api/v1/delete_transcription', methods=['DELETE'])
def delete_transcription():
    # Obtener el ID del video de YouTube del cuerpo de la petición
    video_id = request.json.get('video_id', None)
    if not video_id:
        return jsonify({'error': 'falta el id_video'}), 400
# Verificar si la transcripción existe
    transcription = YoutubeTranscription.query.get(video_id)
    if not transcription:
        return jsonify({'error': 'La transcripción no existe'}), 404
    

    # Eliminar la transcripción
    db.session.delete(transcription)
    db.session.commit()

    return jsonify({'message': 'Transcripción eliminada exitosamente'}), 200
    


                                                                                                                                                                                                                                                                                                                   
                                                  
if __name__ == '__main__':
    app.run(debug=True)
    
    





