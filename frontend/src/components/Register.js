import React, { useState } from 'react';
import axios from 'axios';
import './Register.css';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/auth/register`, { username, email, password });
      if (response.status === 201) {
        window.location.href = '/login';
      }
    } catch (error) {
      setError('Registration failed' );
    }
  };

  return (
    <div className="register-container">
      <form onSubmit={handleSubmit}>
        <h2>Register</h2>
        {error && <p className="error">{error}</p>}
        <div>
          <label>Username</label>
          <input className='register-input' type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div>
          <label>Email</label>
          <input className='register-input' type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label>Password</label>
          <input className='register-input' type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <button className='register-button' type="submit">Register</button>
      </form>
    </div>
  );
};

export default Register;