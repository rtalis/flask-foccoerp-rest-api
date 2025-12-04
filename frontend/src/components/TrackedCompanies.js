import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  LinearProgress,
  Chip,
  Alert,
  CircularProgress,
  Tooltip,
  Card,
  CardContent,
  Divider,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Sync as SyncIcon,
  Business as BusinessIcon,
  Close as CloseIcon,
  Receipt as ReceiptIcon,
  CalendarMonth as CalendarIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from "@mui/icons-material";

const TrackedCompanies = ({ open, onClose }) => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Add company dialog
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newCompany, setNewCompany] = useState({ name: "", cnpj: "", cod_emp1: "" });
  const [addingCompany, setAddingCompany] = useState(false);
  
  // Sync dialog
  const [showSyncDialog, setShowSyncDialog] = useState(false);
  const [syncCompany, setSyncCompany] = useState(null);
  const [syncStartDate, setSyncStartDate] = useState("");
  const [syncEndDate, setSyncEndDate] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(null);
  const [syncResults, setSyncResults] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [currentChunk, setCurrentChunk] = useState(0);

  const fetchCompanies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/tracked_companies`,
        { withCredentials: true }
      );
      const companiesData = response.data.companies || [];
      
      // Fetch NFE count for each company
      const companiesWithCount = await Promise.all(
        companiesData.map(async (company) => {
          try {
            const countRes = await axios.get(
              `${process.env.REACT_APP_API_URL}/api/tracked_companies/${company.id}/nfe_count`,
              { withCredentials: true }
            );
            return { ...company, nfe_count: countRes.data.nfe_count || 0 };
          } catch {
            return { ...company, nfe_count: 0 };
          }
        })
      );
      
      setCompanies(companiesWithCount);
    } catch (err) {
      setError("Erro ao carregar empresas rastreadas");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      fetchCompanies();
    }
  }, [open, fetchCompanies]);

  const handleAddCompany = async () => {
    if (!newCompany.cnpj || !newCompany.cod_emp1) return;
    
    setAddingCompany(true);
    try {
      await axios.post(
        `${process.env.REACT_APP_API_URL}/api/tracked_companies`,
        newCompany,
        { withCredentials: true }
      );
      setNewCompany({ name: "", cnpj: "", cod_emp1: "" });
      setShowAddDialog(false);
      fetchCompanies();
    } catch (err) {
      setError(err.response?.data?.error || "Erro ao adicionar empresa");
    } finally {
      setAddingCompany(false);
    }
  };

  const handleDeleteCompany = async (companyId) => {
    if (!window.confirm("Tem certeza que deseja remover esta empresa?")) return;
    
    try {
      await axios.delete(
        `${process.env.REACT_APP_API_URL}/api/tracked_companies/${companyId}`,
        { withCredentials: true }
      );
      fetchCompanies();
    } catch (err) {
      setError("Erro ao remover empresa");
    }
  };

  const openSyncDialog = (company) => {
    setSyncCompany(company);
    // Default to last 6 months
    const today = new Date();
    const sixMonthsAgo = new Date(today);
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
    
    setSyncStartDate(sixMonthsAgo.toISOString().split("T")[0]);
    setSyncEndDate(today.toISOString().split("T")[0]);
    setSyncProgress(null);
    setSyncResults([]);
    setShowSyncDialog(true);
  };

  const generateChunks = (startDate, endDate) => {
    const chunks = [];
    const start = new Date(startDate);
    const end = new Date(endDate);
    const chunkDays = 15;
    
    let currentStart = new Date(start);
    while (currentStart < end) {
      const currentEnd = new Date(currentStart);
      currentEnd.setDate(currentEnd.getDate() + chunkDays);
      
      if (currentEnd > end) {
        currentEnd.setTime(end.getTime());
      }
      
      chunks.push({
        start: currentStart.toISOString().split("T")[0],
        end: currentEnd.toISOString().split("T")[0],
      });
      
      currentStart = new Date(currentEnd);
      currentStart.setDate(currentStart.getDate() + 1);
    }
    
    return chunks;
  };

  const handleStartSync = async () => {
    if (!syncCompany || !syncStartDate || !syncEndDate) return;
    
    setSyncing(true);
    setSyncProgress({ status: "starting", message: "Iniciando sincronização..." });
    setSyncResults([]);
    
    const chunks = generateChunks(syncStartDate, syncEndDate);
    setTotalChunks(chunks.length);
    setCurrentChunk(0);
    
    const results = [];
    
    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i];
      setCurrentChunk(i + 1);
      setSyncProgress({
        status: "syncing",
        message: `Sincronizando período ${chunk.start} a ${chunk.end}...`,
        progress: ((i + 1) / chunks.length) * 100,
      });
      
      try {
        const response = await axios.post(
          `${process.env.REACT_APP_API_URL}/api/tracked_companies/${syncCompany.id}/sync_chunk`,
          {
            chunk_start: chunk.start,
            chunk_end: chunk.end,
          },
          { withCredentials: true }
        );
        
        results.push({
          ...chunk,
          ...response.data,
        });
        setSyncResults([...results]);
      } catch (err) {
        results.push({
          ...chunk,
          status: "error",
          error: err.message,
        });
        setSyncResults([...results]);
      }
      
      // Small delay between chunks to avoid overwhelming the API
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    
    setSyncing(false);
    setSyncProgress({
      status: "completed",
      message: "Sincronização concluída!",
      progress: 100,
    });
    
    // Refresh company list to update NFE count
    fetchCompanies();
  };

  const formatCNPJ = (cnpj) => {
    if (!cnpj) return "";
    const clean = cnpj.replace(/\D/g, "");
    return clean.replace(
      /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
      "$1.$2.$3/$4-$5"
    );
  };

  const getTotalSyncedNFEs = () => {
    return syncResults.reduce((acc, r) => acc + (r.new_nfes || 0), 0);
  };

  const getTotalFoundNFEs = () => {
    return syncResults.reduce((acc, r) => acc + (r.found || 0), 0);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 3, minHeight: "70vh" },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          bgcolor: "#1a1f2e",
          color: "#fff",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <BusinessIcon />
          <Typography variant="h6" fontWeight={600}>
            Empresas Rastreadas
          </Typography>
        </Box>
        <IconButton onClick={onClose} sx={{ color: "#fff" }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 3,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            Gerencie as empresas para sincronização automática de NFEs do SIEG.
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setShowAddDialog(true)}
            sx={{
              bgcolor: "#1a1f2e",
              "&:hover": { bgcolor: "#2d3548" },
              textTransform: "none",
            }}
          >
            Adicionar Empresa
          </Button>
        </Box>

        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : companies.length === 0 ? (
          <Paper
            elevation={0}
            sx={{
              p: 6,
              textAlign: "center",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 3,
            }}
          >
            <BusinessIcon
              sx={{ fontSize: 48, color: "text.disabled", mb: 2 }}
            />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Nenhuma empresa cadastrada
            </Typography>
            <Typography variant="body2" color="text.disabled">
              Adicione empresas para iniciar o rastreamento de NFEs
            </Typography>
          </Paper>
        ) : (
          <TableContainer
            component={Paper}
            elevation={0}
            sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2 }}
          >
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: "#f5f7fa" }}>
                  <TableCell sx={{ fontWeight: 600 }}>Cód. emp</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Empresa</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>CNPJ</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="center">
                    NFEs no Sistema
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">
                    Ações
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {companies.map((company) => (
                  <TableRow
                    key={company.id}
                    sx={{ "&:hover": { bgcolor: "#f5f7fa" } }}
                  >
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace" fontWeight={500} >
                      {company.cod_emp1}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box>
                        <Typography variant="body1" fontWeight={500}>
                          {company.name}
                        </Typography>
                        {company.fantasy_name && (
                          <Typography variant="caption" color="text.secondary">
                            {company.fantasy_name}
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {formatCNPJ(company.cnpj)}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        icon={<ReceiptIcon />}
                        label={company.nfe_count || 0}
                        size="small"
                        color={company.nfe_count > 0 ? "primary" : "default"}
                        variant={company.nfe_count > 0 ? "filled" : "outlined"}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Sincronizar NFEs">
                        <IconButton
                          color="primary"
                          onClick={() => openSyncDialog(company)}
                        >
                          <SyncIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Remover empresa">
                        <IconButton
                          color="error"
                          onClick={() => handleDeleteCompany(company.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>

      {/* Add Company Dialog */}
      <Dialog
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Adicionar Empresa</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Código empresa"
              value={newCompany.cod_emp1}
              onChange={(e) =>
                setNewCompany({ ...newCompany, cod_emp1: e.target.value })
              }
              fullWidth
              placeholder="Ex: 1"
              helperText="Código da empresa no Focco ERP"
            />
            <TextField
              label="Nome da Empresa"
              value={newCompany.name}
              onChange={(e) =>
                setNewCompany({ ...newCompany, name: e.target.value })
              }
              fullWidth
            />
            <TextField
              label="CNPJ"
              value={newCompany.cnpj}
              onChange={(e) =>
                setNewCompany({ ...newCompany, cnpj: e.target.value })
              }
              fullWidth
              placeholder="00.000.000/0000-00"
              helperText="Apenas números ou formato completo"
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setShowAddDialog(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={handleAddCompany}
            disabled={addingCompany || !newCompany.cnpj || !newCompany.cod_emp1}
            sx={{ bgcolor: "#1a1f2e", "&:hover": { bgcolor: "#2d3548" } }}
          >
            {addingCompany ? <CircularProgress size={20} /> : "Adicionar"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Sync Dialog */}
      <Dialog
        open={showSyncDialog}
        onClose={() => !syncing && setShowSyncDialog(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle sx={{ bgcolor: "#1a1f2e", color: "#fff" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <SyncIcon />
            <Typography variant="h6">
              Sincronizar NFEs - {syncCompany?.name}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 3 }}>
          {!syncing && !syncProgress?.status && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Selecione o período para baixar as NFEs do SIEG. O download será
                feito em blocos de 15 dias.
              </Typography>

              <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
                <TextField
                  label="Data Inicial"
                  type="date"
                  value={syncStartDate}
                  onChange={(e) => setSyncStartDate(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                />
                <TextField
                  label="Data Final"
                  type="date"
                  value={syncEndDate}
                  onChange={(e) => setSyncEndDate(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                />
              </Box>

              {syncStartDate && syncEndDate && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="body2">
                    Serão processados{" "}
                    <strong>
                      {generateChunks(syncStartDate, syncEndDate).length}
                    </strong>{" "}
                    blocos de 15 dias.
                  </Typography>
                </Alert>
              )}
            </Box>
          )}

          {(syncing || syncProgress?.status) && (
            <Box>
              <Box sx={{ mb: 3 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Typography variant="body2" fontWeight={500}>
                    {syncProgress?.message}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {currentChunk} / {totalChunks}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={syncProgress?.progress || 0}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>

              {syncProgress?.status === "completed" && (
                <Card
                  elevation={0}
                  sx={{
                    mb: 3,
                    bgcolor: "#e8f5e9",
                    border: "1px solid #c8e6c9",
                  }}
                >
                  <CardContent>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        mb: 1,
                      }}
                    >
                      <CheckCircleIcon color="success" />
                      <Typography variant="h6" color="success.main">
                        Sincronização Concluída
                      </Typography>
                    </Box>
                    <Typography variant="body2">
                      <strong>{getTotalFoundNFEs()}</strong> NFEs encontradas •{" "}
                      <strong>{getTotalSyncedNFEs()}</strong> novas NFEs
                      adicionadas
                    </Typography>
                  </CardContent>
                </Card>
              )}

              {syncResults.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Detalhes por período:
                  </Typography>
                  <TableContainer
                    component={Paper}
                    elevation={0}
                    sx={{
                      maxHeight: 300,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell>Período</TableCell>
                          <TableCell align="center">Encontradas</TableCell>
                          <TableCell align="center">Novas</TableCell>
                          <TableCell align="center">Já Existiam</TableCell>
                          <TableCell align="center">Status</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {syncResults.map((result, idx) => (
                          <TableRow key={idx}>
                            <TableCell>
                              <Typography variant="body2">
                                {result.start} a {result.end}
                              </Typography>
                            </TableCell>
                            <TableCell align="center">
                              {result.found || 0}
                            </TableCell>
                            <TableCell align="center">
                              <Chip
                                label={result.new_nfes || 0}
                                size="small"
                                color={result.new_nfes > 0 ? "success" : "default"}
                              />
                            </TableCell>
                            <TableCell align="center">
                              {result.already_existed || 0}
                            </TableCell>
                            <TableCell align="center">
                              {result.status === "success" ? (
                                <CheckCircleIcon
                                  fontSize="small"
                                  color="success"
                                />
                              ) : result.status === "error" ? (
                                <Tooltip title={result.error}>
                                  <ErrorIcon fontSize="small" color="error" />
                                </Tooltip>
                              ) : (
                                <CircularProgress size={16} />
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button
            onClick={() => setShowSyncDialog(false)}
            disabled={syncing}
          >
            {syncProgress?.status === "completed" ? "Fechar" : "Cancelar"}
          </Button>
          {!syncProgress?.status && (
            <Button
              variant="contained"
              onClick={handleStartSync}
              disabled={syncing || !syncStartDate || !syncEndDate}
              startIcon={
                syncing ? <CircularProgress size={20} /> : <SyncIcon />
              }
              sx={{ bgcolor: "#1a1f2e", "&:hover": { bgcolor: "#2d3548" } }}
            >
              {syncing ? "Sincronizando..." : "Iniciar Sincronização"}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};

export default TrackedCompanies;
