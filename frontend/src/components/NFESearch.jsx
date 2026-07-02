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
  Skeleton,
  SvgIcon,
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
import SettingsIcon from "@mui/icons-material/Settings";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import TrackedCompanies from "./TrackedCompanies";
import NFEDetails from "./NFEDetails";
import { openPurchaseOrderReport } from "../utils/openPurchaseOrderReport";

const PedIcon = (props) => (
  <SvgIcon {...props} viewBox="0 0 22 22">
    <path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z M11.5 9.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5z M12.5 7h3v1h-1.5v1.5h1.5v1h-1.5v1.5h1.5v1h-3z M21.5 11.5c0 .83-.67 1.5-1.5 1.5h-2.5V7H20c.83 0 1.5.67 1.5 1.5z M9 9.5h1v-1H9z M19 11.5h1v-3h-1z M4 6H2v14c0 1.1.9 2 2 2h14v-2H4z" />
  </SvgIcon>
);

// Highlighter component that mimics the green text highlight from the UI design
const HighlightedText = ({ text, highlight }) => {
  if (!highlight || !text) return <>{text}</>;
  const terms = highlight.trim().split(/\s+/).filter(t => t.length > 0);
  if (terms.length === 0) return <>{text}</>;

  const regex = new RegExp(`(${terms.join('|')})`, 'gi');
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) => {
        const isMatch = terms.some(t => t.toLowerCase() === part.toLowerCase());
        return isMatch ? (
          <Box component="span" key={i} sx={{ bgcolor: '#bbf7d0', color: '#166534', px: 0.5, borderRadius: 0.5, fontWeight: 600 }}>
            {part}
          </Box>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </>
  );
};

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
  const [searchByNumber, setSearchByNumber] = useState(storedParams.searchByNumber);
  const [searchByChave, setSearchByChave] = useState(storedParams.searchByChave);
  const [searchByFornecedor, setSearchByFornecedor] = useState(storedParams.searchByFornecedor);
  const [searchByItem, setSearchByItem] = useState(storedParams.searchByItem);
  const [includeEstimated, setIncludeEstimated] = useState(storedParams.includeEstimated);
  const [exactTermSearch, setExactTermSearch] = useState(storedParams.exactTermSearch);

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
  const [showTrackedCompanies, setShowTrackedCompanies] = useState(false);
  const [selectedNfe, setSelectedNfe] = useState(null);
  const [showNfeDetails, setShowNfeDetails] = useState(false);

  const [userCapabilities, setUserCapabilities] = useState([]);
  const canViewFinancials = userCapabilities.includes('view_financials');

  useEffect(() => {
    let isMounted = true;
    const stored = localStorage.getItem('userCapabilities');
    if (stored) {
      try {
        setUserCapabilities(JSON.parse(stored));
      } catch (error) {
        setUserCapabilities(['view_financials', 'view_nfes']);
      }
    } else {
      setUserCapabilities(['view_financials', 'view_nfes']);
    }

    const refreshCapabilities = async () => {
      try {
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/auth/me`, { withCredentials: true });
        if (!isMounted) return;
        const nextCapabilities = response.data?.capabilities || [];
        setUserCapabilities(nextCapabilities);
        localStorage.setItem('userCapabilities', JSON.stringify(nextCapabilities));
      } catch (error) {
        console.error("Error refreshing user capabilities:", error);
      }
    };

    refreshCapabilities();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    loadTrackedCompanies();
  }, []);

  const loadTrackedCompanies = async () => {
    setLoadingCompanies(true);
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/tracked_companies`, { withCredentials: true });
      setTrackedCompanies(response.data.companies || []);
    } catch (err) {
      console.error("Error loading companies:", err);
    } finally {
      setLoadingCompanies(false);
    }
  };

  const handleSearch = async () => {
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

      if (startDate) params.start_date = startDate.toISOString().split("T")[0];
      if (endDate) params.end_date = endDate.toISOString().split("T")[0];

      const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/search_nfe`, { params, withCredentials: true });
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Erro ao buscar NFE");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleViewDanfe = async (nfe) => {
    const nfeChave = nfe.chave || nfe.nfe_chave;
    setLoadingDanfe(nfeChave);
    try {
      if (nfeChave) {
        const encodedXmlKey = encodeURIComponent(nfeChave);
        const newWindow = window.open(`/danfe-loading.html?xmlKey=${encodedXmlKey}`, "_blank");
        if (!newWindow) {
          alert("Pop-up bloqueado pelo navegador. Por favor, permita pop-ups para este site.");
          return;
        }

        await axios.get(`${import.meta.env.VITE_API_URL}/api/get_nfe_data`, { params: { xmlKey: nfeChave }, withCredentials: true });

        const pdfResponse = await axios.get(`${import.meta.env.VITE_API_URL}/api/get_danfe_pdf`, { params: { xmlKey: nfeChave }, withCredentials: true });

        if (!pdfResponse.data) {
          newWindow.document.body.innerHTML = '<div style="color:red;">Erro ao carregar o PDF. Dados inválidos recebidos.</div>';
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
            .filter(([key, value]) => typeof value === "string" && value.length > 100)
            .sort((a, b) => b[1].length - a[1].length)[0];
          if (possibleBase64) {
            pdfBase64 = possibleBase64[1];
          } else {
            newWindow.document.body.innerHTML = '<div style="color:red;">Erro ao carregar o PDF. Formato de resposta não reconhecido.</div>';
            return;
          }
        }

        const byteCharacters = atob(pdfBase64);
        const byteArrays = [];
        for (let i = 0; i < byteCharacters.length; i += 512) {
          const slice = byteCharacters.slice(i, i + 512);
          const byteNumbers = new Array(slice.length);
          for (let j = 0; j < slice.length; j++) byteNumbers[j] = slice.charCodeAt(j);
          byteArrays.push(new Uint8Array(byteNumbers));
        }
        const blob = new Blob(byteArrays, { type: "application/pdf" });
        const blobUrl = URL.createObjectURL(blob);
        const number = nfe.numero || nfe.num_nf || nfe.number || nfe.numero_nf;
        newWindow.postMessage({ type: "pdfBlobUrl", url: blobUrl, number }, "*");
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

  const handleOpenPurchaseReport = (codPedc, codEmp1) => {
    try {
      openPurchaseOrderReport({ codPedc, codEmp1, apiUrl: import.meta.env.VITE_API_URL });
    } catch (err) {
      setError(err.message || "Erro ao abrir relatorio do pedido");
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("pt-BR");
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return "-";
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
  };

  const formatQuantity = (value) => {
    if (value === null || value === undefined) return "-";
    return Number(value).toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 3 });
  };

  const formatCNPJ = (cnpj) => {
    if (!cnpj) return "-";
    const cleaned = cnpj.replace(/\D/g, "");
    if (cleaned.length !== 14) return cnpj;
    return cleaned.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
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
    if (typeof window !== "undefined") {
      localStorage.removeItem(NFE_SEARCH_PARAMS_KEY);
    }
  };

  const toggleNfeExpanded = (nfeId) => {
    setExpandedNfe((prev) => ({ ...prev, [nfeId]: !prev[nfeId] }));
  };

  const searchFieldOptions = [
    { name: "searchByNumber", label: "Número da NF", checked: searchByNumber, onChange: setSearchByNumber },
    { name: "searchByChave", label: "Chave de Acesso", checked: searchByChave, onChange: setSearchByChave },
    { name: "searchByItem", label: "Descrição do Item", checked: searchByItem, onChange: handleSearchByItemChange },
    { name: "searchByFornecedor", label: "Fornecedor", checked: searchByFornecedor, onChange: handleSearchByFornecedorChange },
  ];

  const getNfePurchaseSummary = (nfe) => {
    const linked = nfe.linked_purchases || [];
    const estimated = nfe.estimated_purchases || [];
    const allPurchases = [...linked, ...estimated];
    const uniqueOrders = [...new Set(allPurchases.map((p) => p.cod_pedc))];
    return {
      allPurchases,
      uniqueOrders,
      uniqueOrderCount: uniqueOrders.length,
      linkedCount: linked.length,
      estimatedCount: estimated.length,
      hasEstimated: estimated.length > 0,
      hasLinked: linked.length > 0,
    };
  };

  const totalNfes = results?.nfes?.length || 0;
  const totalNfesWithOrders = results?.nfes?.filter((nfe) => getNfePurchaseSummary(nfe).uniqueOrderCount > 0).length || 0;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ptBR}>
      <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fa" }}>
        
        {/* Header Section */}
        <Paper elevation={0} sx={{ p: 3, mx: { xs: 2, md: 3 }, mt: { xs: 2, md: 3 }, mb: 3, background: "linear-gradient(135deg, #1a1f2e 0%, #2d3548 100%)", borderRadius: 3, color: "#fff" }}>
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 2 }}>
            <Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1 }}>
                <ManageSearchIcon sx={{ fontSize: 32 }} />
                <Typography variant="h5" sx={{ fontWeight: 700 }}>Buscar Notas Fiscais</Typography>
              </Box>
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.7)", maxWidth: 450 }}>
                Pesquise por número, descrição de item, fornecedor ou chave de acesso.
              </Typography>
            </Box>

            {/* Tracked Companies Info */}
            <Paper elevation={0} sx={{ px: 2.5, py: 1.5, bgcolor: "rgba(255,255,255,0.15)", borderRadius: 2, border: "1px solid rgba(255,255,255,0.2)", minWidth: 200 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <BusinessIcon sx={{ fontSize: 20, color: "#fff" }} />
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.8)", display: "block" }}>Empresas Rastreadas</Typography>
                  {loadingCompanies ? (
                    <CircularProgress size={16} sx={{ color: "#fff" }} />
                  ) : (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
                      {trackedCompanies.length === 0 ? (
                        <Typography variant="body2" sx={{ color: "#fff" }}>Nenhuma empresa</Typography>
                      ) : (
                        trackedCompanies.slice(0, 3).map((company) => {
                          const fullName = company.name || company.fantasy_name || formatCNPJ(company.cnpj);
                          const shortName = fullName.length > 20 ? fullName.substring(0, 20) + "..." : fullName;
                          const label = `${company.cod_emp1 ? company.cod_emp1 + " - " : ""}${shortName}`;
                          return (
                            <Tooltip key={company.id} title={`${company.cod_emp1 ? company.cod_emp1 + " - " : ""}${fullName}`}>
                              <Chip label={label} size="small" sx={{ bgcolor: "rgba(255,255,255,0.2)", color: "#fff", fontSize: "0.7rem", height: 22, maxWidth: 180 }} />
                            </Tooltip>
                          );
                        })
                      )}
                      {trackedCompanies.length > 3 && (
                        <Chip label={"+" + (trackedCompanies.length - 3)} size="small" sx={{ bgcolor: "rgba(255,255,255,0.3)", color: "#fff", fontSize: "0.7rem", height: 22 }} />
                      )}
                    </Box>
                  )}
                </Box>
                <Tooltip title="Configurar empresas">
                  <IconButton size="small" onClick={() => setShowTrackedCompanies(true)} sx={{ color: "rgba(255,255,255,0.7)", "&:hover": { color: "#fff", bgcolor: "rgba(255,255,255,0.1)" } }}>
                    <SettingsIcon sx={{ fontSize: 18 }} />
                  </IconButton>
                </Tooltip>
              </Box>
            </Paper>
          </Box>
        </Paper>

        <Box sx={{ px: { xs: 2, md: 3 }, pb: 3 }}>
          {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

          {/* Search Box */}
          <Paper elevation={0} sx={{ p: 3, mb: 3, borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
            <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap", mb: 3 }}>
              <TextField
                sx={{ flexGrow: 1, minWidth: 300 }}
                label="Buscar NFE"
                placeholder="Ex.: número da NF, descrição do item, fornecedor..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={handleKeyPress}
                variant="outlined"
                size="small"
                InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon color="action" /></InputAdornment> }}
              />
              <DatePicker label="Data Inicial" value={startDate} onChange={setStartDate} slotProps={{ textField: { size: "small", sx: { minWidth: 150 } } }} />
              <DatePicker label="Data Final" value={endDate} onChange={setEndDate} slotProps={{ textField: { size: "small", sx: { minWidth: 150 } } }} />
              <Button
                variant="contained"
                onClick={handleSearch}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
                sx={{ px: 3, py: 1, textTransform: "none", fontWeight: 600, bgcolor: "#1a1f2e", "&:hover": { bgcolor: "#2d3548" } }}
              >
                Buscar
              </Button>
            </Box>

            {/* Quick Filters */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Pesquisar por...</Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
                {searchFieldOptions.map((field) => (
                  <FormControlLabel
                    key={field.name}
                    control={<Checkbox checked={field.checked} onChange={(e) => field.onChange(e.target.checked)} size="small" />}
                    label={<Typography variant="body2">{field.label}</Typography>}
                    sx={{ mr: 2 }}
                  />
                ))}
                <FormControlLabel control={<Checkbox checked={exactTermSearch} onChange={(e) => setExactTermSearch(e.target.checked)} size="small" />} label={<Typography variant="body2">Termo Exato</Typography>} sx={{ mr: 2 }} />
                <FormControlLabel
                  control={<Switch checked={includeEstimated} onChange={(e) => setIncludeEstimated(e.target.checked)} size="small" />}
                  label={<Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}><AutoAwesomeIcon fontSize="small" color="secondary" /><Typography variant="body2">Matches estimados</Typography></Box>}
                />
                <Button variant="text" color="inherit" size="small" onClick={handleRestoreDefaults} sx={{ textTransform: "none", ml: "auto" }}>
                  Limpar filtros
                </Button>
              </Box>
            </Box>
          </Paper>

          {/* Loading State */}
          {loading && (
            <Box sx={{ mb: 3 }}>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} variant="rounded" height={150} sx={{ mb: 2, borderRadius: 2 }} animation="wave" />
              ))}
            </Box>
          )}

          {/* Results Area */}
          {!loading && results && (
            <Box>
              {/* Top Summary Metrics */}
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" }, gap: 1.5, mb: 2 }}>
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: 2, border: "1px solid", borderColor: "divider" }}>
                  <Typography variant="caption" color="text.secondary">NFEs encontradas</Typography>
                  <Typography variant="h6" fontWeight={700}>{totalNfes}</Typography>
                </Paper>
                <Paper elevation={0} sx={{ p: 1.5, borderRadius: 2, border: "1px solid", borderColor: "divider" }}>
                  <Typography variant="caption" color="text.secondary">NFEs com pedido vinculado</Typography>
                  <Typography variant="h6" fontWeight={700}>{totalNfesWithOrders}</Typography>
                </Paper>
              </Box>

              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Typography variant="subtitle1" fontWeight={600}>
                  {totalNfes} NFEs encontradas
                </Typography>
              </Box>

              {/* MAIN NFE CARDS */}
              {results.nfes && results.nfes.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  {results.nfes.map((nfe) => {
                    const nfeKey = nfe.id || nfe.chave || nfe.numero;
                    const linkedPurchases = nfe.linked_purchases || [];
                    const estimatedPurchases = nfe.estimated_purchases || [];
                    const allOrders = [...linkedPurchases, ...estimatedPurchases];

                    // Helper to get matching orders for a specific item in the NFE
                    const getLinkedOrdersForItem = (itemNumero) => {
                      return allOrders.filter(p => String(p.nfe_item_numero) === String(itemNumero));
                    };

                    const nfeItems = nfe.nfe_items || [];
                    const isExpanded = expandedNfe[nfeKey];

                    // Sort so matches appear first. Uses EVERY so all terms must be present.
                    const sortedItems = [...nfeItems].sort((a, b) => {
                      const aDesc = a.descricao || '';
                      const bDesc = b.descricao || '';
                      const terms = searchTerm ? searchTerm.trim().split(/\s+/).filter(t => t.length > 0) : [];
                      
                      const aMatch = terms.length > 0 && terms.every(t => aDesc.toLowerCase().includes(t.toLowerCase()));
                      const bMatch = terms.length > 0 && terms.every(t => bDesc.toLowerCase().includes(t.toLowerCase()));
                      
                      if (aMatch && !bMatch) return -1;
                      if (!aMatch && bMatch) return 1;
                      return (a.numero_item || 0) - (b.numero_item || 0);
                    });

                    const visibleItems = isExpanded ? sortedItems : sortedItems.slice(0, 3);
                    const hiddenCount = sortedItems.length - visibleItems.length;

                    return (
                      <Paper
                        key={nfeKey}
                        elevation={0}
                        sx={{
                          mb: 3,
                          overflow: "hidden",
                          borderRadius: 2,
                          border: "1px solid",
                          borderColor: "divider",
                        }}
                      >
                        {/* Dark Blue NFE Group Header */}
                        <Box
                          sx={{
                            bgcolor: "#2c3e50", // Dark slate/blue matches the UI request
                            color: "#fff",
                            px: 2,
                            py: 1.5,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            flexWrap: "wrap",
                            gap: 1
                          }}
                        >
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              Nota Fiscal: {nfe.numero} ~ Data: {formatDate(nfe.data_emissao)} ~ Fornecedor: {nfe.fornecedor || '-'} - {formatCurrency(nfe.valor_total)}
                            </Typography>
                            {nfe.informacoes_adicionais && (
                              <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'rgba(255,255,255,0.8)' }}>
                                <strong>Obs:</strong> {nfe.informacoes_adicionais}
                              </Typography>
                            )}
                          </Box>
                          
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Tooltip title="Ver Detalhes">
                              <IconButton size="small" onClick={() => { setSelectedNfe(nfe); setShowNfeDetails(true); }} sx={{ color: '#fff' }}>
                                <InfoOutlinedIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Visualizar DANFE">
                              <IconButton size="small" onClick={() => handleViewDanfe(nfe)} disabled={loadingDanfe === nfe.numero} sx={{ color: '#fff' }}>
                                {loadingDanfe === nfe.numero ? <CircularProgress size={18} color="inherit" /> : <PictureAsPdfIcon fontSize="small" />}
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </Box>

                        {/* NFE Items Table */}
                        <TableContainer>
                          <Table size="small">
                            <TableHead sx={{ bgcolor: "#f8fafc" }}>
                              <TableRow>
                                <TableCell sx={{ fontWeight: 600, width: 80 }}>Cod. item</TableCell>
                                <TableCell sx={{ fontWeight: 600 }}>Descrição do item</TableCell>
                                <TableCell align="center" sx={{ fontWeight: 600 }}>UN</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 600 }}>Quantidade</TableCell>
                                {canViewFinancials && (
                                  <>
                                    <TableCell align="right" sx={{ fontWeight: 600 }}>Preço Unitário</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 600 }}>Total</TableCell>
                                  </>
                                )}
                                <TableCell sx={{ fontWeight: 600 }}>Pedidos Vinculados</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {visibleItems.map((item, idx) => {
                                const linkedOrders = getLinkedOrdersForItem(item.numero_item);
                                const terms = searchTerm ? searchTerm.trim().split(/\s+/).filter(t => t.length > 0) : [];
                                
                                // Require EVERY word to match for the line to be flagged as Yellow
                                const isMatched = terms.length > 0 && terms.every(t => (item.descricao || '').toLowerCase().includes(t.toLowerCase()));

                                return (
                                  <TableRow key={item.id || idx} sx={{ bgcolor: isMatched ? '#fffde7' : 'inherit' }}>
                                    <TableCell>{item.numero_item}</TableCell>
                                    <TableCell>
                                      <Typography variant="body2">
                                        <HighlightedText text={item.descricao} highlight={searchTerm} />
                                      </Typography>
                                    </TableCell>
                                    <TableCell align="center">{item.unidade || '-'}</TableCell>
                                    <TableCell align="right">{formatQuantity(item.quantidade)}</TableCell>
                                    {canViewFinancials && (
                                      <>
                                        <TableCell align="right">{formatCurrency(item.preco_unitario)}</TableCell>
                                        <TableCell align="right">{formatCurrency((item.quantidade || 0) * (item.preco_unitario || 0))}</TableCell>
                                      </>
                                    )}
                                    <TableCell>
                                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                        {linkedOrders.map(lo => (
                                          <Tooltip key={`${lo.cod_emp1}-${lo.cod_pedc}-${lo.linha}`} title={`Comprador: ${lo.func_nome || '-'}`}>
                                            <Chip
                                              size="small"
                                              icon={lo.is_estimated ? <AutoAwesomeIcon sx={{ fontSize: 14 }} /> : undefined}
                                              label={`${lo.cod_emp1 || '-'}/${lo.cod_pedc} - L${lo.linha || '-'}`}
                                              color={lo.is_estimated ? "warning" : "primary"}
                                              variant="outlined"
                                              clickable
                                              onClick={() => handleOpenPurchaseReport(lo.cod_pedc, lo.cod_emp1)}
                                            />
                                          </Tooltip>
                                        ))}
                                        {linkedOrders.length === 0 && <Typography variant="caption" color="text.secondary">-</Typography>}
                                      </Box>
                                    </TableCell>
                                  </TableRow>
                                );
                              })}

                              {/* Show/Hide Items toggles */}
                              {!isExpanded && hiddenCount > 0 && (
                                <TableRow>
                                  <TableCell colSpan={canViewFinancials ? 7 : 5} align="center" sx={{ py: 1 }}>
                                    <Button
                                      size="small"
                                      color="inherit"
                                      endIcon={<KeyboardArrowDownIcon />}
                                      onClick={() => toggleNfeExpanded(nfeKey)}
                                      sx={{ textTransform: 'none', color: 'text.secondary' }}
                                    >
                                      Mostrar outros {hiddenCount} itens dessa nota
                                    </Button>
                                  </TableCell>
                                </TableRow>
                              )}
                              {isExpanded && hiddenCount > 0 && (
                                <TableRow>
                                  <TableCell colSpan={canViewFinancials ? 7 : 5} align="center" sx={{ py: 1 }}>
                                    <Button
                                      size="small"
                                      color="inherit"
                                      endIcon={<KeyboardArrowUpIcon />}
                                      onClick={() => toggleNfeExpanded(nfeKey)}
                                      sx={{ textTransform: 'none', color: 'text.secondary' }}
                                    >
                                      Ocultar itens
                                    </Button>
                                  </TableCell>
                                </TableRow>
                              )}
                            </TableBody>
                          </Table>
                        </TableContainer>

                        {/* NFE Footer Details */}
                        <Box sx={{ p: 1.5, bgcolor: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
                          <Typography variant="caption" color="text.secondary">
                            Chave: {nfe.chave} | CNPJ: {formatCNPJ(nfe.cnpj)}
                          </Typography>
                          <Typography variant="body2" fontWeight={600}>
                            Valor total da nota: {formatCurrency(nfe.valor_total)}
                          </Typography>
                        </Box>
                      </Paper>
                    );
                  })}
                </Box>
              )}

              {/* No results message */}
              {(!results.nfes || results.nfes.length === 0) && (
                <Paper elevation={0} sx={{ p: 4, textAlign: "center", borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
                  <ManageSearchIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">Nenhum resultado encontrado</Typography>
                  <Typography variant="body2" color="text.secondary">Tente ajustar os filtros ou termos de busca</Typography>
                </Paper>
              )}
            </Box>
          )}

          {/* Initial state - no search yet */}
          {!loading && !results && (
            <Paper elevation={0} sx={{ p: 4, textAlign: "center", borderRadius: 3, border: "1px solid", borderColor: "divider" }}>
              <ManageSearchIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
              <Typography variant="h6" color="text.secondary">Digite um termo para buscar</Typography>
              <Typography variant="body2" color="text.secondary">Pesquise por número da NF, descrição do item, fornecedor ou chave de acesso</Typography>
            </Paper>
          )}
        </Box>
      </Box>

      {/* Dialogs remain identical */}
      <TrackedCompanies open={showTrackedCompanies} onClose={() => { setShowTrackedCompanies(false); loadTrackedCompanies(); }} />
      <NFEDetails open={showNfeDetails} onClose={() => { setShowNfeDetails(false); setSelectedNfe(null); }} nfeChave={selectedNfe?.chave} nfeNumero={selectedNfe?.numero} />
    </LocalizationProvider>
  );
};

export default NFESearch;