import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Paper,
  Snackbar,
  Alert,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Stack,
  Chip,
  Skeleton,
  Tooltip,
  Collapse,
} from "@mui/material";
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Close as CloseIcon,
  People as PeopleIcon,
  Key as KeyIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from "@mui/icons-material";

const Register = () => {
  const navigate = useNavigate();

  // User form state
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    role: "viewer",
    purchaser_name: "",
    system_name: "",
    initial_screen: "/dashboard",
    allowed_screens: ["/dashboard"],
  });

  // UI state
  const [isEditing, setIsEditing] = useState(false);
  const [editUserId, setEditUserId] = useState(null);
  const [error, setError] = useState("");
  const [purchaserNames, setPurchaserNames] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [alert, setAlert] = useState({
    open: false,
    message: "",
    severity: "success",
  });
  const [isAdmin, setIsAdmin] = useState(false);

  // Available screens for permissions
  const availableScreens = [
    { path: "/dashboard", label: "Dashboard" },
    { path: "/search", label: "Buscar Pedidos" },
    { path: "/quotation-analyzer", label: "Analisar Cotações" },
    { path: "/import", label: "Importar Dados" },
  ];

  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL}/auth/me`,
          { withCredentials: true }
        );
        if (response.data.role !== "admin") {
          setError("Somente administradores podem registrar novos usuários");
          setIsAdmin(false);
        } else {
          setIsAdmin(true);
          await Promise.all([fetchPurchaserNames(), fetchUsers()]);
        }
      } catch (err) {
        navigate("/login");
      } finally {
        setLoading(false);
      }
    };

    checkAdminStatus();
  }, [navigate]);

  const fetchPurchaserNames = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/purchasers`,
        { withCredentials: true }
      );
      // Filter out empty values and duplicates
      const filteredNames = response.data
        .filter((name) => name && name.trim() !== "")
        .filter((name, index, self) => self.indexOf(name) === index)
        .sort((a, b) => a.localeCompare(b));
      setPurchaserNames(filteredNames);
    } catch (error) {
      console.error("Error fetching purchaser names:", error);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/auth/users`,
        { withCredentials: true }
      );
      setUsers(response.data);
    } catch (error) {
      console.error("Error fetching users:", error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleScreensChange = (screenPath) => {
    setFormData((prev) => {
      const currentScreens = [...prev.allowed_screens];
      if (currentScreens.includes(screenPath)) {
        return {
          ...prev,
          allowed_screens: currentScreens.filter((path) => path !== screenPath),
        };
      } else {
        return {
          ...prev,
          allowed_screens: [...currentScreens, screenPath],
        };
      }
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isEditing && editUserId) {
        await axios.put(
          `${process.env.REACT_APP_API_URL}/auth/users/${editUserId}`,
          formData,
          { withCredentials: true }
        );
        setAlert({
          open: true,
          message: "Usuário atualizado!",
          severity: "success",
        });
      } else {
        const response = await axios.post(
          `${process.env.REACT_APP_API_URL}/auth/register`,
          formData,
          { withCredentials: true }
        );
        if (response.status === 201) {
          setAlert({
            open: true,
            message: "Usuário criado!",
            severity: "success",
          });
        } else {
          throw new Error("Falha ao criar usuário");
        }
      }
      resetForm();
      fetchUsers();
    } catch (error) {
      setAlert({
        open: true,
        message: error.response?.data?.error || "Operação falhou",
        severity: "error",
      });
    }
  };

  const handleEditUser = (user) => {
    setIsEditing(true);
    setEditUserId(user.id);
    setShowAdvanced(true);
    setFormData({
      username: user.username,
      email: user.email,
      password: "",
      role: user.role || "viewer",
      purchaser_name: user.purchaser_name || "",
      system_name: user.system_name || "",
      initial_screen: user.initial_screen || "/dashboard",
      allowed_screens: user.allowed_screens || ["/dashboard"],
    });
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Excluir este usuário?")) return;
    try {
      await axios.delete(
        `${process.env.REACT_APP_API_URL}/auth/users/${userId}`,
        { withCredentials: true }
      );
      setAlert({
        open: true,
        message: "Usuário excluído!",
        severity: "success",
      });
      fetchUsers();
    } catch (error) {
      setAlert({
        open: true,
        message: error.response?.data?.error || "Falha ao excluir",
        severity: "error",
      });
    }
  };

  const resetForm = () => {
    setFormData({
      username: "",
      email: "",
      password: "",
      role: "viewer",
      purchaser_name: "",
      system_name: "",
      initial_screen: "/dashboard",
      allowed_screens: ["/dashboard"],
    });
    setIsEditing(false);
    setEditUserId(null);
    setShowAdvanced(false);
    setError("");
  };

  const handleCloseAlert = () => setAlert({ ...alert, open: false });

  const getRoleLabel = (role) => {
    const labels = { admin: "Admin", purchaser: "Comprador", viewer: "Viewer" };
    return labels[role] || role;
  };

  const getRoleColor = (role) => {
    const colors = { admin: "error", purchaser: "primary", viewer: "default" };
    return colors[role] || "default";
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Skeleton variant="rounded" height={200} sx={{ mb: 3 }} />
        <Skeleton variant="rounded" height={300} />
      </Container>
    );
  }

  if (!isAdmin) {
    return (
      <Container maxWidth="sm" sx={{ mt: 10 }}>
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h6" color="error" gutterBottom>
            Acesso restrito
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {error || "Apenas administradores podem acessar esta página."}
          </Typography>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <PeopleIcon color="primary" />
          <Typography variant="h5" fontWeight={600}>
            Usuários
          </Typography>
        </Box>
        <Button
          variant="outlined"
          size="small"
          startIcon={<KeyIcon />}
          onClick={() => navigate("/token-manager")}
        >
          Tokens
        </Button>
      </Box>

      {/* User Form */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Typography variant="subtitle2" color="text.secondary">
            {isEditing ? "Editar usuário" : "Novo usuário"}
          </Typography>
          {isEditing && (
            <IconButton size="small" onClick={resetForm}>
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
        </Box>

        <Box component="form" onSubmit={handleSubmit}>
          <Stack spacing={2}>
            {/* Row 1: Username, Email, Password */}
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                required
                size="small"
                label="Usuário"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                sx={{ flex: 1 }}
              />
              <TextField
                required
                size="small"
                label="Email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
                sx={{ flex: 1 }}
              />
              <TextField
                size="small"
                label="Senha"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleInputChange}
                required={!isEditing}
                placeholder={isEditing ? "Manter atual" : ""}
                sx={{ flex: 1 }}
              />
            </Stack>

            {/* Row 2: Role + System Name */}
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Tipo</InputLabel>
                <Select
                  name="role"
                  label="Tipo"
                  value={formData.role}
                  onChange={handleInputChange}
                >
                  <MenuItem value="admin">Admin</MenuItem>
                  <MenuItem value="purchaser">Comprador</MenuItem>
                  <MenuItem value="viewer">Viewer</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ flex: 1 }}>
                <InputLabel>Nome no Sistema</InputLabel>
                <Select
                  name="system_name"
                  label="Nome no Sistema"
                  value={formData.system_name}
                  onChange={handleInputChange}
                >
                  <MenuItem value="">Nenhum</MenuItem>
                  {purchaserNames.map((name) => (
                    <MenuItem key={name} value={name}>
                      {name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>

            {/* Advanced toggle */}
            <Button
              size="small"
              variant="text"
              onClick={() => setShowAdvanced(!showAdvanced)}
              endIcon={showAdvanced ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              sx={{ alignSelf: "flex-start", textTransform: "none" }}
            >
              {showAdvanced ? "Menos opções" : "Mais opções"}
            </Button>

            <Collapse in={showAdvanced}>
              <Stack spacing={2}>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <TextField
                    size="small"
                    label="Nome Exibição"
                    name="purchaser_name"
                    value={formData.purchaser_name}
                    onChange={handleInputChange}
                    sx={{ flex: 1 }}
                  />
                  <FormControl size="small" sx={{ minWidth: 180 }}>
                    <InputLabel>Tela Inicial</InputLabel>
                    <Select
                      name="initial_screen"
                      label="Tela Inicial"
                      value={formData.initial_screen}
                      onChange={handleInputChange}
                    >
                      {availableScreens.map((s) => (
                        <MenuItem key={s.path} value={s.path}>
                          {s.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Stack>

                <Box sx={{ p: 2, bgcolor: "grey.50", borderRadius: 1 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mb: 1, display: "block" }}
                  >
                    Telas permitidas
                  </Typography>
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    {availableScreens.map((screen) => (
                      <FormControlLabel
                        key={screen.path}
                        control={
                          <Checkbox
                            size="small"
                            checked={formData.allowed_screens.includes(
                              screen.path
                            )}
                            onChange={() => handleScreensChange(screen.path)}
                          />
                        }
                        label={
                          <Typography variant="body2">
                            {screen.label}
                          </Typography>
                        }
                      />
                    ))}
                  </Stack>
                </Box>
              </Stack>
            </Collapse>

            {/* Actions */}
            <Stack direction="row" spacing={1} sx={{ pt: 1 }}>
              <Button
                type="submit"
                variant="contained"
                disableElevation
                startIcon={isEditing ? <SaveIcon /> : <AddIcon />}
              >
                {isEditing ? "Salvar" : "Criar"}
              </Button>
              {isEditing && (
                <Button variant="text" onClick={resetForm}>
                  Cancelar
                </Button>
              )}
            </Stack>
          </Stack>
        </Box>
      </Paper>

      {/* Users Table */}
      <Paper sx={{ borderRadius: 2, overflow: "hidden" }}>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: "grey.50" }}>
                <TableCell sx={{ fontWeight: 600 }}>Usuário</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Email</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Tipo</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Sistema</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  Ações
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    sx={{ textAlign: "center", py: 4, color: "text.secondary" }}
                  >
                    Nenhum usuário cadastrado.
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
                  <TableRow key={user.id} hover>
                    <TableCell>{user.username}</TableCell>
                    <TableCell sx={{ color: "text.secondary" }}>
                      {user.email}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getRoleLabel(user.role)}
                        color={getRoleColor(user.role)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{user.system_name || "—"}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="Editar">
                        <IconButton
                          size="small"
                          onClick={() => handleEditUser(user)}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Excluir">
                        <span>
                          <IconButton
                            size="small"
                            color="error"
                          
                            onClick={() => handleDeleteUser(user.id)}
                            disabled={user.id === 1}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Snackbar
        open={alert.open}
        autoHideDuration={3000}
        onClose={handleCloseAlert}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={handleCloseAlert}
          severity={alert.severity}
          variant="filled"
        >
          {alert.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Register;
