import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import UnifiedSearch from './components/UnifiedSearch';
import Login from './components/Login';
import Register from './components/Register';

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/auth/protected`, { withCredentials: true });
        if (response.status === 200) {
          setIsAuthenticated(true);

          // Automatically log out after 1 hour
          const logoutTimer = setTimeout(handleLogout, 3600000);
          return () => clearTimeout(logoutTimer); // Cleanup timeout
        }
      } catch (error) {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);

    setTimeout(handleLogout, 3600000);
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${process.env.REACT_APP_API_URL}/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error('Error logging out:', error);
    } finally {
      setIsAuthenticated(false);
    }
  };

  return (
    <Router>
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/search" /> : <Login onLogin={handleLogin} />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/search" /> : <Register />} />
        <Route
          path="/search"
          element={isAuthenticated ? <UnifiedSearch onLogout={handleLogout} /> : <Navigate to="/login" />}
        />
          <Route path="/import" element={isAuthenticated ? <ImportFile /> : <Login />} />
        <Route path="*" element={<Navigate to={isAuthenticated ? "/search" : "/login"} />} />
      </Routes>
    </Router>
  );
};

export default App;
