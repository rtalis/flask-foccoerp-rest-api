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
  Stack,
  SvgIcon,
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
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import TrackedCompanies from "./TrackedCompanies";
import NFEDetails from "./NFEDetails";
import { openPurchaseOrderReport } from "../utils/openPurchaseOrderReport";

const PedIcon = (props) => (
  <SvgIcon {...props} viewBox="0 0 22 22">
    <path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z M11.5 9.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5z M12.5 7h3v1h-1.5v1.5h1.5v1h-1.5v1.5h1.5v1h-3z M21.5 11.5c0 .83-.67 1.5-1.5 1.5h-2.5V7H20c.83 0 1.5.67 1.5 1.5z M9 9.5h1v-1H9z M19 11.5h1v-3h-1z M4 6H2v14c0 1.1.9 2 2 2h14v-2H4z" />
  </SvgIcon>
);

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
  const [expandedNfeItemGroups, setExpandedNfeItemGroups] = useState({});
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
        const response = await axios.get(
          `${import.meta.env.VITE_API_URL}/auth/me`,
          { withCredentials: true },
        );
        if (!isMounted) {
          return;
        }
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
        nfe_item_numero: purchase.nfe_item_numero,
        nfe_item_descricao: purchase.nfe_item_descricao,
        nfe_item_quantidade: purchase.nfe_item_quantidade,
        nfe_item_unidade: purchase.nfe_item_unidade,
        nfe_item_preco: purchase.nfe_item_preco,
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

  const toggleNfeItemGroupExpanded = (key) => {
    setExpandedNfeItemGroups((prev) => ({
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
        `${import.meta.env.VITE_API_URL}/api/tracked_companies`,
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
        `${import.meta.env.VITE_API_URL}/api/search_nfe`,
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
        const encodedXmlKey = encodeURIComponent(nfeChave);
        const newWindow = window.open(
          `/danfe-loading.html?xmlKey=${encodedXmlKey}`,
          "_blank",
        );
        if (!newWindow) {
          alert(
            "Pop-up bloqueado pelo navegador. Por favor, permita pop-ups para este site.",
          );
          return;
        }

        // First ensure the NFE data is stored in the database
        await axios.get(`${import.meta.env.VITE_API_URL}/api/get_nfe_data`, {
          params: { xmlKey: nfeChave },
          withCredentials: true,
        });

        // Then get the PDF
        const pdfResponse = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/get_danfe_pdf`,
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

  const handleOpenPurchaseReport = (codPedc, codEmp1) => {
    try {
      openPurchaseOrderReport({
        codPedc,
        codEmp1,
        apiUrl: import.meta.env.VITE_API_URL,
      });
    } catch (err) {
      setError(err.message || "Erro ao abrir relatorio do pedido");
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

  const formatQuantity = (value) => {
    if (value === null || value === undefined) return "-";
    return Number(value).toLocaleString("pt-BR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3,
    });
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

  const getNfePurchaseSummary = (nfe) => {
    const linked = nfe.linked_purchases || [];
    const estimated = nfe.estimated_purchases || [];
    const allPurchases = [...linked, ...estimated];
    const uniqueOrders = [...new Set(allPurchases.map((p) => p.cod_pedc))];
    const estimatedCount = estimated.length;
    const linkedCount = linked.length;
    return {
      allPurchases,
      uniqueOrders,
      uniqueOrderCount: uniqueOrders.length,
      linkedCount,
      estimatedCount,
      hasEstimated: estimatedCount > 0,
      hasLinked: linkedCount > 0,
    };
  };

  const groupPurchasesByNfeItem = (purchases, nfeItems = []) => {
    const grouped = {};

    nfeItems.forEach((nfeItem) => {
      const key = `${nfeItem.numero_item || "sem-numero"}-${nfeItem.descricao || "sem-descricao"}`;
      grouped[key] = {
        key,
        nfe_item_id: nfeItem.id,
        nfe_item_descricao: nfeItem.descricao || "Não identificado",
        nfe_item_numero: nfeItem.numero_item,
        nfe_item_unidade: nfeItem.unidade,
        nfe_item_quantidade: nfeItem.quantidade,
        nfe_item_preco: nfeItem.preco_unitario,
        fulfillments: [],
        has_estimated: false,
      };
    });

    purchases.forEach((purchase, idx) => {
      const key = `${purchase.nfe_item_numero || "sem-numero"}-${purchase.nfe_item_descricao || "sem-descricao"}`;
      if (!grouped[key]) {
        grouped[key] = {
          key,
          nfe_item_id: null,
          nfe_item_descricao: purchase.nfe_item_descricao || "Não identificado",
          nfe_item_numero: purchase.nfe_item_numero,
          nfe_item_unidade: purchase.nfe_item_unidade || purchase.unidade_medida,
          nfe_item_quantidade: purchase.nfe_item_quantidade,
          nfe_item_preco: purchase.nfe_item_preco,
          fulfillments: [],
          has_estimated: false,
        };
      }

      if (purchase.is_estimated) {
        grouped[key].has_estimated = true;
      }

      grouped[key].fulfillments.push({
        id: `${purchase.cod_emp1}-${purchase.cod_pedc}-${purchase.linha || idx}`,
        cod_emp1: purchase.cod_emp1,
        cod_pedc: purchase.cod_pedc,
        item_descricao: purchase.item_descricao,
        func_nome: purchase.func_nome,
        quantidade: purchase.quantidade,
        preco_unitario: purchase.preco_unitario,
        total_item: purchase.total_item,
        linha: purchase.linha,
      });
    });

    return Object.values(grouped).sort((a, b) => {
      const aNum = a.nfe_item_numero ?? Number.MAX_SAFE_INTEGER;
      const bNum = b.nfe_item_numero ?? Number.MAX_SAFE_INTEGER;
      return aNum - bNum;
    });
  };

  const totalNfes = results?.nfes?.length || 0;
  const totalNfesWithOrders =
    results?.nfes?.filter((nfe) => getNfePurchaseSummary(nfe).uniqueOrderCount > 0)
      .length || 0;
  const totalUnlinkedOrders = results?.unlinked_purchase_orders?.length || 0;

  const buildNfeItemGroupKey = (nfeKey, nfeItemNumero, nfeItemDescricao) =>
    `nfe-item-${nfeKey}-${nfeItemNumero || "sem-numero"}-${nfeItemDescricao || "sem-descricao"}`;

  const handleOpenPurchaseDetails = (nfeKey, nfe, codPedc, codEmp1) => {
    setExpandedNfe((prev) => ({ ...prev, [nfeKey]: true }));
    const purchases = [
      ...(nfe.linked_purchases || []),
      ...(nfe.estimated_purchases || []),
    ];
    const selectedPurchase = purchases.find(
      (purchase) =>
        purchase.cod_pedc === codPedc && String(purchase.cod_emp1) === String(codEmp1),
    );

    if (!selectedPurchase) return;

    const nfeItemGroupKey = buildNfeItemGroupKey(
      nfeKey,
      selectedPurchase.nfe_item_numero,
      selectedPurchase.nfe_item_descricao,
    );
    setExpandedNfeItemGroups((prev) => ({ ...prev, [nfeItemGroupKey]: true }));
  };

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
                          const label = `${company.cod_emp1 ? company.cod_emp1 + " - " : ""
                            }${shortName}`;
                          const fullLabel = `${company.cod_emp1 ? company.cod_emp1 + " - " : ""
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
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(3, minmax(0, 1fr))",
                  },
                  gap: 1.5,
                  mb: 2,
                }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    NFEs encontradas
                  </Typography>
                  <Typography variant="h6" fontWeight={700}>
                    {totalNfes}
                  </Typography>
                </Paper>
                <Paper
                  elevation={0}
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    NFEs com pedido vinculado
                  </Typography>
                  <Typography variant="h6" fontWeight={700}>
                    {totalNfesWithOrders}
                  </Typography>
                </Paper>
                <Paper
                  elevation={0}
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    border: "1px solid",
                    borderColor: "warning.main",
                    bgcolor: "#fffaf0",
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    Pedidos atendidos com NFE, mas sem dados correspondentes.
                  </Typography>
                  <Typography variant="h6" fontWeight={700} color="warning.dark">
                    {totalUnlinkedOrders}
                  </Typography>
                </Paper>
              </Box>

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
                  {totalNfes} NFEs encontradas
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
                        <TableCell sx={{ fontWeight: 600 }}>
                          NFE
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>
                          Fornecedor
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Valor
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Atende ao pedido(s)
                        </TableCell>
                        <TableCell align="center" sx={{ fontWeight: 600 }}>
                          Ações
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {results.nfes.map((nfe) => {
                        const nfeKey = nfe.id || nfe.chave || nfe.numero;
                        const summary = getNfePurchaseSummary(nfe);
                        return (
                          <React.Fragment key={nfeKey}>
                            <TableRow
                              hover
                              sx={{
                                bgcolor: expandedNfe[nfeKey]
                                  ? "#e3f2fd"
                                  : "inherit",
                                "&:hover": { bgcolor: "#e3f2fd" },
                              }}
                            >
                              <TableCell padding="checkbox" sx={{ width: 40 }}>
                                {summary.uniqueOrderCount > 0 && (
                                  <Tooltip title="Ver/ocultar pedidos vinculados">
                                    <IconButton
                                      size="small"
                                      onClick={() => toggleNfeExpanded(nfeKey)}
                                      sx={{
                                        transform: expandedNfe[nfeKey]
                                          ? "rotate(180deg)"
                                          : "rotate(0deg)",
                                        transition: "transform 0.3s ease",
                                      }}
                                    >
                                      <KeyboardArrowDownIcon
                                        fontSize="small"
                                        sx={{ color: "primary.main" }}
                                      />
                                    </IconButton>
                                  </Tooltip>
                                )}
                              </TableCell>
                              <TableCell>
                                <Typography fontWeight={700}>{nfe.numero}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  Emissão: {formatDate(nfe.data_emissao)}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ display: "block" }}
                                >
                                  Chave: {(nfe.chave || "-").toString().slice(0, 16)}...
                                </Typography>
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
                                <Typography variant="caption" color="text.secondary">
                                  CNPJ: {formatCNPJ(nfe.cnpj)}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                {formatCurrency(nfe.valor_total)}
                              </TableCell>
                              <TableCell align="center">
                                {summary.uniqueOrderCount === 0 ? (
                                  <Chip
                                    size="small"
                                    label="Sem vínculo"
                                    variant="outlined"
                                    color="default"
                                  />
                                ) : (
                                  (() => {
                                    const groupedOrders = groupPurchasesByOrder(
                                      summary.allPurchases,
                                    );
                                    const visibleOrders = groupedOrders.slice(0, 3);
                                    const extraCount = groupedOrders.length - visibleOrders.length;

                                    return (
                                      <Stack
                                        direction="column"
                                        spacing={0.5}
                                        justifyContent="center"
                                        alignItems="center"
                                        useFlexGap
                                      >
                                        {visibleOrders.map((order) => (
                                          <Box
                                            key={`${order.cod_emp1}-${order.cod_pedc}`}
                                            sx={{
                                              display: "flex",
                                              alignItems: "center",
                                              gap: 0.5,
                                            }}
                                          >
                                            {order.has_estimated && (
                                              <AutoAwesomeIcon
                                                sx={{ fontSize: 16, color: "warning.main" }}
                                              />
                                            )}
                                            <Tooltip title="Abrir detalhes do pedido">
                                              <Chip
                                                size="small"
                                                label={`${order.cod_emp1 || "-"} / ${order.cod_pedc}`}
                                                color={order.has_estimated ? "warning" : "primary"}
                                                variant="outlined"
                                                clickable
                                                onClick={() =>
                                                  handleOpenPurchaseDetails(
                                                    nfeKey,
                                                    nfe,
                                                    order.cod_pedc,
                                                    order.cod_emp1,
                                                  )
                                                }
                                              />
                                            </Tooltip>
                                            <Tooltip title="Visualizar pedido de compra">
                                              <IconButton
                                                size="small"
                                                color="primary"
                                                onClick={() =>
                                                  handleOpenPurchaseReport(
                                                    order.cod_pedc,
                                                    order.cod_emp1,
                                                  )
                                                }
                                              >
                                                <PedIcon sx={{ fontSize: 16 }} />
                                              </IconButton>
                                            </Tooltip>
                                          </Box>
                                        ))}
                                        {extraCount > 0 && (
                                          <Tooltip
                                            title={groupedOrders
                                              .slice(3)
                                              .map(
                                                (order) =>
                                                  `${order.cod_emp1 || "-"} / ${order.cod_pedc}`,
                                              )
                                              .join(", ")}
                                          >
                                            <Chip
                                              size="small"
                                              label={`+${extraCount}`}
                                              variant="outlined"
                                            />
                                          </Tooltip>
                                        )}
                                      </Stack>
                                    );
                                  })()
                                )}
                              </TableCell>
                              <TableCell align="center">
                                <Box
                                  sx={{
                                    display: "flex",
                                    justifyContent: "center",
                                    alignItems: "center",
                                    columnGap: 0.5,
                                  }}
                                >
                                  <Box sx={{ width: 32, display: "flex", justifyContent: "center" }}>
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
                                  </Box>
                                  <Box sx={{ width: 32, display: "flex", justifyContent: "center" }}>
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
                                </Box>
                              </TableCell>
                            </TableRow>
                            {/* Expanded Row - Linked Purchase Orders */}
                            <TableRow>
                              <TableCell colSpan={6} sx={{ py: 0, border: 0 }}>
                                <Collapse
                                  in={expandedNfe[nfeKey]}
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

                                      // Group purchases by NFE item (item-first hierarchy)
                                      const groupedNfeItems =
                                        groupPurchasesByNfeItem(
                                          allPurchases,
                                          nfe.nfe_items || [],
                                        );

                                      return (
                                        <Box>
                                          <Table
                                            size="small"
                                            sx={{
                                              bgcolor: "#fff",
                                              borderRadius: 1,
                                            }}
                                          >
                                            <TableHead>
                                              <TableRow sx={{ bgcolor: "#f8fafc" }}>
                                                <TableCell padding="checkbox" />
                                                <TableCell>Item NFE</TableCell>
                                                <TableCell align="center">
                                                  UN
                                                </TableCell>
                                                <TableCell align="right">
                                                  Qtde NFE
                                                </TableCell>
                                                {canViewFinancials && (
                                                  <>
                                                    <TableCell align="right">
                                                      Vlr Unit. NFE
                                                    </TableCell>
                                                    <TableCell align="right">
                                                      Total NFE
                                                    </TableCell>
                                                  </>
                                                )}
                                                <TableCell align="center">
                                                  Vinculacoes
                                                </TableCell>
                                              </TableRow>
                                            </TableHead>
                                            <TableBody>
                                              {groupedNfeItems.map((nfeItem) => {
                                                const nfeItemKey = buildNfeItemGroupKey(
                                                  nfeKey,
                                                  nfeItem.nfe_item_numero,
                                                  nfeItem.nfe_item_descricao,
                                                );
                                                const nfeTotal =
                                                  (Number(nfeItem.nfe_item_quantidade) || 0) *
                                                  (Number(nfeItem.nfe_item_preco) || 0);
                                                return (
                                                  <React.Fragment key={nfeItemKey}>
                                                    <TableRow
                                                      hover
                                                      onClick={() =>
                                                        toggleNfeItemGroupExpanded(
                                                          nfeItemKey,
                                                        )
                                                      }
                                                      sx={{
                                                        bgcolor: expandedNfeItemGroups[
                                                          nfeItemKey
                                                        ]
                                                          ? "#f0f9ff"
                                                          : "#f8fafc",
                                                        "&:hover": {
                                                          bgcolor: "#f0f9ff",
                                                          cursor: "pointer",
                                                        },
                                                        borderBottom: "1px solid #e2e8f0",
                                                        transition: "background-color 0.2s",
                                                      }}
                                                    >
                                                      <TableCell padding="checkbox" sx={{ width: 40 }}>
                                                        <IconButton
                                                          size="small"
                                                          onClick={(e) => {
                                                            e.stopPropagation();
                                                            toggleNfeItemGroupExpanded(
                                                              nfeItemKey,
                                                            );
                                                          }}
                                                          sx={{
                                                            transform: expandedNfeItemGroups[
                                                              nfeItemKey
                                                            ]
                                                              ? "rotate(180deg)"
                                                              : "rotate(0deg)",
                                                            transition: "transform 0.3s ease",
                                                          }}
                                                        >
                                                          <KeyboardArrowDownIcon
                                                            fontSize="small"
                                                            sx={{ color: "primary.main" }}
                                                          />
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
                                                            variant="body2"
                                                            sx={{
                                                              maxWidth: 360,
                                                              overflow: "hidden",
                                                              textOverflow:
                                                                "ellipsis",
                                                              whiteSpace:
                                                                "nowrap",
                                                            }}
                                                          >
                                                            {nfeItem.nfe_item_numero
                                                              ? `#${nfeItem.nfe_item_numero} - `
                                                              : ""}
                                                            {nfeItem.nfe_item_descricao}
                                                          </Typography>
                                                          {nfeItem.has_estimated && (
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
                                                      <TableCell align="center">
                                                        {nfeItem.nfe_item_unidade ||
                                                          "-"}
                                                      </TableCell>
                                                      <TableCell align="right">
                                                        {formatQuantity(
                                                          nfeItem.nfe_item_quantidade,
                                                        )}
                                                      </TableCell>
                                                      {canViewFinancials && (
                                                        <>
                                                          <TableCell align="right">
                                                            {nfeItem.nfe_item_preco !=
                                                              null
                                                              ? formatCurrency(
                                                                nfeItem.nfe_item_preco,
                                                              )
                                                              : "-"}
                                                          </TableCell>
                                                          <TableCell align="right">
                                                            {nfeItem.nfe_item_preco !=
                                                              null &&
                                                              nfeItem.nfe_item_quantidade !=
                                                              null
                                                              ? formatCurrency(
                                                                nfeTotal,
                                                              )
                                                              : "-"}
                                                          </TableCell>
                                                        </>
                                                      )}
                                                      <TableCell align="center">
                                                        <Chip
                                                          size="small"
                                                          label={
                                                            nfeItem.fulfillments
                                                              .length
                                                          }
                                                          color="primary"
                                                          variant="outlined"
                                                        />
                                                      </TableCell>
                                                    </TableRow>
                                                    {/* Nested Items Row */}
                                                    <TableRow>
                                                      <TableCell
                                                        colSpan={
                                                          canViewFinancials
                                                            ? 7
                                                            : 5
                                                        }
                                                        sx={{ py: 0, border: 0, bgcolor: "transparent" }}
                                                      >
                                                        <Collapse
                                                          in={
                                                            expandedNfeItemGroups[
                                                            nfeItemKey
                                                            ]
                                                          }
                                                          timeout="auto"
                                                          unmountOnExit
                                                        >
                                                          <Box
                                                            sx={{
                                                              py: 2,
                                                              pl: 8,
                                                              pr: 2,
                                                              bgcolor: "#ffffff",
                                                              borderLeft: "3px solid #3b82f6",
                                                            }}
                                                          >
                                                            <Table
                                                              size="small"
                                                              sx={{
                                                                bgcolor: "#f9fafb",
                                                                borderRadius: 1,
                                                                border: "1px solid #e5e7eb",
                                                              }}
                                                            >
                                                              <TableHead>
                                                                <TableRow
                                                                  sx={{
                                                                    bgcolor:
                                                                      "#f3f4f6",
                                                                    borderBottom: "2px solid #d1d5db",
                                                                  }}
                                                                >
                                                                  <TableCell
                                                                    sx={{
                                                                      fontSize: "0.70rem",
                                                                      fontWeight: 600,
                                                                      color: "#6b7280",
                                                                      textTransform: "uppercase",
                                                                      letterSpacing: "0.5px",
                                                                      py: 1,
                                                                    }}
                                                                  >
                                                                    Pedido
                                                                  </TableCell>
                                                                  <TableCell
                                                                    sx={{
                                                                      fontSize: "0.70rem",
                                                                      fontWeight: 600,
                                                                      color: "#6b7280",
                                                                      textTransform: "uppercase",
                                                                      letterSpacing: "0.5px",
                                                                      py: 1,
                                                                    }}
                                                                  >
                                                                    Item do Pedido
                                                                  </TableCell>
                                                                  <TableCell
                                                                    align="right"
                                                                    sx={{
                                                                      fontSize: "0.70rem",
                                                                      fontWeight: 600,
                                                                      color: "#6b7280",
                                                                      textTransform: "uppercase",
                                                                      letterSpacing: "0.5px",
                                                                      py: 1,
                                                                    }}
                                                                  >
                                                                    Comprador
                                                                  </TableCell>
                                                                  <TableCell
                                                                    align="right"
                                                                    sx={{
                                                                      fontSize: "0.70rem",
                                                                      fontWeight: 600,
                                                                      color: "#6b7280",
                                                                      textTransform: "uppercase",
                                                                      letterSpacing: "0.5px",
                                                                      py: 1,
                                                                    }}
                                                                  >
                                                                    Qtde Pedido
                                                                  </TableCell>
                                                                  {canViewFinancials && (
                                                                    <>
                                                                      <TableCell
                                                                        align="right"
                                                                        sx={{
                                                                          fontSize: "0.70rem",
                                                                          fontWeight: 600,
                                                                          color: "#6b7280",
                                                                          textTransform: "uppercase",
                                                                          letterSpacing: "0.5px",
                                                                          py: 1,
                                                                        }}
                                                                      >
                                                                        Preço Unit. Pedido
                                                                      </TableCell>
                                                                      <TableCell
                                                                        align="right"
                                                                        sx={{
                                                                          fontSize: "0.70rem",
                                                                          fontWeight: 600,
                                                                          color: "#6b7280",
                                                                          textTransform: "uppercase",
                                                                          letterSpacing: "0.5px",
                                                                          py: 1,
                                                                        }}
                                                                      >
                                                                        Total Pedido
                                                                      </TableCell>
                                                                    </>
                                                                  )}
                                                                </TableRow>
                                                              </TableHead>
                                                              <TableBody>
                                                                {nfeItem.fulfillments.map(
                                                                  (purchaseItem) => {
                                                                    return (
                                                                      <TableRow
                                                                        key={
                                                                          purchaseItem.id
                                                                        }
                                                                        sx={{
                                                                          "&:hover": {
                                                                            bgcolor: "#f3f4f6",
                                                                          },
                                                                          borderBottom: "1px solid #e5e7eb",
                                                                          transition: "background-color 0.2s",
                                                                        }}
                                                                      >
                                                                        <TableCell
                                                                          sx={{
                                                                            fontSize: "0.875rem",
                                                                            py: 1,
                                                                          }}
                                                                        >
                                                                          <Typography
                                                                            variant="body2"
                                                                            sx={{
                                                                              fontWeight: 500,
                                                                              color: "#1f2937",
                                                                            }}
                                                                          >
                                                                            {`${purchaseItem.cod_emp1 || "-"} / ${purchaseItem.cod_pedc || "-"}`}
                                                                          </Typography>
                                                                        </TableCell>
                                                                        <TableCell
                                                                          sx={{
                                                                            fontSize: "0.875rem",
                                                                            py: 1,
                                                                          }}
                                                                        >
                                                                          <Typography
                                                                            variant="body2"
                                                                            sx={{
                                                                              maxWidth: 420,
                                                                              overflow:
                                                                                "hidden",
                                                                              textOverflow:
                                                                                "ellipsis",
                                                                              whiteSpace:
                                                                                "nowrap",
                                                                              color: "#374151",
                                                                            }}
                                                                          >
                                                                            {`L${purchaseItem.linha || "-"} - ${purchaseItem.item_descricao || "-"}`}
                                                                          </Typography>
                                                                        </TableCell>
                                                                        <TableCell
                                                                          align="right"
                                                                          sx={{
                                                                            fontSize: "0.875rem",
                                                                            py: 1,
                                                                          }}
                                                                        >
                                                                          <Typography variant="body2">
                                                                            {purchaseItem.func_nome ||
                                                                              "-"}
                                                                          </Typography>
                                                                        </TableCell>
                                                                        <TableCell
                                                                          align="right"
                                                                          sx={{
                                                                            fontSize: "0.875rem",
                                                                            py: 1,
                                                                          }}
                                                                        >
                                                                          {formatQuantity(
                                                                            purchaseItem.quantidade,
                                                                          )}
                                                                        </TableCell>
                                                                        {canViewFinancials && (
                                                                          <>
                                                                            <TableCell
                                                                              align="right"
                                                                              sx={{
                                                                                fontSize: "0.875rem",
                                                                                py: 1,
                                                                              }}
                                                                            >
                                                                              {formatCurrency(
                                                                                purchaseItem.preco_unitario,
                                                                              )}
                                                                            </TableCell>
                                                                            <TableCell
                                                                              align="right"
                                                                              sx={{
                                                                                fontSize: "0.875rem",
                                                                                py: 1,
                                                                                fontWeight: 600,
                                                                                color: "#1f2937",
                                                                              }}
                                                                            >
                                                                              {formatCurrency(
                                                                                purchaseItem.total_item,
                                                                              )}
                                                                            </TableCell>
                                                                          </>
                                                                        )}
                                                                      </TableRow>
                                                                    );
                                                                  },
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
                        )
                      })}
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
                              Pedidos atendidos no sistema com "{results.query}" mas sem danfe correspondente
                              ({groupedUnlinked.length}{" "}
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
                                                    {canViewFinancials && (
                                                      <>
                                                        <TableCell align="right">
                                                          Preço Unit.
                                                        </TableCell>
                                                        <TableCell align="right">
                                                          Total
                                                        </TableCell>
                                                      </>
                                                    )}
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
                                                        {canViewFinancials && (
                                                          <>
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
                                                          </>
                                                        )}
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
