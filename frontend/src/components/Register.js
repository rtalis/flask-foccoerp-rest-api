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
  Grid,
  Snackbar,
  Alert,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
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
    // Check if user is admin
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
          // Fetch data only if admin
          fetchPurchaserNames();
          fetchUsers();
        }
      } catch (err) {
        navigate("/login");
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
      let response;

      if (isEditing && editUserId) {
        // Update existing user
        response = await axios.put(
          `${process.env.REACT_APP_API_URL}/auth/users/${editUserId}`,
          formData,
          { withCredentials: true }
        );

        setAlert({
          open: true,
          message: "Usuário atualizado com sucesso!",
          severity: "success",
        });
      } else {
        // Create new user
        response = await axios.post(
          `${process.env.REACT_APP_API_URL}/auth/register`,
          formData,
          { withCredentials: true }
        );
        if (response.status === 201) {
          setAlert({
            open: true,
            message: "Usuário criado com sucesso!",
            severity: "success",
          });
        } else {
          throw new Error("Falha ao criar usuário");
        }
      }

      // Reset form and refresh users list
      resetForm();
      fetchUsers();
    } catch (error) {
      console.error("Operation failed", error);
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
    setFormData({
      username: user.username,
      email: user.email,
      password: "", // Don't show password
      role: user.role || "viewer",
      purchaser_name: user.purchaser_name || "",
      system_name: user.system_name || "",
      initial_screen: user.initial_screen || "/dashboard",
      allowed_screens: user.allowed_screens || ["/dashboard"],
    });
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Tem certeza que deseja excluir este usuário?")) {
      return;
    }

    try {
      await axios.delete(
        `${process.env.REACT_APP_API_URL}/auth/users/${userId}`,
        { withCredentials: true }
      );

      setAlert({
        open: true,
        message: "Usuário excluído com sucesso!",
        severity: "success",
      });

      fetchUsers();
    } catch (error) {
      console.error("Failed to delete user", error);
      setAlert({
        open: true,
        message: error.response?.data?.error || "Falha ao excluir usuário",
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
    setError("");
  };

  const handleCloseAlert = () => {
    setAlert({ ...alert, open: false });
  };

  if (!isAdmin) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Paper className="p-6 flex flex-col shadow-md rounded-lg">
          <Typography variant="h5" color="error" className="mb-3 font-bold">
            Acesso Restrito
          </Typography>
          <Typography variant="body1">
            {error || "Somente administradores podem acessar esta página."}
          </Typography>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }} className="transition-all">
      <Paper className="p-6 mb-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
        <Typography
          variant="h5"
          className="pb-3 mb-4 border-b-2 border-gray-200 text-gray-800"
        >
          {isEditing ? "Editar Usuário" : "Cadastrar Novo Usuário"}
        </Typography>

        <Box component="form" onSubmit={handleSubmit} className="mt-6">
          <Grid container spacing={3}>
            {/* Username - full width */}
            <Grid item xs={12}>
              <TextField
                required
                fullWidth
                label="Nome de Usuário"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                autoFocus
              />
            </Grid>

            {/* Email and Password - half width on desktop, full on mobile */}
            <Grid item xs={12} md={6}>
              <TextField
                required
                fullWidth
                label="Email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Senha"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleInputChange}
                required={!isEditing}
                helperText={
                  isEditing ? "Deixe em branco para manter a senha atual" : ""
                }
              />
            </Grid>

            {/* User type - full width */}
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Tipo de Usuário</InputLabel>
                <Select
                  name="role"
                  value={formData.role}
                  onChange={handleInputChange}
                >
                  <MenuItem value="admin">Administrador</MenuItem>
                  <MenuItem value="purchaser">Comprador</MenuItem>
                  <MenuItem value="viewer">Visualizador</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Purchaser name and System name - half width on desktop */}
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Nome"
                name="purchaser_name"
                value={formData.purchaser_name}
                onChange={handleInputChange}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Nome no Sistema</InputLabel>
                <Select
                  name="system_name"
                  value={formData.system_name}
                  onChange={handleInputChange}
                >
                  <MenuItem value="">
                    <em>Nenhum</em>
                  </MenuItem>
                  {purchaserNames.map((name) => (
                    <MenuItem key={name} value={name}>
                      {name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Typography variant="caption" className="text-gray-600 mt-1">
                Nome utilizado para filtrar pedidos por comprador
              </Typography>
            </Grid>

            {/* Initial screen - full width */}
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Tela Inicial</InputLabel>
                <Select
                  name="initial_screen"
                  value={formData.initial_screen}
                  onChange={handleInputChange}
                >
                  {availableScreens.map((screen) => (
                    <MenuItem key={screen.path} value={screen.path}>
                      {screen.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          {/* Screens permission checkboxes */}
          <Box className="mt-6 mb-6 p-4 bg-gray-50 rounded-md border border-gray-200">
            <Typography variant="subtitle1" className="mb-3 font-medium">
              Telas Permitidas
            </Typography>
            <Box className="flex flex-wrap">
              {availableScreens.map((screen) => (
                <FormControlLabel
                  key={screen.path}
                  className="w-full md:w-1/2 py-2"
                  control={
                    <Checkbox
                      checked={formData.allowed_screens.includes(screen.path)}
                      onChange={() => handleScreensChange(screen.path)}
                    />
                  }
                  label={screen.label}
                />
              ))}
            </Box>
          </Box>

          <Box className="mt-6 flex flex-col sm:flex-row gap-3">
            <Button
              type="submit"
              variant="contained"
              className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-6"
              startIcon={isEditing ? <SaveIcon /> : <AddIcon />}
            >
              {isEditing ? "Atualizar" : "Cadastrar"}
            </Button>

            {isEditing && (
              <Button
                type="button"
                variant="outlined"
                className="border border-gray-400 text-gray-700 py-2 px-6"
                startIcon={<CancelIcon />}
                onClick={resetForm}
              >
                Cancelar
              </Button>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Users Table */}
      <Paper className="mt-8 p-6 rounded-lg shadow-md overflow-hidden">
        <Typography
          variant="h5"
          className="pb-3 mb-4 border-b-2 border-gray-200 text-gray-800"
        >
          Usuários Cadastrados
        </Typography>

        <TableContainer className="overflow-x-auto">
          <Table>
            <TableHead>
              <TableRow className="bg-gray-100">
                <TableCell className="font-medium">Nome de Usuário</TableCell>
                <TableCell className="font-medium">Email</TableCell>
                <TableCell className="font-medium">Tipo</TableCell>
                <TableCell className="font-medium">Comprador</TableCell>
                <TableCell className="font-medium whitespace-nowrap">
                  Ações
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow
                  key={user.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <TableCell>{user.username}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    {user.role === "admin"
                      ? "Administrador"
                      : user.role === "purchaser"
                      ? "Comprador"
                      : "Visualizador"}
                  </TableCell>
                  <TableCell>
                    {user.purchaser_name || user.system_name || "—"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <IconButton
                      color="primary"
                      onClick={() => handleEditUser(user)}
                      title="Editar"
                      className="p-2"
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      color="error"
                      onClick={() => handleDeleteUser(user.id)}
                      title="Excluir"
                      disabled={user.id === 1} // Prevent deleting the main admin
                      className="p-2"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Snackbar
        open={alert.open}
        autoHideDuration={6000}
        onClose={handleCloseAlert}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={handleCloseAlert}
          severity={alert.severity}
          className="rounded-md"
        >
          {alert.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Register;
