import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Paper,
  Snackbar,
  Alert,
  Stack,
  Divider,
  Skeleton,
  InputAdornment,
  IconButton,
} from "@mui/material";
import {
  AccountCircle as AccountCircleIcon,
  Save as SaveIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Lock as LockIcon,
} from "@mui/icons-material";

const Account = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userData, setUserData] = useState({
    username: "",
    email: "",
    purchaser_name: "",
  });
  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [alert, setAlert] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/auth/me`,
        { withCredentials: true },
      );
      setUserData({
        username: response.data.username || "",
        email: response.data.email || "",
        purchaser_name: response.data.purchaser_name || "",
      });
    } catch (error) {
      setAlert({
        open: true,
        message: "Erro ao carregar dados da conta",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUserDataChange = (e) => {
    const { name, value } = e.target;
    setUserData((prev) => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData((prev) => ({ ...prev, [name]: value }));
  };

  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();

    if (!userData.username || userData.username.trim() === "") {
      setAlert({
        open: true,
        message: "Nome de usuário é obrigatório",
        severity: "error",
      });
      return;
    }

    if (!userData.email || !isValidEmail(userData.email)) {
      setAlert({
        open: true,
        message: "Email válido é obrigatório",
        severity: "error",
      });
      return;
    }

    setSaving(true);
    try {
      await axios.put(
        `${process.env.REACT_APP_API_URL}/auth/me`,
        {
          username: userData.username,
          email: userData.email,
          purchaser_name: userData.purchaser_name,
        },
        { withCredentials: true },
      );
      setAlert({
        open: true,
        message: "Perfil atualizado com sucesso!",
        severity: "success",
      });
    } catch (error) {
      setAlert({
        open: true,
        message: error.response?.data?.error || "Erro ao atualizar perfil",
        severity: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();

    if (passwordData.new_password !== passwordData.confirm_password) {
      setAlert({
        open: true,
        message: "As senhas não coincidem",
        severity: "error",
      });
      return;
    }

    if (passwordData.new_password.length < 8) {
      setAlert({
        open: true,
        message: "A nova senha deve ter pelo menos 8 caracteres",
        severity: "error",
      });
      return;
    }

    setSaving(true);
    try {
      await axios.put(
        `${process.env.REACT_APP_API_URL}/auth/me`,
        {
          current_password: passwordData.current_password,
          new_password: passwordData.new_password,
        },
        { withCredentials: true },
      );
      setAlert({
        open: true,
        message: "Senha alterada com sucesso!",
        severity: "success",
      });
      setPasswordData({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (error) {
      setAlert({
        open: true,
        message: error.response?.data?.error || "Erro ao alterar senha",
        severity: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  const togglePasswordVisibility = (field) => {
    setShowPasswords((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Skeleton variant="rounded" height={300} />
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
        <AccountCircleIcon color="primary" sx={{ fontSize: 28 }} />
        <Typography variant="h5" fontWeight={600}>
          Minha Conta
        </Typography>
      </Box>

      <Stack spacing={3}>
        {/* Profile Section */}
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 2 }}>
            Informações do Perfil
          </Typography>
          <Box component="form" onSubmit={handleSaveProfile}>
            <Stack spacing={2.5}>
              <TextField
                size="small"
                label="Nome de usuário"
                name="username"
                value={userData.username}
                onChange={handleUserDataChange}
                fullWidth
                required
              />
              <TextField
                size="small"
                label="Email"
                name="email"
                type="email"
                value={userData.email}
                onChange={handleUserDataChange}
                fullWidth
                required
              />
              <TextField
                size="small"
                label="Nome de exibição"
                name="purchaser_name"
                value={userData.purchaser_name}
                onChange={handleUserDataChange}
                fullWidth
                helperText="Este nome será exibido em relatórios e atividades"
              />
              <Box sx={{ pt: 1 }}>
                <Button
                  type="submit"
                  variant="contained"
                  disableElevation
                  startIcon={<SaveIcon />}
                  disabled={saving}
                >
                  Salvar Alterações
                </Button>
              </Box>
            </Stack>
          </Box>
        </Paper>

        {/* Password Section */}
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
            <LockIcon fontSize="small" color="action" />
            <Typography variant="subtitle1" fontWeight={600}>
              Alterar Senha
            </Typography>
          </Box>
          <Divider sx={{ mb: 2.5 }} />
          <Box component="form" onSubmit={handleChangePassword}>
            <Stack spacing={2.5}>
              <TextField
                size="small"
                label="Senha atual"
                name="current_password"
                type={showPasswords.current ? "text" : "password"}
                value={passwordData.current_password}
                onChange={handlePasswordChange}
                required
                fullWidth
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => togglePasswordVisibility("current")}
                        edge="end"
                      >
                        {showPasswords.current ? (
                          <VisibilityOffIcon fontSize="small" />
                        ) : (
                          <VisibilityIcon fontSize="small" />
                        )}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <TextField
                size="small"
                label="Nova senha"
                name="new_password"
                type={showPasswords.new ? "text" : "password"}
                value={passwordData.new_password}
                onChange={handlePasswordChange}
                required
                fullWidth
                helperText="Mínimo de 8 caracteres"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => togglePasswordVisibility("new")}
                        edge="end"
                      >
                        {showPasswords.new ? (
                          <VisibilityOffIcon fontSize="small" />
                        ) : (
                          <VisibilityIcon fontSize="small" />
                        )}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <TextField
                size="small"
                label="Confirmar nova senha"
                name="confirm_password"
                type={showPasswords.confirm ? "text" : "password"}
                value={passwordData.confirm_password}
                onChange={handlePasswordChange}
                required
                fullWidth
                error={
                  passwordData.confirm_password !== "" &&
                  passwordData.new_password !== passwordData.confirm_password
                }
                helperText={
                  passwordData.confirm_password !== "" &&
                  passwordData.new_password !== passwordData.confirm_password
                    ? "As senhas não coincidem"
                    : ""
                }
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => togglePasswordVisibility("confirm")}
                        edge="end"
                      >
                        {showPasswords.confirm ? (
                          <VisibilityOffIcon fontSize="small" />
                        ) : (
                          <VisibilityIcon fontSize="small" />
                        )}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <Box sx={{ pt: 1 }}>
                <Button
                  type="submit"
                  variant="contained"
                  disableElevation
                  startIcon={<LockIcon />}
                  disabled={saving}
                >
                  Alterar Senha
                </Button>
              </Box>
            </Stack>
          </Box>
        </Paper>
      </Stack>

      <Snackbar
        open={alert.open}
        autoHideDuration={4000}
        onClose={() => setAlert({ ...alert, open: false })}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={() => setAlert({ ...alert, open: false })}
          severity={alert.severity}
          variant="filled"
        >
          {alert.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Account;
