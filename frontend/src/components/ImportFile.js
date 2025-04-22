import React, { useState } from 'react';
import axios from 'axios';
import './ImportFile.css';

const ImportFile = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setMessage('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('file', file);

    try {
      setLoading(true);
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/api/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        withCredentials: true
      });
      setMessage(response.data.message || 'Arquivo importado com sucesso');
    } catch (error) {
      setMessage(error.response?.data?.error || 'Erro ao importar arquivo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="import-file-container">
      <form onSubmit={handleSubmit} className="import-file-form">
        <h2>Importar Arquivo</h2>
        <input type="file" onChange={handleFileChange} required />
        <button className='import-file-button' type="submit" disabled={loading}>
          {loading ? 'Importando...' : 'Importar'}
        </button>
        {message && <p className={`message ${message.includes('Erro') ? 'error' : 'success'}`}>{message}</p>}
      </form>
      
      {loading && (
        <div className="loading-overlay">
          <div className="loading-icon">
            <div className="spinner"></div>
          </div>
          <div className="loading-text">
            Importando arquivo...
            <br />
            Por favor, aguarde.
          </div>
        </div>
      )}
    </div>
  );
};

export default ImportFile;