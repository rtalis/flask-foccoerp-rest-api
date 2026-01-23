import React, { useState, useEffect } from "react";
import axios from "axios";
import "./Login.css";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);
  const [startAnimation, setStartAnimation] = useState(false);
  const [version, setVersion] = useState("");
  const [showSessionWarning, setShowSessionWarning] = useState(false);
  const [warningMessage, setWarningMessage] = useState("");

  useEffect(() => {
    fetch("/release-notes.json")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          // Sort by version (assume semantic versioning, latest last)
          const sorted = [...data].sort((a, b) =>
            a.version > b.version ? 1 : -1,
          );
          setVersion(sorted[sorted.length - 1].version);
        }
      });
  }, []);

  // Map configuration - Change these to your desired location
  const initialCenter = [-15.7801, -47.9292];
  const initialZoom = 2;
  const targetLocation = [-3.123873, -40.127983];
  const targetZoom = 14;

  const performLogin = async (force = false) => {
    setLoading(true);
    setError("");
    if (!force) {
      setStartAnimation(true);
    }

    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/auth/login`,
        { email, password, force },
        { withCredentials: true },
      );

      if (response.status === 200) {
        // Check if this is a warning about existing session
        if (
          response.data.warning === "active_session" &&
          response.data.requires_confirmation
        ) {
          setWarningMessage(response.data.message);
          setShowSessionWarning(true);
          setStartAnimation(false);
          setLoading(false);
          return;
        }

        // Successful login
        setLoginSuccess(true);
        setTimeout(() => {
          onLogin();
        }, 1);
      }
    } catch (error) {
      setError("Login failed: Invalid email or password");
      setStartAnimation(false);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    performLogin(false);
  };

  const handleConfirmLogin = () => {
    setShowSessionWarning(false);
    performLogin(true);
  };

  const handleCancelLogin = () => {
    setShowSessionWarning(false);
    setStartAnimation(false);
  };

  return (
    <div className="login-container">
      {/* Map Background */}
      <div className="map-background">
        <MapContainer
          center={initialCenter}
          zoom={initialZoom}
          style={{ height: "100%", width: "100%" }}
          zoomControl={false}
          attributionControl={false}
          dragging={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          touchZoom={false}
        >
          <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}{r}.png" />
          <ZoomToLocation
            trigger={startAnimation}
            targetLocation={targetLocation}
            targetZoom={targetZoom}
          />
        </MapContainer>
      </div>

      {/* Session Warning Dialog */}
      {showSessionWarning && (
        <div className="session-warning-overlay">
          <div className="session-warning-dialog">
            <div className="dialog-icon">ℹ️</div>
            <h3>Sessão em Andamento</h3>
            <p>{warningMessage}</p>
            <div className="warning-buttons">
              <button className="btn-cancel" onClick={handleCancelLogin}>
                Cancelar
              </button>
              <button className="btn-confirm" onClick={handleConfirmLogin}>
                Continuar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Login Form Overlay */}
      <div className={`login-overlay ${loginSuccess ? "fade-out" : ""}`}>
        <form className="login-form" onSubmit={handleSubmit}>
          <h2>JHub - Hub de buscas Ruah</h2>
          <div>
            <label>Email:</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label>Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={loading || loginSuccess}>
            {loading && <span className="loading-spinner"></span>}
            {loginSuccess ? "Welcome!" : loading ? "Logging in..." : "Login"}
          </button>
          {error && <p className="error-message">{error}</p>}
        </form>
      </div>

      {/* Copyright */}
      <div className="copyright">
        <span>
          © {new Date().getFullYear()} Roxel.dev | Criado por Ronaldo Talison
          {version && ` | v${version}`}
        </span>
      </div>
    </div>
  );
};

export default Login;
