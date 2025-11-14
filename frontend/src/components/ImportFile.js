import React, { useState, useRef } from "react";
import axios from "axios";
import "./ImportFile.css";

const CHUNK_SIZE = 1024 * 1024; // 1MB chunks
const ALLOWED_EXTENSIONS = ["xml"];

const ImportFile = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const abortControllerRef = useRef(null);

  const validateFile = (file) => {
    const extension = file.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      throw new Error("Arquivo inválido. Apenas arquivos XML são permitidos.");
    }

    // Validar tamanho máximo (exemplo: 50MB)
    if (file.size > 50 * 1024 * 1024) {
      throw new Error("Arquivo muito grande. Tamanho máximo permitido: 50MB");
    }
  };

  const uploadChunk = async (chunk, chunkIndex, totalChunks, fileId) => {
    const formData = new FormData();
    formData.append("file", chunk);
    formData.append("chunkIndex", chunkIndex);
    formData.append("totalChunks", totalChunks);
    formData.append("fileId", fileId);

    try {
      await axios.post(
        `${process.env.REACT_APP_API_URL}/api/upload_chunk`,
        formData,
        {
          withCredentials: true,
          signal: abortControllerRef.current?.signal,
        }
      );
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error("Upload cancelado pelo usuário");
      }
      throw error;
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    try {
      if (selectedFile) {
        validateFile(selectedFile);
        setFile(selectedFile);
        setMessage("");
      }
    } catch (error) {
      setMessage(error.message);
      e.target.value = null;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    try {
      setIsUploading(true);
      setMessage("");

      const fileId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      let uploadedChunks = 0;

      abortControllerRef.current = new AbortController();

      for (let i = 0; i < totalChunks; i++) {
        const chunk = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
        await uploadChunk(chunk, i, totalChunks, fileId);
        uploadedChunks++;
        setUploadProgress(Math.round((uploadedChunks / totalChunks) * 100));
      }

      // Iniciar processamento
      setIsProcessing(true);
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/api/process_file`,
        { fileId },
        { withCredentials: true }
      );

      setMessage(response.data.message);
    } catch (error) {
      setMessage(error.response?.data?.error || error.message);
    } finally {
      setIsUploading(false);
      setIsProcessing(false);
      setUploadProgress(0);
      abortControllerRef.current = null;
    }
  };

  const handleCancel = () => {
    abortControllerRef.current?.abort();
    setMessage("Upload cancelado");
    setIsUploading(false);
    setUploadProgress(0);
  };

  return (
    <div className="import-file-container">
      <form onSubmit={handleSubmit} className="import-file-form">
        <h2>Importar Arquivo</h2>
        <p>Selecione um arquivo de relatório XML para importação:</p>
        <input
          type="file"
          onChange={handleFileChange}
          accept=".xml"
          disabled={isUploading || isProcessing}
          required
        />
        <div className="button-group">
          <button
            className="import-file-button"
            type="submit"
            disabled={isUploading || isProcessing || !file}
          >
            {isUploading
              ? "Enviando..."
              : isProcessing
              ? "Processando..."
              : "Importar"}
          </button>
          {isUploading && (
            <button
              type="button"
              className="cancel-button"
              onClick={handleCancel}
            >
              Cancelar
            </button>
          )}
        </div>
        {message && (
          <p
            className={`message ${
              message.includes("Erro") ? "error" : "success"
            }`}
          >
            {message}
          </p>
        )}
      </form>

      {(isUploading || isProcessing) && (
        <div className="loading-overlay">
          <div className="loading-icon">
            <div className="spinner"></div>
            {isUploading && (
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            )}
          </div>
          <div className="loading-text">
            {isUploading
              ? isProcessing
                ? "Processando arquivo..."
                : `Enviando arquivo... ${uploadProgress}%`
              : "Processando arquivo..."}
            <br />
            Por favor, aguarde.
          </div>
        </div>
      )}
    </div>
  );
};

export default ImportFile;
