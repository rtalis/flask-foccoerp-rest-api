import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import Layout from "./components/Layout";
import UnifiedSearch from "./components/UnifiedSearch";
import Login from "./components/Login";
import ImportFile from "./components/ImportFile";
import Register from "./components/Register";
import QuotationAnalyzer from "./components/QuotationAnalyzer";
import Dashboard from "./components/Dashboard";
import AdvancedSearch from "./components/AdvancedSearch";
import TokenManager from "./components/TokenManager";

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL}/auth/protected`,
          { withCredentials: true }
        );
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
  }, []);

  useEffect(() => {
    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401) {
          setIsAuthenticated(false);
          if (window.location.pathname !== "/login") {
            window.location.href = "/login";
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptorId);
    };
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
    setTimeout(handleLogout, 3600000);
  };

  const handleLogout = async () => {
    try {
      await axios.post(
        `${process.env.REACT_APP_API_URL}/auth/logout`,
        {},
        { withCredentials: true }
      );
    } catch (error) {
      console.error("Error logging out:", error);
    } finally {
      setIsAuthenticated(false);
    }
  };

  return (
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
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/advanced-search" element={<AdvancedSearch />} />
          <Route path="/quotation-analyzer" element={<QuotationAnalyzer />} />
          <Route path="/import" element={<ImportFile />} />
          <Route path="/register" element={<Register />} />
          <Route path="/token-manager" element={<TokenManager />} />
        </Route>

        {/* Default redirect */}
        <Route
          path="*"
          element={<Navigate to={isAuthenticated ? "/search" : "/login"} />}
        />
      </Routes>
    </Router>
  );
};

export default App;
