import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./ImportFile.css";

const CHUNK_SIZE = 1024 * 1024; // 1MB
const ALLOWED_EXTENSIONS = ["xml"];

const STATUS_LABELS = {
  pending: "Na fila",
  uploading: "Enviando",
  processing: "Processando",
  completed: "Concluído",
  error: "Erro",
  canceled: "Cancelado",
};

const ImportFile = () => {
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);
  const filesQueueRef = useRef(null);
  const activeFileRef = useRef(null);

  const notify = (text, type = "info") => setFeedback({ text, type });

  const validateFile = (file) => {
    const extension = file.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      throw new Error("Arquivo inválido. Apenas arquivos XML são permitidos.");
    }

    if (file.size > 100 * 1024 * 1024) {
      throw new Error("Arquivo muito grande. Tamanho máximo permitido: 100MB");
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const power = Math.min(
      Math.floor(Math.log(bytes) / Math.log(1024)),
      units.length - 1
    );
    const value = bytes / Math.pow(1024, power);
    return `${value.toFixed(value >= 10 || power === 0 ? 0 : 1)} ${
      units[power]
    }`;
  };

  const updateFile = (fileId, updater) => {
    setFiles((prev) =>
      prev.map((item) =>
        item.id === fileId
          ? {
              ...item,
              ...(typeof updater === "function" ? updater(item) : updater),
            }
          : item
      )
    );

    // Update active file ref for auto-scroll
    if (
      typeof updater === "object" &&
      (updater.status === "uploading" || updater.status === "processing")
    ) {
      activeFileRef.current = fileId;
    }
  };

  const addFilesToQueue = (newFiles) => {
    if (!newFiles.length) return;

    const acceptedFiles = [];
    newFiles.forEach((file) => {
      try {
        validateFile(file);
        acceptedFiles.push(file);
      } catch (error) {
        notify(error.message, "error");
      }
    });

    if (!acceptedFiles.length) return;

    setFiles((prev) => {
      const existingKeys = new Set(
        prev.map((item) => `${item.file.name}-${item.file.size}`)
      );

      const newEntries = acceptedFiles
        .filter((file) => !existingKeys.has(`${file.name}-${file.size}`))
        .map((file) => ({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`,
          file,
          status: "pending",
          progress: 0,
          message: "",
        }));

      if (!newEntries.length) {
        notify("Os arquivos selecionados já estão na fila.", "info");
        return prev;
      }

      notify(`${newEntries.length} arquivo(s) adicionados à fila.`, "success");
      return [...prev, ...newEntries];
    });
  };

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    addFilesToQueue(selectedFiles);
    event.target.value = "";
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    addFilesToQueue(droppedFiles);
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemoveFile = (fileId) => {
    setFiles((prev) => prev.filter((item) => item.id !== fileId));
  };

  const handleRetry = (fileId) => {
    updateFile(fileId, { status: "pending", progress: 0, message: "" });
    notify("Arquivo marcado para reenvio.", "info");
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
      if (
        error.name === "AbortError" ||
        error.code === "ERR_CANCELED" ||
        (typeof axios.isCancel === "function" && axios.isCancel(error))
      ) {
        throw new Error("Upload cancelado pelo usuário");
      }
      throw error;
    }
  };

  const uploadSingleFile = async (fileItem) => {
    const { id, file } = fileItem;

    try {
      updateFile(id, {
        status: "uploading",
        progress: 0,
        message: "Preparando envio...",
      });

      abortControllerRef.current = new AbortController();

      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      for (let i = 0; i < totalChunks; i++) {
        const chunk = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
        await uploadChunk(chunk, i, totalChunks, id);
        const progress = Math.round(((i + 1) / totalChunks) * 100);
        updateFile(id, { progress });
      }

      updateFile(id, {
        status: "processing",
        message: "Arquivo enviado. Processando informação...",
      });

      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/api/process_file`,
        { fileId: id },
        { withCredentials: true }
      );

      updateFile(id, {
        status: "completed",
        progress: 100,
        message: response.data?.message || "Importação concluída com sucesso.",
      });

      return "success";
    } catch (error) {
      const errorMessage =
        error.response?.data?.error || error.message || "Erro inesperado.";

      if (errorMessage.includes("Upload cancelado")) {
        updateFile(id, {
          status: "canceled",
          message: errorMessage,
        });
        return "aborted";
      }

      updateFile(id, {
        status: "error",
        message: errorMessage,
      });

      return "error";
    } finally {
      abortControllerRef.current = null;
    }
  };

  const startUpload = async () => {
    if (isUploading) return;

    const queue = files.filter((file) =>
      ["pending", "error", "canceled"].includes(file.status)
    );

    if (!queue.length) {
      notify("Nenhum arquivo pendente para envio.", "info");
      return;
    }

    setIsUploading(true);
    notify(`Iniciando envio de ${queue.length} arquivo(s)...`, "info");

    let aborted = false;

    for (const fileItem of queue) {
      const result = await uploadSingleFile(fileItem);
      if (result === "aborted") {
        notify("Envio cancelado pelo usuário.", "warning");
        aborted = true;
        break;
      }
    }

    setIsUploading(false);

    if (!aborted) {
      notify("Fila processada com sucesso.", "success");
    }
  };

  const handleCancel = () => {
    if (!abortControllerRef.current) return;
    notify("Cancelando envio atual...", "warning");
    abortControllerRef.current.abort();
  };

  const hasPendingFiles = files.some((file) =>
    ["pending", "error", "canceled"].includes(file.status)
  );

  // Auto-scroll to active file
  useEffect(() => {
    if (activeFileRef.current && filesQueueRef.current) {
      const activeElement = document.querySelector(
        `[data-file-id="${activeFileRef.current}"]`
      );
      if (activeElement && filesQueueRef.current) {
        const container = filesQueueRef.current;
        const elementTop = activeElement.offsetTop;
        const elementHeight = activeElement.offsetHeight;
        const containerHeight = container.clientHeight;
        const scrollTop = container.scrollTop;

        // Check if element is not fully visible
        if (
          elementTop < scrollTop ||
          elementTop + elementHeight > scrollTop + containerHeight
        ) {
          activeElement.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          });
        }
      }
    }
  }, [files]);

  React.useEffect(() => {
    if (!isUploading && files.some((f) => f.status === "pending")) {
      startUpload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files, isUploading]);

  return (
    <div className="import-file-container">
      <div
        className={`import-panel ${isDragging ? "dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="import-header">
          <h1>Importar Arquivos</h1>
          <p>
            Importe relatórios XML do FoccoERP para sincronizar pedidos de
            compra, cotações e informações de fornecedores.
          </p>
        </div>

        <div className="import-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xml"
            multiple
            hidden
            onChange={handleFileChange}
          />
          <button
            type="button"
            className="action-button primary"
            onClick={handleBrowseClick}
            disabled={isUploading}
          >
            Selecionar arquivos
          </button>
          {isUploading && (
            <button
              type="button"
              className="action-button danger"
              onClick={handleCancel}
            >
              Cancelar envio
            </button>
          )}
        </div>

        {feedback && (
          <div className={`global-message ${feedback.type}`}>
            {feedback.text}
          </div>
        )}

        <div className="files-queue" ref={filesQueueRef}>
          {files.length === 0 ? (
            <div className="empty-queue">
              <p>Nenhum arquivo na fila.</p>
              <span>Use o botão "Selecionar arquivos" para começar.</span>
            </div>
          ) : (
            files.map((fileItem) => (
              <div
                className="file-card"
                key={fileItem.id}
                data-file-id={fileItem.id}
              >
                <div className="file-card-header">
                  <div>
                    <p className="file-name">{fileItem.file.name}</p>
                    <span className="file-size">
                      {formatBytes(fileItem.file.size)}
                    </span>
                  </div>
                  <span className={`status-pill status-${fileItem.status}`}>
                    {STATUS_LABELS[fileItem.status] || fileItem.status}
                  </span>
                </div>

                <div className="progress-wrapper">
                  <div className="progress-bar">
                    <div
                      className={`progress-bar-fill status-${fileItem.status}`}
                      style={{ width: `${fileItem.progress}%` }}
                    />
                  </div>
                  {fileItem.status === "processing" && (
                    <div
                      className="processing-indicator"
                      aria-label="Processando arquivo"
                    >
                      <span className="sr-only">Processando</span>
                    </div>
                  )}
                  <span className="progress-value">{fileItem.progress}%</span>
                </div>

                {fileItem.message && (
                  <p
                    className={`file-message ${
                      fileItem.status === "error" ? "error" : ""
                    }`}
                  >
                    {fileItem.message}
                  </p>
                )}

                <div className="file-actions">
                  {["pending", "error", "canceled"].includes(
                    fileItem.status
                  ) && (
                    <button
                      type="button"
                      onClick={() => handleRemoveFile(fileItem.id)}
                      disabled={isUploading && fileItem.status === "pending"}
                    >
                      Remover
                    </button>
                  )}
                  {fileItem.status === "error" && (
                    <button
                      type="button"
                      className="retry"
                      onClick={() => handleRetry(fileItem.id)}
                      disabled={isUploading}
                    >
                      Tentar novamente
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default ImportFile;
