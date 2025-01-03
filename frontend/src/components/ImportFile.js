// filepath: /home/talison/dev/flask-rest-api/frontend/src/components/ImportFile.js
import React, { useState } from 'react';
import axios from 'axios';
import './ImportFile.css';

const ImportFile = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/api/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        withCredentials: true
      });
      setMessage(response.data.message || 'File imported successfully');
    } catch (error) {
      setMessage(error.response.data.error || 'Error importing file');
    }
  };

  return (
    <div className="import-file-container">
      <form onSubmit={handleSubmit} className="import-file-form">
        <h2>Import File</h2>
        <input type="file" onChange={handleFileChange} required />
        <button className='import-file-button' type="submit">Import</button>
        {message && <p className="message">{message}</p>}
      </form>
    </div>
  );
};

export default ImportFile;