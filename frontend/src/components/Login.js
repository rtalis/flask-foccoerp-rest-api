import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Login.css';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Component to handle map zoom animation
const ZoomToLocation = ({ trigger, targetLocation, targetZoom }) => {
  const map = useMap();
  
  useEffect(() => {
    if (trigger) {
      map.flyTo(targetLocation, targetZoom, {
        duration: 3.5,
        easeLinearity: 0.25,
      });
    }
  }, [trigger, targetLocation, targetZoom, map]);
  
  return null;
};

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);
  const [startAnimation, setStartAnimation] = useState(false);

  // Map configuration - Change these to your desired location
  const initialCenter = [-15.7801, -47.9292]; 
  const initialZoom = 2;
  const targetLocation = [-3.123873, -40.127983]; 
  const targetZoom = 14;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setStartAnimation(true); 
    
    try {
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/auth/login`, { email, password }, { withCredentials: true });
      if (response.status === 200) {
        setLoginSuccess(true);
        setTimeout(() => {
          onLogin();
        }, 1);
      }
    } catch (error) {
      setError('Login failed: Invalid email or password');
      setStartAnimation(false); 
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* Map Background */}
      <div className="map-background">
        <MapContainer
          center={initialCenter}
          zoom={initialZoom}
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
          attributionControl={false}
          dragging={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          touchZoom={false}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}{r}.png"
          />
          <ZoomToLocation
            trigger={startAnimation}
            targetLocation={targetLocation}
            targetZoom={targetZoom}
          />
        </MapContainer>
      </div>

      {/* Login Form Overlay */}
      <div className={`login-overlay ${loginSuccess ? 'fade-out' : ''}`}>
        <form className="login-form" onSubmit={handleSubmit}>
          <h2>JHub - Hub de buscas Ruah</h2>
          <div>
            <label>Email:</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label>Password:</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" disabled={loading || loginSuccess}>
            {loading && <span className="loading-spinner"></span>}
            {loginSuccess ? 'Welcome!' : loading ? 'Logging in...' : 'Login'}
          </button>
          {error && <p className="error-message">{error}</p>}
        </form>
      </div>

      {/* Copyright */}
      <div className="copyright">
        <span>© {new Date().getFullYear()} Roxel.dev | Criado por Ronaldo Talison | v2.0.0</span>
      </div>
    </div>
  );
};

export default Login;