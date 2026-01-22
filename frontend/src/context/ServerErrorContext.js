import React, { createContext, useContext, useState, useCallback } from "react";

const BACKUP_URL = "https://jhub2.roxel.dev";

const ServerErrorContext = createContext();

export const useServerError = () => {
  const context = useContext(ServerErrorContext);
  if (!context) {
    throw new Error("useServerError must be used within a ServerErrorProvider");
  }
  return context;
};

export const ServerErrorProvider = ({ children }) => {
  const [error, setError] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const [errorType, setErrorType] = useState("server"); // 'server' or 'session'

  const showError = useCallback((errorDetails) => {
    setError(errorDetails);
    setErrorType("server");
    setIsVisible(true);
  }, []);

  const showSessionError = useCallback((errorDetails) => {
    setError(errorDetails);
    setErrorType("session");
    setIsVisible(true);
  }, []);

  const hideError = useCallback(() => {
    setIsVisible(false);
    setError(null);
    setErrorType("server");
  }, []);

  const goToBackupServer = useCallback(() => {
    window.location.href = BACKUP_URL;
  }, []);

  const goToLogin = useCallback(() => {
    window.location.href = "/login";
  }, []);

  const value = {
    error,
    isVisible,
    errorType,
    backupUrl: BACKUP_URL,
    showError,
    showSessionError,
    hideError,
    goToBackupServer,
    goToLogin,
  };

  return (
    <ServerErrorContext.Provider value={value}>
      {children}
    </ServerErrorContext.Provider>
  );
};

export default ServerErrorContext;
