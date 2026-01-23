import React from "react";
import { useServerError } from "../context/ServerErrorContext";
import "./ServerErrorPopup.css";

const ServerErrorPopup = () => {
  const {
    error,
    isVisible,
    errorType,
    hideError,
    goToBackupServer,
    goToLogin,
    backupUrl,
  } = useServerError();

  if (!isVisible) {
    return null;
  }

  // Session invalidated popup (logged in from another device)
  if (errorType === "session") {
    return (
      <div className="server-error-overlay">
        <div className="server-error-popup">
          <div className="server-error-icon session-error-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              width="48"
              height="48"
            >
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" />
            </svg>
          </div>

          <h2 className="server-error-title">Sessão Encerrada</h2>

          <p className="server-error-message">
            Você foi desconectado porque sua conta foi acessada em outro
            dispositivo.
          </p>

          <p
            className="server-error-message"
            style={{ marginTop: "8px", fontSize: "0.9rem", color: "#6c757d" }}
          >
            Apenas uma sessão ativa é permitida por vez. Se não foi você,
            recomendamos alterar sua senha.
          </p>

          <div className="server-error-actions">
            <button
              className="server-error-btn server-error-btn-primary"
              onClick={goToLogin}
            >
              Fazer Login Novamente
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Server error popup
  return (
    <div className="server-error-overlay">
      <div className="server-error-popup">
        <div className="server-error-icon">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            width="48"
            height="48"
          >
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
        </div>

        <h2 className="server-error-title">Erro no Servidor</h2>

        <p className="server-error-message">
          Ocorreu um erro ao processar sua requisição. Isso pode ter ocorrido
          por:
        </p>

        <ul className="server-error-reasons">
          <li>O servidor está temporariamente indisponível</li>
          <li>Problemas de conexão com a internet</li>
          <li>Manutenção programada</li>
        </ul>

        {error?.message && (
          <div className="server-error-details">
            <strong>Detalhes:</strong> {error.message}
          </div>
        )}

        <div className="server-error-actions">
          <button
            className="server-error-btn server-error-btn-secondary"
            onClick={hideError}
          >
            Fechar
          </button>

          <button
            className="server-error-btn server-error-btn-primary"
            onClick={goToBackupServer}
          >
            Usar Backup (jhub2)
            <span className="server-error-btn-hint">{backupUrl}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ServerErrorPopup;
