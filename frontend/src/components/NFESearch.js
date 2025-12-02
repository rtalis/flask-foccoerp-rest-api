import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  CircularProgress,
  InputAdornment,
  Tooltip,
  Alert,
  Switch,
  FormControlLabel,
  Checkbox,
  Collapse,
  Skeleton,
} from "@mui/material";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { ptBR } from "date-fns/locale";
import ManageSearchIcon from "@mui/icons-material/ManageSearch";
import SearchIcon from "@mui/icons-material/Search";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import BusinessIcon from "@mui/icons-material/Business";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import ReceiptIcon from "@mui/icons-material/Receipt";
import SettingsIcon from "@mui/icons-material/Settings";
import TrackedCompanies from "./TrackedCompanies";

const NFESearch = () => {
  // Search state
  const [searchTerm, setSearchTerm] = useState("");
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Company tracking state
  const [trackedCompanies, setTrackedCompanies] = useState([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);

  // Advanced filters
  const [searchByNumber, setSearchByNumber] = useState(true);
  const [searchByChave, setSearchByChave] = useState(true);
  const [searchByFornecedor, setSearchByFornecedor] = useState(true);
  const [searchByItem, setSearchByItem] = useState(true);
  const [includeEstimated, setIncludeEstimated] = useState(true);

  // DANFE loading state
  const [loadingDanfe, setLoadingDanfe] = useState(null);

  // Expanded NFEs
  const [expandedNfe, setExpandedNfe] = useState({});

  // Tracked Companies Dialog
  const [showTrackedCompanies, setShowTrackedCompanies] = useState(false);

  // Load tracked companies on mount
  useEffect(() => {
    loadTrackedCompanies();
  }, []);

  const loadTrackedCompanies = async () => {
    setLoadingCompanies(true);
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/tracked_companies`,
        { withCredentials: true }
      );
      setTrackedCompanies(response.data.companies || []);
    } catch (err) {
      console.error("Error loading companies:", err);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) {
      setError("Digite um termo para buscar");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const params = {
        query: searchTerm.trim(),
        search_by_number: searchByNumber,
        search_by_chave: searchByChave,
        search_by_fornecedor: searchByFornecedor,
        search_by_item: searchByItem,
        include_estimated: includeEstimated,
      };

      if (startDate) {
        params.start_date = startDate.toISOString().split("T")[0];
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split("T")[0];
      }

      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/search_nfe`,
        { params, withCredentials: true }
      );

      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Erro ao buscar NFE");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleViewDanfe = async (nfe) => {
    const nfeNumber = nfe.numero || nfe.nfe_numero;
    setLoadingDanfe(nfeNumber);

    try {
      const nfeResponse = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/get_nfe_by_number`,
        {
          params: { num_nf: nfeNumber },
          withCredentials: true,
        }
      );

      if (
        nfeResponse.data &&
        nfeResponse.data.found &&
        nfeResponse.data.chave
      ) {
        const newWindow = window.open("", "_blank");
        if (!newWindow) {
          alert("Pop-up bloqueado pelo navegador.");
          return;
        }
        newWindow.document.write(
          "<html><head><title>Carregando DANFE...</title></head>" +
            "<body style='font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;'>" +
            "<div>Carregando DANFE...</div></body></html>"
        );

        const pdfResponse = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/get_danfe_pdf`,
          {
            params: { xmlKey: nfeResponse.data.chave },
            withCredentials: true,
          }
        );

        let pdfBase64 = pdfResponse.data;
        if (typeof pdfResponse.data === "object") {
          pdfBase64 =
            pdfResponse.data.arquivo ||
            pdfResponse.data.pdf ||
            pdfResponse.data.content;
        }

        const byteCharacters = atob(pdfBase64);
        const byteArrays = [];
        for (let i = 0; i < byteCharacters.length; i += 512) {
          const slice = byteCharacters.slice(i, i + 512);
          const byteNumbers = new Array(slice.length);
          for (let j = 0; j < slice.length; j++) {
            byteNumbers[j] = slice.charCodeAt(j);
          }
          byteArrays.push(new Uint8Array(byteNumbers));
        }
        const blob = new Blob(byteArrays, { type: "application/pdf" });
        const blobUrl = URL.createObjectURL(blob);

        newWindow.location.href = blobUrl;
      } else {
        setError("DANFE não encontrada para NF " + nfeNumber);
      }
    } catch (err) {
      console.error("Error loading DANFE:", err);
      setError("Erro ao carregar DANFE");
    } finally {
      setLoadingDanfe(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString("pt-BR");
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(value);
  };

  const formatCNPJ = (cnpj) => {
    if (!cnpj) return "-";
    const cleaned = cnpj.replace(/\D/g, "");
    if (cleaned.length !== 14) return cnpj;
    return cleaned.replace(
      /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
      "$1.$2.$3/$4-$5"
    );
  };

  const handleRestoreDefaults = () => {
    setSearchTerm("");
    setStartDate(null);
    setEndDate(null);
    setSearchByNumber(true);
    setSearchByChave(true);
    setSearchByFornecedor(true);
    setSearchByItem(true);
    setIncludeEstimated(true);
    setResults(null);
    setError(null);
  };

  const toggleNfeExpanded = (nfeId) => {
    setExpandedNfe((prev) => ({
      ...prev,
      [nfeId]: !prev[nfeId],
    }));
  };

  const searchFieldOptions = [
    {
      name: "searchByNumber",
      label: "Número da NF",
      checked: searchByNumber,
      onChange: setSearchByNumber,
    },
    {
      name: "searchByItem",
      label: "Descrição do Item",
      checked: searchByItem,
      onChange: setSearchByItem,
    },
    {
      name: "searchByFornecedor",
      label: "Fornecedor",
      checked: searchByFornecedor,
      onChange: setSearchByFornecedor,
    },
    {
      name: "searchByChave",
      label: "Chave de Acesso",
      checked: searchByChave,
      onChange: setSearchByChave,
    },
  ];

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ptBR}>
      <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fa" }}>
        {/* Header Section */}
        <Paper
          elevation={0}
          sx={{
            p: 3,
            mx: { xs: 2, md: 3 },
            mt: { xs: 2, md: 3 },
            mb: 3,
            background: "linear-gradient(135deg, #1a1f2e 0%, #2d3548 100%)",
            borderRadius: 3,
            color: "#fff",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 2,
            }}
          >
            <Box>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1 }}
              >
                <ManageSearchIcon sx={{ fontSize: 32 }} />
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  Buscar Notas Fiscais
                </Typography>
              </Box>
              <Typography
                variant="body2"
                sx={{ color: "rgba(255,255,255,0.7)", maxWidth: 450 }}
              >
                Pesquise por número, descrição de item, fornecedor ou chave de
                acesso.
              </Typography>
            </Box>

            {/* Tracked Companies Info */}
            <Paper
              elevation={0}
              sx={{
                px: 2.5,
                py: 1.5,
                bgcolor: "rgba(255,255,255,0.15)",
                borderRadius: 2,
                border: "1px solid rgba(255,255,255,0.2)",
                minWidth: 200,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <BusinessIcon sx={{ fontSize: 20, color: "#fff" }} />
                <Box sx={{ flexGrow: 1 }}>
                  <Typography
                    variant="caption"
                    sx={{ color: "rgba(255,255,255,0.8)", display: "block" }}
                  >
                    Empresas Rastreadas
                  </Typography>
                  {loadingCompanies ? (
                    <CircularProgress size={16} sx={{ color: "#fff" }} />
                  ) : (
                    <Box
                      sx={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: 0.5,
                        mt: 0.5,
                      }}
                    >
                      {trackedCompanies.length === 0 ? (
                        <Typography variant="body2" sx={{ color: "#fff" }}>
                          Nenhuma empresa
                        </Typography>
                      ) : (
                        trackedCompanies.slice(0, 3).map((company) => (
                          <Chip
                            key={company.id}
                            label={
                              company.name ||
                              company.fantasy_name ||
                              formatCNPJ(company.cnpj)
                            }
                            size="small"
                            sx={{
                              bgcolor: "rgba(255,255,255,0.2)",
                              color: "#fff",
                              fontSize: "0.7rem",
                              height: 22,
                            }}
                          />
                        ))
                      )}
                      {trackedCompanies.length > 3 && (
                        <Chip
                          label={"+" + (trackedCompanies.length - 3)}
                          size="small"
                          sx={{
                            bgcolor: "rgba(255,255,255,0.3)",
                            color: "#fff",
                            fontSize: "0.7rem",
                            height: 22,
                          }}
                        />
                      )}
                    </Box>
                  )}
                </Box>
                <Tooltip title="Configurar empresas">
                  <IconButton
                    size="small"
                    onClick={() => setShowTrackedCompanies(true)}
                    sx={{
                      color: "rgba(255,255,255,0.7)",
                      "&:hover": {
                        color: "#fff",
                        bgcolor: "rgba(255,255,255,0.1)",
                      },
                    }}
                  >
                    <SettingsIcon sx={{ fontSize: 18 }} />
                  </IconButton>
                </Tooltip>
              </Box>
            </Paper>
          </Box>
        </Paper>

        <Box sx={{ px: { xs: 2, md: 3 }, pb: 3 }}>
          {/* Error Alert */}
          {error && (
            <Alert
              severity="error"
              onClose={() => setError(null)}
              sx={{ mb: 2 }}
            >
              {error}
            </Alert>
          )}

          {/* Search Box */}
          <Paper
            elevation={0}
            sx={{
              p: 3,
              mb: 3,
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            <Box
              sx={{
                display: "flex",
                gap: 2,
                alignItems: "center",
                flexWrap: "wrap",
                mb: 3,
              }}
            >
              <TextField
                sx={{ flexGrow: 1, minWidth: 300 }}
                label="Buscar NFE"
                placeholder="Ex.: número da NF, descrição do item, fornecedor..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={handleKeyPress}
                variant="outlined"
                size="small"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon color="action" />
                    </InputAdornment>
                  ),
                }}
              />
              <DatePicker
                label="Data Inicial"
                value={startDate}
                onChange={setStartDate}
                slotProps={{
                  textField: { size: "small", sx: { minWidth: 150 } },
                }}
              />
              <DatePicker
                label="Data Final"
                value={endDate}
                onChange={setEndDate}
                slotProps={{
                  textField: { size: "small", sx: { minWidth: 150 } },
                }}
              />
              <Button
                variant="contained"
                onClick={handleSearch}
                disabled={loading}
                startIcon={
                  loading ? <CircularProgress size={20} /> : <SearchIcon />
                }
                sx={{
                  px: 3,
                  py: 1,
                  textTransform: "none",
                  fontWeight: 600,
                  bgcolor: "#1a1f2e",
                  "&:hover": { bgcolor: "#2d3548" },
                }}
              >
                Buscar
              </Button>
            </Box>

            {/* Quick Filters */}
            <Box sx={{ mb: 2 }}>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                sx={{ mb: 1 }}
              >
                Pesquisar por...
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 1,
                  alignItems: "center",
                }}
              >
                {searchFieldOptions.map((field) => (
                  <FormControlLabel
                    key={field.name}
                    control={
                      <Checkbox
                        checked={field.checked}
                        onChange={(e) => field.onChange(e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2">{field.label}</Typography>
                    }
                    sx={{ mr: 2 }}
                  />
                ))}
                <FormControlLabel
                  control={
                    <Switch
                      checked={includeEstimated}
                      onChange={(e) => setIncludeEstimated(e.target.checked)}
                      size="small"
                    />
                  }
                  label={
                    <Box
                      sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                    >
                      <AutoAwesomeIcon fontSize="small" color="secondary" />
                      <Typography variant="body2">Matches estimados</Typography>
                    </Box>
                  }
                />
                <Button
                  variant="text"
                  color="inherit"
                  size="small"
                  onClick={handleRestoreDefaults}
                  sx={{ textTransform: "none", ml: "auto" }}
                >
                  Limpar filtros
                </Button>
              </Box>
            </Box>
          </Paper>

          {/* Loading State */}
          {loading && (
            <Box sx={{ mb: 3 }}>
              {[1, 2, 3, 4, 5].map((i) => (
                <Paper
                  key={i}
                  elevation={0}
                  sx={{
                    mb: 2,
                    overflow: "hidden",
                    borderRadius: 2,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Box
                    sx={{
                      bgcolor: "#e3f2fd",
                      p: 2,
                      display: "flex",
                      alignItems: "center",
                      gap: 2,
                    }}
                  >
                    <Skeleton
                      variant="circular"
                      width={24}
                      height={24}
                      animation="wave"
                    />
                    <Skeleton
                      variant="text"
                      width="80%"
                      height={28}
                      animation="wave"
                    />
                  </Box>
                  <Box sx={{ p: 2 }}>
                    {[1, 2].map((j) => (
                      <Box
                        key={j}
                        sx={{
                          display: "flex",
                          gap: 2,
                          py: 1,
                          borderBottom: j < 2 ? "1px solid #f0f0f0" : "none",
                        }}
                      >
                        <Skeleton variant="text" width={80} animation="wave" />
                        <Skeleton variant="text" width={60} animation="wave" />
                        <Skeleton variant="text" width={200} animation="wave" />
                        <Skeleton variant="text" width={80} animation="wave" />
                      </Box>
                    ))}
                  </Box>
                </Paper>
              ))}
            </Box>
          )}

          {/* Results */}
          {!loading && results && (
            <Box>
              {/* Results Summary */}
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 2,
                }}
              >
                <Typography variant="subtitle1" fontWeight={600}>
                  {results.nfes?.length || 0} NFEs encontradas
                  {results.purchase_orders?.length > 0 && (
                    <Typography
                      component="span"
                      variant="body2"
                      color="text.secondary"
                      sx={{ ml: 1 }}
                    >
                      • {results.purchase_orders.length} pedidos vinculados
                    </Typography>
                  )}
                </Typography>
              </Box>

              {/* NFEs Table */}
              {results.nfes && results.nfes.length > 0 && (
                <TableContainer
                  component={Paper}
                  elevation={0}
                  sx={{
                    mb: 3,
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ bgcolor: "#f5f7fa" }}>
                        <TableCell padding="checkbox" />
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Número
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Data Emissão
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Fornecedor
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          CNPJ
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Valor Total
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Itens
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Ações
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {results.nfes.map((nfe) => (
                        <React.Fragment key={nfe.id || nfe.chave}>
                          <TableRow
                            hover
                            sx={{
                              bgcolor: expandedNfe[nfe.id]
                                ? "#e3f2fd"
                                : "inherit",
                              "&:hover": { bgcolor: "#e3f2fd" },
                            }}
                          >
                            <TableCell padding="checkbox">
                              <IconButton
                                size="small"
                                onClick={() => toggleNfeExpanded(nfe.id)}
                              >
                                {expandedNfe[nfe.id] ? (
                                  <KeyboardArrowUpIcon />
                                ) : (
                                  <KeyboardArrowDownIcon />
                                )}
                              </IconButton>
                            </TableCell>
                            <TableCell align="center">
                              <Typography fontWeight={600}>
                                {nfe.numero}
                              </Typography>
                            </TableCell>
                            <TableCell align="center">
                              {formatDate(nfe.data_emissao)}
                            </TableCell>
                            <TableCell align="center">
                              <Tooltip title={nfe.fornecedor || "-"}>
                                <Typography
                                  sx={{
                                    maxWidth: 200,
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                  }}
                                >
                                  {nfe.fornecedor || "-"}
                                </Typography>
                              </Tooltip>
                            </TableCell>
                            <TableCell align="center">
                              {formatCNPJ(nfe.cnpj)}
                            </TableCell>
                            <TableCell align="center">
                              {formatCurrency(nfe.valor_total)}
                            </TableCell>
                            <TableCell align="center">
                              {nfe.matched_items &&
                              nfe.matched_items.length > 0 ? (
                                <Tooltip title={nfe.matched_items.join(", ")}>
                                  <Chip
                                    size="small"
                                    label={
                                      nfe.matched_items.length +
                                      " encontrado(s)"
                                    }
                                    color="info"
                                    variant="outlined"
                                  />
                                </Tooltip>
                              ) : (
                                "-"
                              )}
                            </TableCell>
                            <TableCell align="center">
                              <Tooltip title="Visualizar DANFE">
                                <IconButton
                                  size="small"
                                  color="primary"
                                  onClick={() => handleViewDanfe(nfe)}
                                  disabled={loadingDanfe === nfe.numero}
                                >
                                  {loadingDanfe === nfe.numero ? (
                                    <CircularProgress size={18} />
                                  ) : (
                                    <PictureAsPdfIcon fontSize="small" />
                                  )}
                                </IconButton>
                              </Tooltip>
                            </TableCell>
                          </TableRow>
                          {/* Expanded Row - Linked Purchase Orders */}
                          <TableRow>
                            <TableCell colSpan={8} sx={{ py: 0, border: 0 }}>
                              <Collapse
                                in={expandedNfe[nfe.id]}
                                timeout="auto"
                                unmountOnExit
                              >
                                <Box sx={{ p: 2, bgcolor: "#fafafa" }}>
                                  {(() => {
                                    const relatedPOs =
                                      results.purchase_orders?.filter(
                                        (po) => po.nfe_numero === nfe.numero
                                      ) || [];

                                    if (relatedPOs.length === 0) {
                                      return (
                                        <Typography
                                          variant="body2"
                                          color="text.secondary"
                                        >
                                          Nenhum pedido de compra vinculado a
                                          esta NFE.
                                        </Typography>
                                      );
                                    }

                                    return (
                                      <Box>
                                        <Typography
                                          variant="subtitle2"
                                          gutterBottom
                                          sx={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 1,
                                          }}
                                        >
                                          <ReceiptIcon
                                            fontSize="small"
                                            color="primary"
                                          />
                                          Pedidos de Compra Vinculados (
                                          {relatedPOs.length})
                                        </Typography>
                                        <Table
                                          size="small"
                                          sx={{
                                            bgcolor: "#fff",
                                            borderRadius: 1,
                                          }}
                                        >
                                          <TableHead>
                                            <TableRow>
                                              <TableCell>Pedido</TableCell>
                                              <TableCell>Data</TableCell>
                                              <TableCell>Fornecedor</TableCell>
                                              <TableCell>Item</TableCell>
                                              <TableCell align="right">
                                                Valor
                                              </TableCell>
                                              <TableCell>Tipo</TableCell>
                                            </TableRow>
                                          </TableHead>
                                          <TableBody>
                                            {relatedPOs.map((po, idx) => (
                                              <TableRow
                                                key={po.cod_pedc + "-" + idx}
                                              >
                                                <TableCell>
                                                  <Typography fontWeight={500}>
                                                    {po.cod_pedc}
                                                  </Typography>
                                                </TableCell>
                                                <TableCell>
                                                  {formatDate(po.dt_emis)}
                                                </TableCell>
                                                <TableCell>
                                                  {po.fornecedor || "-"}
                                                </TableCell>
                                                <TableCell>
                                                  <Tooltip
                                                    title={
                                                      po.item_descricao || "-"
                                                    }
                                                  >
                                                    <Typography
                                                      variant="body2"
                                                      sx={{
                                                        maxWidth: 200,
                                                        overflow: "hidden",
                                                        textOverflow:
                                                          "ellipsis",
                                                        whiteSpace: "nowrap",
                                                      }}
                                                    >
                                                      {po.item_descricao || "-"}
                                                    </Typography>
                                                  </Tooltip>
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(po.valor)}
                                                </TableCell>
                                                <TableCell>
                                                  {po.match_type ===
                                                  "estimated" ? (
                                                    <Chip
                                                      size="small"
                                                      icon={<AutoAwesomeIcon />}
                                                      label={
                                                        (po.match_score?.toFixed(
                                                          0
                                                        ) || 0) + "%"
                                                      }
                                                      color="secondary"
                                                      variant="outlined"
                                                    />
                                                  ) : (
                                                    <Chip
                                                      size="small"
                                                      label="Vinculado"
                                                      color="success"
                                                      variant="outlined"
                                                    />
                                                  )}
                                                </TableCell>
                                              </TableRow>
                                            ))}
                                          </TableBody>
                                        </Table>
                                      </Box>
                                    );
                                  })()}
                                </Box>
                              </Collapse>
                            </TableCell>
                          </TableRow>
                        </React.Fragment>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}

              {/* No results message */}
              {(!results.nfes || results.nfes.length === 0) && (
                <Paper
                  elevation={0}
                  sx={{
                    p: 4,
                    textAlign: "center",
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <ManageSearchIcon
                    sx={{ fontSize: 64, color: "text.disabled", mb: 2 }}
                  />
                  <Typography variant="h6" color="text.secondary">
                    Nenhum resultado encontrado
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Tente ajustar os filtros ou termos de busca
                  </Typography>
                </Paper>
              )}
            </Box>
          )}

          {/* Initial state - no search yet */}
          {!loading && !results && (
            <Paper
              elevation={0}
              sx={{
                p: 4,
                textAlign: "center",
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <ManageSearchIcon
                sx={{ fontSize: 64, color: "text.disabled", mb: 2 }}
              />
              <Typography variant="h6" color="text.secondary">
                Digite um termo para buscar
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pesquise por número da NF, descrição do item, fornecedor ou
                chave de acesso
              </Typography>
            </Paper>
          )}
        </Box>
      </Box>

      {/* Tracked Companies Dialog */}
      <TrackedCompanies
        open={showTrackedCompanies}
        onClose={() => {
          setShowTrackedCompanies(false);
          loadTrackedCompanies(); // Refresh companies after closing
        }}
      />
    </LocalizationProvider>
  );
};

export default NFESearch;
