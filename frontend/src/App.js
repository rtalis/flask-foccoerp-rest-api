import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import UnifiedSearch from './components/UnifiedSearch';
import Login from './components/Login';

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get('http://localhost:5000/auth/protected');
        if (response.status === 200) {
          setIsAuthenticated(true);
          setTimeout(() => {
            handleLogout();
          }, 3600000); // 1 hora em milissegundos
        }
      } catch (error) {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
    setTimeout(() => {
      handleLogout();
    }, 3600000); // 1 hora em milissegundos
  };

  const handleLogout = async () => {
    try {
      await axios.post('http://localhost:5000/auth/logout');
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Error logging out', error);
    }
  };

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/login" element={isAuthenticated ? <Navigate to="/search" /> : <Login onLogin={handleLogin} />} />
          <Route path="/register" element={isAuthenticated ? <Navigate to="/search" /> : <Login />} />
          <Route path="/search" element={isAuthenticated ? <UnifiedSearch onLogout={handleLogout} /> : <Navigate to="/login" />} />
          <Route path="/" element={<Navigate to="/login" />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;