import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";

import {
  ServerErrorProvider,
  useServerError,
} from "./context/ServerErrorContext";
import Layout from "./components/Layout";
import UnifiedSearch from "./components/UnifiedSearch";
import Login from "./components/Login";
import ImportFile from "./components/ImportFile";
import Register from "./components/Register";
import QuotationAnalyzer from "./components/QuotationAnalyzer";
import Dashboard from "./components/Dashboard";
import AdvancedSearch from "./components/AdvancedSearch";
import TokenManager from "./components/TokenManager";
import NFESearch from "./components/NFESearch";
import ReleaseNotes from "./components/ReleaseNotes";
import ServerErrorPopup from "./components/ServerErrorPopup";
import Account from "./components/Account";

const AppContent = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showReleaseNotes, setShowReleaseNotes] = useState(false);
  const [unseenReleases, setUnseenReleases] = useState([]);
  const { showError, showSessionError } = useServerError();

  const apiUrl = process.env.REACT_APP_API_URL;

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${apiUrl}/auth/protected`, {
          withCredentials: true,
        });
        if (response.status === 200) {
          setIsAuthenticated(true);

          // Automatically log out after 1 hour
          const logoutTimer = setTimeout(handleLogout, 3600000);
          return () => clearTimeout(logoutTimer);
        }
      } catch (error) {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, [apiUrl]);

  // Interceptor for 401 (auth) errors and session invalidation
  useEffect(() => {
    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        // Check for session invalidation (logged in from another device)
        if (error?.response?.status === 403 && 
            error?.response?.data?.code === 'SESSION_INVALIDATED') {
          setIsAuthenticated(false);
          showSessionError({
            message: error.response.data.message || 'Você foi desconectado porque fez login em outro dispositivo.',
          });
          return Promise.reject(error);
        }
        
        if (error?.response?.status === 401) {
          setIsAuthenticated(false);
          if (window.location.pathname !== "/login") {
            window.location.href = "/login";
          }
        }
        return Promise.reject(error);
      },
    );

    return () => {
      axios.interceptors.response.eject(interceptorId);
    };
  }, [showSessionError]);

  // Interceptor for server errors (network errors, 500+, timeouts)
  useEffect(() => {
    const serverErrorInterceptorId = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        // Check if it's a server error or network error
        const isNetworkError = !error.response && error.message;
        const isServerError = error.response?.status >= 500;
        const isTimeout =
          error.code === "ECONNABORTED" || error.message?.includes("timeout");

        // Ignore cancelled requests
        if (axios.isCancel(error)) {
          return Promise.reject(error);
        }

        if (isNetworkError || isServerError || isTimeout) {
          let errorMessage = "Erro desconhecido";

          if (isTimeout) {
            errorMessage = "Tempo limite de conexão excedido";
          } else if (isNetworkError) {
            errorMessage =
              error.message || "Não foi possível conectar ao servidor";
          } else if (isServerError) {
            errorMessage = `Erro do servidor (${error.response.status}): ${error.response.statusText || "Erro interno"}`;
          }

          showError({
            message: errorMessage,
            status: error.response?.status,
            url: error.config?.url,
          });
        }

        return Promise.reject(error);
      },
    );

    return () => {
      axios.interceptors.response.eject(serverErrorInterceptorId);
    };
  }, [showError]);

  const handleLogin = () => {
    setIsAuthenticated(true);
    setTimeout(handleLogout, 3600000);

    fetch("/release-notes.json")
      .then((res) => res.json())
      .then((releases) => {
        if (!Array.isArray(releases)) return;
        releases.sort((a, b) => (a.version > b.version ? 1 : -1));
        const unseen = releases.filter(
          (rel) => !localStorage.getItem(`releaseNotesSeen_${rel.version}`),
        );
        if (unseen.length > 0) {
          setUnseenReleases(unseen);
          setShowReleaseNotes(true);
        } else {
          setUnseenReleases([]);
          setShowReleaseNotes(false);
        }
        unseen.forEach((rel) =>
          localStorage.setItem(`releaseNotesSeen_${rel.version}`, "true"),
        );
      });
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${apiUrl}/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error("Error logging out:", error);
    } finally {
      setIsAuthenticated(false);
    }
  };

  return (
    <>
      <ServerErrorPopup />
      {showReleaseNotes && unseenReleases.length > 0 && (
        <ReleaseNotes
          onClose={() => setShowReleaseNotes(false)}
          unseenReleases={unseenReleases}
        />
      )}
      <Router>
        <Routes>
          {/* Public routes - no sidebar */}
          <Route
            path="/login"
            element={
              isAuthenticated ? (
                <Navigate to="/search" />
              ) : (
                <Login onLogin={handleLogin} />
              )
            }
          />

          {/* Protected routes with shared Layout */}
          <Route
            element={
              isAuthenticated ? (
                <Layout onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" />
              )
            }
          >
            <Route path="/search" element={<UnifiedSearch />} />
            <Route path="/nfe-search" element={<NFESearch />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/advanced-search" element={<AdvancedSearch />} />
            <Route path="/quotation-analyzer" element={<QuotationAnalyzer />} />
            <Route path="/import" element={<ImportFile />} />
            <Route path="/register" element={<Register />} />
            <Route path="/token-manager" element={<TokenManager />} />
            <Route path="/account" element={<Account />} />
          </Route>

          {/* Default redirect */}
          <Route
            path="*"
            element={<Navigate to={isAuthenticated ? "/search" : "/login"} />}
          />
        </Routes>
      </Router>
    </>
  );
};

const App = () => {
  return (
    <ServerErrorProvider>
      <AppContent />
    </ServerErrorProvider>
  );
};

export default App;
