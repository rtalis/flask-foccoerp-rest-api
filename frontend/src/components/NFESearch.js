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
import { ptBR, tr } from "date-fns/locale";
import ManageSearchIcon from "@mui/icons-material/ManageSearch";
import SearchIcon from "@mui/icons-material/Search";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import BusinessIcon from "@mui/icons-material/Business";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import ReceiptIcon from "@mui/icons-material/Receipt";
import SettingsIcon from "@mui/icons-material/Settings";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import TrackedCompanies from "./TrackedCompanies";
import NFEDetails from "./NFEDetails";

const NFESearch = () => {
  // LocalStorage keys
  const NFE_SEARCH_PARAMS_KEY = "nfeSearchParams";

  // Default search parameters
  const DEFAULT_SEARCH_PARAMS = {
    searchTerm: "",
    startDate: null,
    endDate: null,
    searchByNumber: true,
    searchByChave: true,
    searchByFornecedor: false,
    searchByItem: false,
    includeEstimated: true,
    exactTermSearch: true,
  };

  const getStoredSearchParams = () => {
    if (typeof window === "undefined") {
      return { ...DEFAULT_SEARCH_PARAMS };
    }
    try {
      const stored = localStorage.getItem(NFE_SEARCH_PARAMS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          ...DEFAULT_SEARCH_PARAMS,
          ...parsed,
          startDate: parsed.startDate ? new Date(parsed.startDate) : null,
          endDate: parsed.endDate ? new Date(parsed.endDate) : null,
        };
      }
    } catch (error) {
      console.warn("Erro ao recuperar filtros salvos da NFE", error);
    }
    return { ...DEFAULT_SEARCH_PARAMS };
  };

  // Initialize state from localStorage
  const storedParams = getStoredSearchParams();

  // Search state
  const [searchTerm, setSearchTerm] = useState(storedParams.searchTerm);
  const [startDate, setStartDate] = useState(storedParams.startDate);
  const [endDate, setEndDate] = useState(storedParams.endDate);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Company tracking state
  const [trackedCompanies, setTrackedCompanies] = useState([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);

  // Advanced filters
  const [searchByNumber, setSearchByNumber] = useState(
    storedParams.searchByNumber,
  );
  const [searchByChave, setSearchByChave] = useState(
    storedParams.searchByChave,
  );
  const [searchByFornecedor, setSearchByFornecedor] = useState(
    storedParams.searchByFornecedor,
  );
  const [searchByItem, setSearchByItem] = useState(storedParams.searchByItem);
  const [includeEstimated, setIncludeEstimated] = useState(
    storedParams.includeEstimated,
  );
  const [exactTermSearch, setExactTermSearch] = useState(
    storedParams.exactTermSearch,
  );

  // Save search params to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== "undefined") {
      const paramsToSave = {
        searchTerm,
        startDate: startDate ? startDate.toISOString() : null,
        endDate: endDate ? endDate.toISOString() : null,
        searchByNumber,
        searchByChave,
        searchByFornecedor,
        searchByItem,
        includeEstimated,
        exactTermSearch,
      };
      localStorage.setItem(NFE_SEARCH_PARAMS_KEY, JSON.stringify(paramsToSave));
    }
  }, [
    searchTerm,
    startDate,
    endDate,
    searchByNumber,
    searchByChave,
    searchByFornecedor,
    searchByItem,
    includeEstimated,
    exactTermSearch,
  ]);

  const handleSearchByFornecedorChange = (checked) => {
    setSearchByFornecedor(checked);
    if (checked) setExactTermSearch(false);
  };

  const handleSearchByItemChange = (checked) => {
    setSearchByItem(checked);
    if (checked) setExactTermSearch(false);
  };

  const [loadingDanfe, setLoadingDanfe] = useState(null);
  const [expandedNfe, setExpandedNfe] = useState({});
  const [expandedPurchaseOrder, setExpandedPurchaseOrder] = useState({});
  const [showTrackedCompanies, setShowTrackedCompanies] = useState(false);
  const [selectedNfe, setSelectedNfe] = useState(null);
  const [showNfeDetails, setShowNfeDetails] = useState(false);
  const groupPurchasesByOrder = (purchases) => {
    const grouped = {};
    purchases.forEach((purchase) => {
      const key = `${purchase.cod_pedc}-${purchase.cod_emp1}`;
      if (!grouped[key]) {
        grouped[key] = {
          cod_pedc: purchase.cod_pedc,
          cod_emp1: purchase.cod_emp1,
          fornecedor: purchase.fornecedor,
          nfe_numero: purchase.nfe_numero,
          dt_emis: purchase.dt_emis,
          total_pedido: purchase.total_pedido,
          func_nome: purchase.func_nome,
          has_estimated: false,
          items: [],
        };
      }
      if (purchase.is_estimated) {
        grouped[key].has_estimated = true;
      }
      grouped[key].items.push({
        item_descricao: purchase.item_descricao,
        linha: purchase.linha,
        quantidade: purchase.quantidade,
        qtde_atendida: purchase.qtde_atendida,
        qtde_saldo: purchase.qtde_saldo,
        preco_unitario: purchase.preco_unitario,
        total_item: purchase.total_item,
        unidade_medida: purchase.unidade_medida,
        dt_entrega: purchase.dt_entrega,
        is_estimated: purchase.is_estimated,
        match_score: purchase.match_score,
      });
    });
    return Object.values(grouped);
  };

  // Helper function to build active filters description
  const getActiveFiltersDescription = () => {
    const filters = [];
    if (searchByNumber) filters.push("Número NF");
    if (searchByChave) filters.push("Chave");
    if (searchByItem) filters.push("Descrição");
    if (searchByFornecedor) filters.push("Fornecedor");
    if (filters.length === 0) return "";
    if (filters.length === 1) return filters[0];
    return (
      filters.slice(0, -1).join(", ") + " ou " + filters[filters.length - 1]
    );
  };

  const togglePurchaseOrderExpanded = (key) => {
    setExpandedPurchaseOrder((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Load tracked companies on mount
  useEffect(() => {
    loadTrackedCompanies();
  }, []);

  const loadTrackedCompanies = async () => {
    setLoadingCompanies(true);
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/tracked_companies`,
        { withCredentials: true },
      );
      setTrackedCompanies(response.data.companies || []);
    } catch (err) {
      console.error("Error loading companies:", err);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const handleSearch = async () => {
    // Allow search if query is provided OR if date range is set
    if (!searchTerm.trim() && !startDate && !endDate) {
      setError("Digite um termo para buscar ou selecione um período");
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
        exact_term_search: exactTermSearch,
      };

      if (startDate) {
        params.start_date = startDate.toISOString().split("T")[0];
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split("T")[0];
      }

      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/search_nfe`,
        { params, withCredentials: true },
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
    const nfeChave = nfe.chave || nfe.nfe_chave;
    setLoadingDanfe(nfeChave);
    try {
      if (nfeChave) {
        const newWindow = window.open("/danfe-loading.html", "_blank");
        if (!newWindow) {
          alert(
            "Pop-up bloqueado pelo navegador. Por favor, permita pop-ups para este site.",
          );
          return;
        }

        // First ensure the NFE data is stored in the database
        await axios.get(`${process.env.REACT_APP_API_URL}/api/get_nfe_data`, {
          params: { xmlKey: nfeChave },
          withCredentials: true,
        });

        // Then get the PDF
        const pdfResponse = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/get_danfe_pdf`,
          {
            params: { xmlKey: nfeChave },
            withCredentials: true,
          },
        );

        if (!pdfResponse.data) {
          newWindow.document.body.innerHTML =
            '<div style="color:red;">Erro ao carregar o PDF. Dados inválidos recebidos.</div>';
          return;
        }

        let pdfBase64;
        if (typeof pdfResponse.data === "string") {
          pdfBase64 = pdfResponse.data;
        } else if (pdfResponse.data.arquivo) {
          pdfBase64 = pdfResponse.data.arquivo;
        } else if (pdfResponse.data.pdf) {
          pdfBase64 = pdfResponse.data.pdf;
        } else if (pdfResponse.data.content) {
          pdfBase64 = pdfResponse.data.content;
        } else {
          const possibleBase64 = Object.entries(pdfResponse.data)
            .filter(
              ([key, value]) => typeof value === "string" && value.length > 100,
            )
            .sort((a, b) => b[1].length - a[1].length)[0];

          if (possibleBase64) {
            pdfBase64 = possibleBase64[1];
          } else {
            newWindow.document.body.innerHTML =
              '<div style="color:red;">Erro ao carregar o PDF. Formato de resposta não reconhecido.</div>';
            return;
          }
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

        const number = nfe.numero || nfe.num_nf || nfe.number || nfe.numero_nf;
        newWindow.postMessage(
          { type: "pdfBlobUrl", url: blobUrl, number },
          "*",
        );
      } else {
        setError("DANFE não encontrada para NF " + nfe.numero);
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
      "$1.$2.$3/$4-$5",
    );
  };

  const handleRestoreDefaults = () => {
    setSearchTerm(DEFAULT_SEARCH_PARAMS.searchTerm);
    setStartDate(DEFAULT_SEARCH_PARAMS.startDate);
    setEndDate(DEFAULT_SEARCH_PARAMS.endDate);
    setSearchByNumber(DEFAULT_SEARCH_PARAMS.searchByNumber);
    setSearchByChave(DEFAULT_SEARCH_PARAMS.searchByChave);
    setSearchByFornecedor(DEFAULT_SEARCH_PARAMS.searchByFornecedor);
    setSearchByItem(DEFAULT_SEARCH_PARAMS.searchByItem);
    setIncludeEstimated(DEFAULT_SEARCH_PARAMS.includeEstimated);
    setExactTermSearch(DEFAULT_SEARCH_PARAMS.exactTermSearch);
    setResults(null);
    setError(null);
    // Clear localStorage
    if (typeof window !== "undefined") {
      localStorage.removeItem(NFE_SEARCH_PARAMS_KEY);
    }
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
      name: "searchByChave",
      label: "Chave de Acesso",
      checked: searchByChave,
      onChange: setSearchByChave,
    },
    {
      name: "searchByItem",
      label: "Descrição do Item",
      checked: searchByItem,
      onChange: handleSearchByItemChange,
    },
    {
      name: "searchByFornecedor",
      label: "Fornecedor",
      checked: searchByFornecedor,
      onChange: handleSearchByFornecedorChange,
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
                        trackedCompanies.slice(0, 3).map((company) => {
                          const fullName =
                            company.name ||
                            company.fantasy_name ||
                            formatCNPJ(company.cnpj);
                          const shortName =
                            fullName.length > 20
                              ? fullName.substring(0, 20) + "..."
                              : fullName;
                          const label = `${
                            company.cod_emp1 ? company.cod_emp1 + " - " : ""
                          }${shortName}`;
                          const fullLabel = `${
                            company.cod_emp1 ? company.cod_emp1 + " - " : ""
                          }${fullName}`;
                          return (
                            <Tooltip key={company.id} title={fullLabel}>
                              <Chip
                                label={label}
                                size="small"
                                sx={{
                                  bgcolor: "rgba(255,255,255,0.2)",
                                  color: "#fff",
                                  fontSize: "0.7rem",
                                  height: 22,
                                  maxWidth: 180,
                                }}
                              />
                            </Tooltip>
                          );
                        })
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
                    <Checkbox
                      checked={exactTermSearch}
                      onChange={(e) => setExactTermSearch(e.target.checked)}
                      size="small"
                    />
                  }
                  label={<Typography variant="body2">Termo Exato</Typography>}
                  sx={{ mr: 2 }}
                />
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
                  {results.purchase_orders?.filter(
                    (po) =>
                      po.match_type === "linked" ||
                      po.match_type === "estimated",
                  ).length > 0 && (
                    <Typography
                      component="span"
                      variant="body2"
                      color="text.secondary"
                      sx={{ ml: 1 }}
                    >
                      •{" "}
                      {
                        results.purchase_orders.filter(
                          (po) =>
                            po.match_type === "linked" ||
                            po.match_type === "estimated",
                        ).length
                      }{" "}
                      pedidos vinculados
                    </Typography>
                  )}
                  {results.unlinked_purchase_orders?.length > 0 && (
                    <Typography
                      component="span"
                      variant="body2"
                      color="warning.main"
                      sx={{ ml: 1 }}
                    >
                      • {results.unlinked_purchase_orders.length} pedidos sem
                      NFE correspondente
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
                          Pedidos
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
                            <TableCell>
                              <Tooltip title={nfe.fornecedor || "-"}>
                                <Typography
                                  sx={{
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
                              {(() => {
                                const allPurchases = [
                                  ...(nfe.linked_purchases || []),
                                  ...(nfe.estimated_purchases || []),
                                ];
                                const uniqueOrders = [
                                  ...new Set(
                                    allPurchases.map((p) => p.cod_pedc),
                                  ),
                                ];
                                const hasEstimated =
                                  (nfe.estimated_purchases || []).length > 0;

                                if (uniqueOrders.length === 0) return "-";

                                return (
                                  <Box
                                    sx={{
                                      display: "flex",
                                      flexWrap: "wrap",
                                      gap: 0.5,
                                      justifyContent: "center",
                                    }}
                                  >
                                    {uniqueOrders
                                      .slice(0, 3)
                                      .map((orderId, idx) => (
                                        <Chip
                                          key={idx}
                                          size="small"
                                          label={orderId}
                                          color="primary"
                                          variant="outlined"
                                          sx={{ fontSize: "0.7rem" }}
                                        />
                                      ))}
                                    {uniqueOrders.length > 3 && (
                                      <Tooltip
                                        title={uniqueOrders.slice(3).join(", ")}
                                      >
                                        <Chip
                                          size="small"
                                          label={`+${uniqueOrders.length - 3}`}
                                          color="default"
                                          variant="outlined"
                                          sx={{ fontSize: "0.7rem" }}
                                        />
                                      </Tooltip>
                                    )}
                                    {hasEstimated && (
                                      <Tooltip title="Contém matches estimados">
                                        <AutoAwesomeIcon
                                          sx={{
                                            fontSize: 16,
                                            color: "secondary.main",
                                            ml: 0.5,
                                          }}
                                        />
                                      </Tooltip>
                                    )}
                                  </Box>
                                );
                              })()}
                            </TableCell>
                            <TableCell align="center">
                              <Box
                                sx={{
                                  display: "flex",
                                  gap: 0.5,
                                  justifyContent: "center",
                                }}
                              >
                                <Tooltip title="Ver Detalhes">
                                  <IconButton
                                    size="small"
                                    color="info"
                                    onClick={() => {
                                      setSelectedNfe(nfe);
                                      setShowNfeDetails(true);
                                    }}
                                  >
                                    <InfoOutlinedIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
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
                              </Box>
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
                                    // Combine linked_purchases and estimated_purchases from NFE
                                    const linkedPurchases =
                                      nfe.linked_purchases || [];
                                    const estimatedPurchases =
                                      nfe.estimated_purchases || [];
                                    const allPurchases = [
                                      ...linkedPurchases,
                                      ...estimatedPurchases,
                                    ];

                                    if (allPurchases.length === 0) {
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

                                    // Group purchases by order
                                    const groupedOrders =
                                      groupPurchasesByOrder(allPurchases);

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
                                          {groupedOrders.length} pedido(s),{" "}
                                          {allPurchases.length} item(s))
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
                                              <TableCell padding="checkbox" />
                                              <TableCell>Pedido</TableCell>
                                              <TableCell>Empresa</TableCell>
                                              <TableCell>
                                                Data Emissão
                                              </TableCell>
                                              <TableCell>Fornecedor</TableCell>
                                              <TableCell>Comprador</TableCell>
                                              <TableCell align="right">
                                                Total Pedido
                                              </TableCell>
                                              <TableCell align="center">
                                                Itens
                                              </TableCell>
                                            </TableRow>
                                          </TableHead>
                                          <TableBody>
                                            {groupedOrders.map((order) => {
                                              const orderKey = `nfe-${nfe.id}-${order.cod_pedc}-${order.cod_emp1}`;
                                              return (
                                                <React.Fragment key={orderKey}>
                                                  <TableRow
                                                    hover
                                                    sx={{
                                                      bgcolor:
                                                        expandedPurchaseOrder[
                                                          orderKey
                                                        ]
                                                          ? "#e8f5e9"
                                                          : "inherit",
                                                      "&:hover": {
                                                        bgcolor: "#e8f5e9",
                                                      },
                                                    }}
                                                  >
                                                    <TableCell padding="checkbox">
                                                      <IconButton
                                                        size="small"
                                                        onClick={() =>
                                                          togglePurchaseOrderExpanded(
                                                            orderKey,
                                                          )
                                                        }
                                                      >
                                                        {expandedPurchaseOrder[
                                                          orderKey
                                                        ] ? (
                                                          <KeyboardArrowUpIcon fontSize="small" />
                                                        ) : (
                                                          <KeyboardArrowDownIcon fontSize="small" />
                                                        )}
                                                      </IconButton>
                                                    </TableCell>
                                                    <TableCell>
                                                      <Box
                                                        sx={{
                                                          display: "flex",
                                                          alignItems: "center",
                                                          gap: 0.5,
                                                        }}
                                                      >
                                                        <Typography
                                                          fontWeight={600}
                                                        >
                                                          {order.cod_pedc}
                                                        </Typography>
                                                        {order.has_estimated && (
                                                          <Tooltip title="Contém itens com match estimado">
                                                            <AutoAwesomeIcon
                                                              sx={{
                                                                fontSize: 16,
                                                                color:
                                                                  "secondary.main",
                                                              }}
                                                            />
                                                          </Tooltip>
                                                        )}
                                                      </Box>
                                                    </TableCell>
                                                    <TableCell>
                                                      {order.cod_emp1 || "-"}
                                                    </TableCell>
                                                    <TableCell>
                                                      {order.dt_emis
                                                        ? formatDate(
                                                            order.dt_emis,
                                                          )
                                                        : "-"}
                                                    </TableCell>
                                                    <TableCell>
                                                      <Tooltip
                                                        title={
                                                          order.fornecedor ||
                                                          "-"
                                                        }
                                                      >
                                                        <Typography
                                                          sx={{
                                                            textAlign: "center",
                                                            maxWidth: 200,
                                                            overflow: "hidden",
                                                            textOverflow:
                                                              "ellipsis",
                                                            whiteSpace:
                                                              "nowrap",
                                                          }}
                                                        >
                                                          {order.fornecedor ||
                                                            "-"}
                                                        </Typography>
                                                      </Tooltip>
                                                    </TableCell>
                                                    <TableCell>
                                                      {order.func_nome || "-"}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                      {order.total_pedido
                                                        ? formatCurrency(
                                                            order.total_pedido,
                                                          )
                                                        : "-"}
                                                    </TableCell>
                                                    <TableCell align="center">
                                                      <Chip
                                                        size="small"
                                                        label={
                                                          order.items.length
                                                        }
                                                        color="primary"
                                                        variant="outlined"
                                                      />
                                                    </TableCell>
                                                  </TableRow>
                                                  {/* Nested Items Row */}
                                                  <TableRow>
                                                    <TableCell
                                                      colSpan={8}
                                                      sx={{ py: 0, border: 0 }}
                                                    >
                                                      <Collapse
                                                        in={
                                                          expandedPurchaseOrder[
                                                            orderKey
                                                          ]
                                                        }
                                                        timeout="auto"
                                                        unmountOnExit
                                                      >
                                                        <Box
                                                          sx={{
                                                            py: 1,
                                                            pl: 6,
                                                            pr: 2,
                                                            bgcolor: "#f5f5f5",
                                                          }}
                                                        >
                                                          <Typography
                                                            variant="caption"
                                                            color="text.secondary"
                                                            sx={{
                                                              fontWeight: 600,
                                                              mb: 1,
                                                              display: "block",
                                                            }}
                                                          >
                                                            Itens do Pedido:
                                                          </Typography>
                                                          <Table
                                                            size="small"
                                                            sx={{
                                                              bgcolor: "#fff",
                                                              borderRadius: 1,
                                                            }}
                                                          >
                                                            <TableHead>
                                                              <TableRow
                                                                sx={{
                                                                  bgcolor:
                                                                    "#fafafa",
                                                                }}
                                                              >
                                                                <TableCell
                                                                  sx={{
                                                                    width: 50,
                                                                  }}
                                                                >
                                                                  Linha
                                                                </TableCell>
                                                                <TableCell>
                                                                  Descrição
                                                                </TableCell>
                                                                <TableCell align="right">
                                                                  Qtde
                                                                </TableCell>
                                                                <TableCell align="center">
                                                                  UN
                                                                </TableCell>
                                                                <TableCell align="right">
                                                                  Preço Unit.
                                                                </TableCell>
                                                                <TableCell align="right">
                                                                  Total
                                                                </TableCell>
                                                                <TableCell align="right">
                                                                  Atendida
                                                                </TableCell>

                                                                <TableCell>
                                                                  Entrega
                                                                </TableCell>
                                                              </TableRow>
                                                            </TableHead>
                                                            <TableBody>
                                                              {order.items.map(
                                                                (item, idx) => (
                                                                  <TableRow
                                                                    key={idx}
                                                                  >
                                                                    <TableCell
                                                                      sx={{
                                                                        width: 50,
                                                                      }}
                                                                    >
                                                                      <Box
                                                                        sx={{
                                                                          display:
                                                                            "flex",
                                                                          alignItems:
                                                                            "center",
                                                                          gap: 0.5,
                                                                        }}
                                                                      >
                                                                        {item.linha ||
                                                                          "-"}
                                                                        {item.is_estimated && (
                                                                          <Tooltip
                                                                            title={`Match estimado (${
                                                                              item.match_score
                                                                                ? Math.round(
                                                                                    item.match_score,
                                                                                  ) +
                                                                                  "%"
                                                                                : ""
                                                                            })`}
                                                                          >
                                                                            <AutoAwesomeIcon
                                                                              sx={{
                                                                                fontSize: 14,
                                                                                color:
                                                                                  "secondary.main",
                                                                              }}
                                                                            />
                                                                          </Tooltip>
                                                                        )}
                                                                      </Box>
                                                                    </TableCell>
                                                                    <TableCell>
                                                                      <Tooltip
                                                                        title={
                                                                          item.item_descricao ||
                                                                          "-"
                                                                        }
                                                                      >
                                                                        <Typography
                                                                          sx={{
                                                                            maxWidth: 250,
                                                                            overflow:
                                                                              "hidden",
                                                                            textOverflow:
                                                                              "ellipsis",
                                                                            whiteSpace:
                                                                              "nowrap",
                                                                          }}
                                                                        >
                                                                          {item.item_descricao ||
                                                                            "-"}
                                                                        </Typography>
                                                                      </Tooltip>
                                                                    </TableCell>
                                                                    <TableCell align="right">
                                                                      {item.quantidade !=
                                                                      null
                                                                        ? item.quantidade.toLocaleString(
                                                                            "pt-BR",
                                                                          )
                                                                        : "-"}
                                                                    </TableCell>
                                                                    <TableCell align="center">
                                                                      {item.unidade_medida ||
                                                                        "-"}
                                                                    </TableCell>
                                                                    <TableCell align="right">
                                                                      {item.preco_unitario !=
                                                                      null
                                                                        ? formatCurrency(
                                                                            item.preco_unitario,
                                                                          )
                                                                        : "-"}
                                                                    </TableCell>
                                                                    <TableCell align="right">
                                                                      {item.total_item !=
                                                                      null
                                                                        ? formatCurrency(
                                                                            item.total_item,
                                                                          )
                                                                        : "-"}
                                                                    </TableCell>
                                                                    <TableCell align="right">
                                                                      {item.qtde_atendida !=
                                                                      null
                                                                        ? item.qtde_atendida.toLocaleString(
                                                                            "pt-BR",
                                                                          )
                                                                        : "-"}
                                                                    </TableCell>

                                                                    <TableCell>
                                                                      {item.dt_entrega
                                                                        ? formatDate(
                                                                            item.dt_entrega,
                                                                          )
                                                                        : "-"}
                                                                    </TableCell>
                                                                  </TableRow>
                                                                ),
                                                              )}
                                                            </TableBody>
                                                          </Table>
                                                        </Box>
                                                      </Collapse>
                                                    </TableCell>
                                                  </TableRow>
                                                </React.Fragment>
                                              );
                                            })}
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

              {/* Unlinked Purchase Orders Section */}
              {results.unlinked_purchase_orders &&
                results.unlinked_purchase_orders.length > 0 && (
                  <Paper
                    elevation={0}
                    sx={{
                      mb: 3,
                      borderRadius: 3,
                      border: "1px solid",
                      borderColor: "warning.main",
                      bgcolor: "#fff8e1",
                    }}
                  >
                    <Box sx={{ p: 2 }}>
                      {(() => {
                        const groupedUnlinked = groupPurchasesByOrder(
                          results.unlinked_purchase_orders,
                        );
                        return (
                          <>
                            <Typography
                              variant="subtitle1"
                              fontWeight={600}
                              color="warning.dark"
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 1,
                                mb: 2,
                              }}
                            >
                              <ReceiptIcon color="warning" />
                              Pedidos contendo "{results.query}" mas sem NFE
                              correspondente ({groupedUnlinked.length}{" "}
                              pedido(s),{" "}
                              {results.unlinked_purchase_orders.length} item(s))
                            </Typography>
                            <Typography
                              variant="body2"
                              color="text.secondary"
                              sx={{ mb: 2 }}
                            >
                              Estes pedidos têm {getActiveFiltersDescription()}{" "}
                              contendo "{results.query}" registrado, mas não foi
                              encontrada uma NFE com fornecedor correspondente
                              no banco de dados.
                            </Typography>
                            <Table
                              size="small"
                              sx={{ bgcolor: "#fff", borderRadius: 1 }}
                            >
                              <TableHead>
                                <TableRow sx={{ bgcolor: "#f5f7fa" }}>
                                  <TableCell padding="checkbox" />
                                  <TableCell>Pedido</TableCell>
                                  <TableCell>Empresa</TableCell>
                                  <TableCell>Data Emissão</TableCell>
                                  <TableCell>Fornecedor</TableCell>
                                  <TableCell>Comprador</TableCell>
                                  <TableCell align="right">
                                    Total Pedido
                                  </TableCell>
                                  <TableCell>NF Registrada</TableCell>
                                  <TableCell align="center">Itens</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {groupedUnlinked.map((order) => {
                                  const orderKey = `unlinked-${order.cod_pedc}-${order.cod_emp1}`;
                                  return (
                                    <React.Fragment key={orderKey}>
                                      <TableRow
                                        hover
                                        sx={{
                                          bgcolor: expandedPurchaseOrder[
                                            orderKey
                                          ]
                                            ? "#fff3e0"
                                            : "inherit",
                                          "&:hover": { bgcolor: "#fff3e0" },
                                        }}
                                      >
                                        <TableCell padding="checkbox">
                                          <IconButton
                                            size="small"
                                            onClick={() =>
                                              togglePurchaseOrderExpanded(
                                                orderKey,
                                              )
                                            }
                                          >
                                            {expandedPurchaseOrder[orderKey] ? (
                                              <KeyboardArrowUpIcon fontSize="small" />
                                            ) : (
                                              <KeyboardArrowDownIcon fontSize="small" />
                                            )}
                                          </IconButton>
                                        </TableCell>
                                        <TableCell>
                                          <Typography fontWeight={600}>
                                            {order.cod_pedc}
                                          </Typography>
                                        </TableCell>
                                        <TableCell>
                                          {order.cod_emp1 || "-"}
                                        </TableCell>
                                        <TableCell>
                                          {order.dt_emis
                                            ? formatDate(order.dt_emis)
                                            : "-"}
                                        </TableCell>
                                        <TableCell>
                                          <Tooltip
                                            title={order.fornecedor || "-"}
                                          >
                                            <Typography
                                              sx={{
                                                maxWidth: 150,
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                              }}
                                            >
                                              {order.fornecedor || "-"}
                                            </Typography>
                                          </Tooltip>
                                        </TableCell>
                                        <TableCell>
                                          {order.func_nome || "-"}
                                        </TableCell>
                                        <TableCell align="right">
                                          {order.total_pedido
                                            ? formatCurrency(order.total_pedido)
                                            : "-"}
                                        </TableCell>
                                        <TableCell>
                                          <Chip
                                            size="small"
                                            label={order.nfe_numero || "-"}
                                            color="warning"
                                            variant="outlined"
                                          />
                                        </TableCell>
                                        <TableCell align="center">
                                          <Chip
                                            size="small"
                                            label={order.items.length}
                                            color="warning"
                                            variant="outlined"
                                          />
                                        </TableCell>
                                      </TableRow>
                                      {/* Nested Items Row */}
                                      <TableRow>
                                        <TableCell
                                          colSpan={9}
                                          sx={{ py: 0, border: 0 }}
                                        >
                                          <Collapse
                                            in={expandedPurchaseOrder[orderKey]}
                                            timeout="auto"
                                            unmountOnExit
                                          >
                                            <Box
                                              sx={{
                                                py: 1,
                                                pl: 6,
                                                pr: 2,
                                                bgcolor: "#fffde7",
                                              }}
                                            >
                                              <Typography
                                                variant="caption"
                                                color="text.secondary"
                                                sx={{
                                                  fontWeight: 600,
                                                  mb: 1,
                                                  display: "block",
                                                }}
                                              >
                                                Itens do Pedido:
                                              </Typography>
                                              <Table
                                                size="small"
                                                sx={{
                                                  bgcolor: "#fff",
                                                  borderRadius: 1,
                                                }}
                                              >
                                                <TableHead>
                                                  <TableRow
                                                    sx={{ bgcolor: "#fafafa" }}
                                                  >
                                                    <TableCell
                                                      sx={{ width: 50 }}
                                                    >
                                                      Linha
                                                    </TableCell>
                                                    <TableCell>
                                                      Descrição
                                                    </TableCell>
                                                    <TableCell align="right">
                                                      Qtde
                                                    </TableCell>
                                                    <TableCell align="center">
                                                      UN
                                                    </TableCell>
                                                    <TableCell align="right">
                                                      Preço Unit.
                                                    </TableCell>
                                                    <TableCell align="right">
                                                      Total
                                                    </TableCell>
                                                    <TableCell align="right">
                                                      Atendida
                                                    </TableCell>
                                                    <TableCell align="right">
                                                      Saldo
                                                    </TableCell>
                                                    <TableCell>
                                                      Entrega
                                                    </TableCell>
                                                  </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                  {order.items.map(
                                                    (item, idx) => (
                                                      <TableRow key={idx}>
                                                        <TableCell
                                                          sx={{ width: 50 }}
                                                        >
                                                          {item.linha || "-"}
                                                        </TableCell>
                                                        <TableCell>
                                                          <Tooltip
                                                            title={
                                                              item.item_descricao ||
                                                              "-"
                                                            }
                                                          >
                                                            <Typography
                                                              sx={{
                                                                maxWidth: 250,
                                                                overflow:
                                                                  "hidden",
                                                                textOverflow:
                                                                  "ellipsis",
                                                                whiteSpace:
                                                                  "nowrap",
                                                              }}
                                                            >
                                                              {item.item_descricao ||
                                                                "-"}
                                                            </Typography>
                                                          </Tooltip>
                                                        </TableCell>
                                                        <TableCell align="right">
                                                          {item.quantidade !=
                                                          null
                                                            ? item.quantidade.toLocaleString(
                                                                "pt-BR",
                                                              )
                                                            : "-"}
                                                        </TableCell>
                                                        <TableCell align="center">
                                                          {item.unidade_medida ||
                                                            "-"}
                                                        </TableCell>
                                                        <TableCell align="right">
                                                          {item.preco_unitario !=
                                                          null
                                                            ? formatCurrency(
                                                                item.preco_unitario,
                                                              )
                                                            : "-"}
                                                        </TableCell>
                                                        <TableCell align="right">
                                                          {item.total_item !=
                                                          null
                                                            ? formatCurrency(
                                                                item.total_item,
                                                              )
                                                            : "-"}
                                                        </TableCell>
                                                        <TableCell align="right">
                                                          {item.qtde_atendida !=
                                                          null
                                                            ? item.qtde_atendida.toLocaleString(
                                                                "pt-BR",
                                                              )
                                                            : "-"}
                                                        </TableCell>
                                                        <TableCell align="right">
                                                          {item.qtde_saldo !=
                                                          null ? (
                                                            <Chip
                                                              size="small"
                                                              label={item.qtde_saldo.toLocaleString(
                                                                "pt-BR",
                                                              )}
                                                              color={
                                                                item.qtde_saldo >
                                                                0
                                                                  ? "warning"
                                                                  : "success"
                                                              }
                                                              variant="outlined"
                                                            />
                                                          ) : (
                                                            "-"
                                                          )}
                                                        </TableCell>
                                                        <TableCell>
                                                          {item.dt_entrega
                                                            ? formatDate(
                                                                item.dt_entrega,
                                                              )
                                                            : "-"}
                                                        </TableCell>
                                                      </TableRow>
                                                    ),
                                                  )}
                                                </TableBody>
                                              </Table>
                                            </Box>
                                          </Collapse>
                                        </TableCell>
                                      </TableRow>
                                    </React.Fragment>
                                  );
                                })}
                              </TableBody>
                            </Table>
                          </>
                        );
                      })()}
                    </Box>
                  </Paper>
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

      {/* NFE Details Dialog */}
      <NFEDetails
        open={showNfeDetails}
        onClose={() => {
          setShowNfeDetails(false);
          setSelectedNfe(null);
        }}
        nfeChave={selectedNfe?.chave}
        nfeNumero={selectedNfe?.numero}
      />
    </LocalizationProvider>
  );
};

export default NFESearch;
