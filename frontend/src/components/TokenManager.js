import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  IconButton,
  Tooltip,
  Stack,
  Skeleton,
  InputAdornment,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  ArrowBack as ArrowBackIcon,
  ContentCopy as ContentCopyIcon,
  Key as KeyIcon,
  Add as AddIcon,
  Block as BlockIcon,
  AccessTime as AccessTimeIcon,
} from "@mui/icons-material";

const EXPIRATION_PRESETS = [
  { value: 60, label: "1 hora" },
  { value: 60 * 12, label: "12 horas" },
  { value: 60 * 24, label: "1 dia" },
  { value: 60 * 24 * 7, label: "7 dias" },
  { value: 60 * 24 * 30, label: "30 dias" },
  { value: 60 * 24 * 90, label: "90 dias" },
  { value: 60 * 24 * 365, label: "1 ano" },
];

const TokenManager = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [users, setUsers] = useState([]);
  const [tokens, setTokens] = useState([]);
  const [tokensLoading, setTokensLoading] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [expiresMinutes, setExpiresMinutes] = useState(60 * 24 * 7);
  const [submitting, setSubmitting] = useState(false);
  const [alert, setAlert] = useState({
    open: false,
    message: "",
    severity: "success",
  });

  const apiBase = process.env.REACT_APP_API_URL;

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${apiBase}/auth/users`, {
        withCredentials: true,
      });
      setUsers(response.data);
      if (!selectedUserId && response.data.length > 0) {
        setSelectedUserId(response.data[0].id);
      }
    } catch (error) {
      console.error("Erro ao carregar usuários", error);
      setAlert({
        open: true,
        message: "Não foi possível carregar a lista de usuários.",
        severity: "error",
      });
    }
  };

  const fetchTokens = async () => {
    setTokensLoading(true);
    try {
      const response = await axios.get(`${apiBase}/auth/tokens`, {
        withCredentials: true,
      });
      setTokens(response.data);
    } catch (error) {
      console.error("Erro ao carregar tokens", error);
      setAlert({
        open: true,
        message: "Não foi possível carregar os tokens emitidos.",
        severity: "error",
      });
    } finally {
      setTokensLoading(false);
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const me = await axios.get(`${apiBase}/auth/me`, {
          withCredentials: true,
        });
        if (me.data.role !== "admin") {
          setIsAdmin(false);
          setAlert({
            open: true,
            message: "Somente administradores podem gerenciar tokens.",
            severity: "error",
          });
          return;
        }
        setIsAdmin(true);
        await Promise.all([fetchUsers(), fetchTokens()]);
      } catch (error) {
        setIsAdmin(false);
        navigate("/login");
      } finally {
        setLoading(false);
      }
    };

    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const minutesToHuman = (minutes) => {
    if (!minutes) return "—";
    if (minutes < 60) return `${minutes}min`;
    const hours = minutes / 60;
    if (hours < 24) return `${Math.round(hours)}h`;
    const days = hours / 24;
    return `${Math.round(days)}d`;
  };

  const handleGenerate = async () => {
    if (!selectedUserId) {
      setAlert({
        open: true,
        message: "Selecione um usuário.",
        severity: "warning",
      });
      return;
    }

    setSubmitting(true);
    try {
      const response = await axios.post(
        `${apiBase}/auth/users/${selectedUserId}/token`,
        { expires_in: expiresMinutes },
        { withCredentials: true }
      );
      await fetchTokens();
      try {
        await navigator.clipboard.writeText(response.data.token);
        setAlert({
          open: true,
          message: "Token gerado e copiado!",
          severity: "success",
        });
      } catch (copyError) {
        setAlert({
          open: true,
          message: "Token gerado com sucesso.",
          severity: "success",
        });
      }
    } catch (error) {
      console.error("Falha ao gerar token", error);
      setAlert({
        open: true,
        message: error.response?.data?.error || "Erro ao gerar token.",
        severity: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyToken = async (tokenValue) => {
    if (!tokenValue) return;
    try {
      await navigator.clipboard.writeText(tokenValue);
      setAlert({ open: true, message: "Copiado!", severity: "success" });
    } catch (error) {
      setAlert({ open: true, message: "Falha ao copiar.", severity: "error" });
    }
  };

  const handleDisableToken = async (tokenId) => {
    if (!tokenId) return;
    if (!window.confirm("Desativar este token?")) return;

    try {
      await axios.post(
        `${apiBase}/auth/tokens/${tokenId}/disable`,
        {},
        { withCredentials: true }
      );
      setAlert({
        open: true,
        message: "Token desativado.",
        severity: "success",
      });
      await fetchTokens();
    } catch (error) {
      setAlert({
        open: true,
        message: error.response?.data?.error || "Erro ao desativar.",
        severity: "error",
      });
    }
  };

  const formatDateTime = (value) => {
    if (!value) return "—";
    return new Date(value).toLocaleString();
  };

  const statusInfo = (token) => {
    const disabled = Boolean(token.disabled_at);
    const now = Date.now();
    const expiresAt = token.expires_at
      ? new Date(token.expires_at).getTime()
      : null;
    const expired = expiresAt ? expiresAt <= now : false;

    if (disabled) {
      return { label: "Desativado", color: "default" };
    }
    if (expired) {
      return { label: "Expirado", color: "warning" };
    }
    return { label: "Ativo", color: "success" };
  };

  const handleCloseAlert = () => {
    setAlert((prev) => ({ ...prev, open: false }));
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 6 }}>
        <Skeleton variant="rounded" height={180} sx={{ mb: 3 }} />
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
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Apenas administradores podem gerenciar tokens.
          </Typography>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate("/dashboard")}
          >
            Voltar
          </Button>
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
          <KeyIcon color="primary" />
          <Typography variant="h5" fontWeight={600}>
            Tokens de API
          </Typography>
        </Box>
        <Button
          variant="text"
          size="small"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/register")}
        >
          Usuários
        </Button>
      </Box>

      {/* Create Token Card */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
          Novo token
        </Typography>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={2}
          alignItems="flex-end"
        >
          <FormControl size="small" sx={{ minWidth: 200, flex: 1 }}>
            <InputLabel>Usuário</InputLabel>
            <Select
              label="Usuário"
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
            >
              {users.map((user) => (
                <MenuItem key={user.id} value={user.id}>
                  {user.username}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Validade</InputLabel>
            <Select
              label="Validade"
              value={expiresMinutes}
              onChange={(e) => setExpiresMinutes(e.target.value)}
              startAdornment={
                <InputAdornment position="start">
                  <AccessTimeIcon fontSize="small" color="action" />
                </InputAdornment>
              }
            >
              {EXPIRATION_PRESETS.map((p) => (
                <MenuItem key={p.value} value={p.value}>
                  {p.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            disableElevation
            startIcon={<AddIcon />}
            onClick={handleGenerate}
            disabled={!selectedUserId || submitting}
            sx={{ height: 40 }}
          >
            Gerar
          </Button>
        </Stack>
      </Paper>

      {/* Tokens Table */}
      <Paper sx={{ borderRadius: 2, overflow: "hidden" }}>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: "grey.50" }}>
                <TableCell sx={{ fontWeight: 600 }}>Usuário</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Token</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Validade</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Expira</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  Ações
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tokensLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={6}>
                      <Skeleton variant="text" />
                    </TableCell>
                  </TableRow>
                ))
              ) : tokens.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    sx={{ textAlign: "center", py: 4, color: "text.secondary" }}
                  >
                    Nenhum token emitido.
                  </TableCell>
                </TableRow>
              ) : (
                tokens.map((token) => {
                  const status = statusInfo(token);
                  const truncated =
                    token.token?.length > 24
                      ? `${token.token.slice(0, 24)}…`
                      : token.token;
                  const canDisable = status.label === "Ativo";

                  return (
                    <TableRow key={token.id} hover>
                      <TableCell>{token.user?.username || "—"}</TableCell>
                      <TableCell>
                        <Tooltip title="Copiar">
                          <Box
                            component="span"
                            onClick={() => handleCopyToken(token.token)}
                            sx={{
                              fontFamily: "monospace",
                              fontSize: "0.8rem",
                              cursor: "pointer",
                              "&:hover": { color: "primary.main" },
                            }}
                          >
                            {truncated}
                          </Box>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        {minutesToHuman(token.duration_minutes)}
                      </TableCell>
                      <TableCell>{formatDateTime(token.expires_at)}</TableCell>
                      <TableCell>
                        <Chip
                          label={status.label}
                          color={status.color}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Copiar">
                          <IconButton
                            size="small"
                            onClick={() => handleCopyToken(token.token)}
                          >
                            <ContentCopyIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Desativar">
                          <span>
                            <IconButton
                              size="small"
                              onClick={() => handleDisableToken(token.id)}
                              disabled={!canDisable}
                              color="error"
                            >
                              <BlockIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })
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

export default TokenManager;
