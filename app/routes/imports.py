import tempfile
import os
import shutil
import xml.etree.ElementTree as ET
from flask import request, jsonify, current_app
from flask_login import login_required
from app import db
from app.routes.auth import token_required
from app.utils import import_ruah, import_rpdc0250c, import_rcot0300, import_rfor0302
from app.routes.routes import bp


UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'xml'}


def allowed_file(filename):
    """Check if uploaded file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_xml(content):
    """Validate XML content structure."""
    try:
        ET.fromstring(content)
        return True
    except ET.ParseError:
        return False


# PHASE 4 ENDPOINTS

@bp.route('/upload_chunk', methods=['POST'])
@login_required
def upload_chunk():
    """Handle chunked file upload for large XML files."""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    chunk_index = int(request.form['chunkIndex'])
    file_id = request.form['fileId']

    try:
        chunk_dir = os.path.join(UPLOAD_FOLDER, file_id)
        os.makedirs(chunk_dir, exist_ok=True)

        chunk_path = os.path.join(chunk_dir, f'chunk_{chunk_index}')
        file.save(chunk_path)

        return jsonify({'message': 'Chunk uploaded successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/process_file', methods=['POST'])
@login_required
def process_file():
    """Process uploaded XML file chunks and import data."""
    file_id = request.json.get('fileId')
    if not file_id:
        return jsonify({'error': 'No file ID provided'}), 400

    chunk_dir = os.path.join(UPLOAD_FOLDER, file_id)
    if not os.path.exists(chunk_dir):
        return jsonify({'error': 'File chunks not found'}), 404

    final_file_path = os.path.join(UPLOAD_FOLDER, f'{file_id}_complete.xml')

    try:
        chunks = sorted(os.listdir(chunk_dir), key=lambda x: int(x.split('_')[1]))
        with open(final_file_path, 'wb') as outfile:
            for chunk_name in chunks:
                chunk_path = os.path.join(chunk_dir, chunk_name)
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
        
        assembled_size = os.path.getsize(final_file_path)
        
        with open(final_file_path, 'rb') as f:
            content = f.read()
        
        if not is_valid_xml(content):
            raise ValueError('Invalid XML file')

        # Determine document type
        if b'<RPDC0250_RUAH>' in content or b'<RPDC0250>' in content:
            doc_type = 'RPDC0250'
            handler = import_ruah
        elif b'<RPDC0250C>' in content:
            doc_type = 'RPDC0250C'
            handler = import_rpdc0250c
        elif b'<RCOT0300>' in content:
            doc_type = 'RCOT0300'
            handler = import_rcot0300
        elif b'<RFOR0302>' in content:
            doc_type = 'RFOR0302'
            handler = import_rfor0302
        else:
            raise ValueError('Arquivo XML invalido ou não suportado')

        result = handler(content)
        return result

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("process_file: failure | file_id=%s", file_id)
        return jsonify({'error': str(e)}), 500
    
    finally:
        shutil.rmtree(chunk_dir, ignore_errors=True)
        if os.path.exists(final_file_path):
            os.remove(final_file_path)


@bp.route('/import', methods=['POST'])
@token_required
def import_file_bulk(user):
    """
    Import and process XML files in bulk.
    Accepts multiple files under the 'files' form key.
    """
    uploaded_files = request.files.getlist('files')
    if 'file' in request.files:
        uploaded_files.extend(request.files.getlist('file'))

    if not uploaded_files or all(f.filename == '' for f in uploaded_files):
        return jsonify({'error': 'No files provided. Please upload XML files.'}), 400

    results = {
        'successful': [],
        'failed': [],
        'total_processed': 0
    }

    for file in uploaded_files:
        filename = file.filename
        if filename == '':
            continue

        results['total_processed'] += 1

        if not allowed_file(filename):
            results['failed'].append({'filename': filename, 'reason': 'Must be XML format'})
            continue

        try:
            content = file.read()
            if not content:
                results['failed'].append({'filename': filename, 'reason': 'File is empty'})
                continue

            if not is_valid_xml(content):
                results['failed'].append({'filename': filename, 'reason': 'Invalid XML structure'})
                continue

            if b'<RPDC0250_RUAH>' in content or b'<RPDC0250>' in content:
                handler = import_ruah
            elif b'<RPDC0250C>' in content:
                handler = import_rpdc0250c
            elif b'<RCOT0300>' in content:
                handler = import_rcot0300
            elif b'<RFOR0302>' in content:
                handler = import_rfor0302
            else:
                results['failed'].append({'filename': filename, 'reason': 'Unsupported XML document type'})
                continue
         
            handler_result = handler(content)
            
            results['successful'].append({
                'filename': filename, 
                'details': handler_result.get_json() if hasattr(handler_result, 'get_json') else 'Processed'
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"Bulk import failure | filename={filename}")
            results['failed'].append({'filename': filename, 'reason': str(e)})

    # Determine standard HTTP status code
    if not results['failed']:
        status_code = 200 # All good
    elif not results['successful']:
        status_code = 400 # All failed
    else:
        status_code = 207 # Multi-Status (Partial success)

    return jsonify(results), status_code