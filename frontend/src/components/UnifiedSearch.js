import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import ItemScreen from './ItemScreen';
import './UnifiedSearch.css';

import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableFooter,
  Paper, Collapse, Box, Typography, IconButton, TextField, Button, Radio, RadioGroup,
  FormControlLabel, FormControl, FormLabel, Checkbox, Select, MenuItem, InputAdornment,
  AppBar, Toolbar, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Divider,
  CircularProgress, Dialog, DialogTitle, DialogContent, DialogActions, Card, CardContent,
  CardActions, Slide, useScrollTrigger, Switch
} from '@mui/material';
import Autocomplete from '@mui/material/Autocomplete';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import CompareIcon from '@mui/icons-material/Compare';
import UploadIcon from '@mui/icons-material/Upload';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import SearchIcon from '@mui/icons-material/Search';
import LogoutIcon from '@mui/icons-material/Logout';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import ReceiptIcon from '@mui/icons-material/Receipt';
import ManageSearchIcon from '@mui/icons-material/ManageSearch';


const DRAWER_WIDTH_OPEN = 260;
const DRAWER_WIDTH_COLLAPSED = 60;

function HideOnScroll(props) {
  const { children, threshold = 100 } = props;
  const trigger = useScrollTrigger({
    disableHysteresis: true,
    threshold: threshold,
  });

  return (
    <Slide appear={false} direction="down" in={!trigger}>
      {children}
    </Slide>
  );
}
function HideSidebar(props) {
  const { children, threshold = 100 } = props;
  const trigger = useScrollTrigger({
    disableHysteresis: true,
    threshold: threshold,
  });

  return (
    <Slide appear={false} direction="left" in={!trigger}>
      {children}
    </Slide>
  );
}


function PurchaseRow(props) {
  const { purchase, formatDate, formatNumber, formatCurrency, getFirstWords, handleItemClick } = props;
  const [open, setOpen] = useState(true); // Expanded by default
  const [nfeData, setNfeData] = useState(null);
  const [loadingNfe, setLoadingNfe] = useState(false);
  const [showNfeDialog, setShowNfeDialog] = useState(false);

  const fetchNfeData = async () => {
    setLoadingNfe(true);
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/nfe_by_purchase`, {
        params: { cod_pedc: purchase.order.cod_pedc },
        withCredentials: true
      });
      setNfeData(response.data);
      setShowNfeDialog(true);
    } catch (error) {
      console.error('Error fetching NFE data:', error);
    } finally {
      setLoadingNfe(false);
    }
  };

  /** Inicial implementationm, TODO a more robust version  */

  const handleNfeClick = async (nfe) => {
    try {
      const newWindow = window.open('', '_blank');
      if (!newWindow) {
        alert('Pop-up bloqueado pelo navegador. Por favor, permita pop-ups para este site.');
        return;
      }
      newWindow.document.write(`
      <html>
        <head>
          <title>Visualizando DANFE</title>
          <style>
            body { 
              font-family: Arial, sans-serif; 
              display: flex;
              justify-content: center;
              align-items: center;
              height: 100vh;
              margin: 0;
              flex-direction: column;
            }
            .loading { margin-bottom: 20px; }
          </style>
        </head>
        <body>
          <div class="loading">Carregando DANFE...</div>
                          <div className="spinner"></div>

        </body>
      </html>
    `);
      newWindow.document.close();

      // First ensure the NFE data is stored in the database
      await axios.get(`${process.env.REACT_APP_API_URL}/api/get_nfe_data`, {
        params: { xmlKey: nfe.chave },
        withCredentials: true
      });

      // Then get the PDF
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/get_danfe_pdf`, {
        params: { xmlKey: nfe.chave },
        withCredentials: true
      });

      if (!response.data) {
        newWindow.document.body.innerHTML = '<div style="color:red;">Erro ao carregar o PDF. Dados inválidos recebidos.</div>';
        return;
      }
      let pdfBase64;
      if (typeof response.data === 'string') {
        pdfBase64 = response.data;
      } else if (response.data.arquivo) {
        pdfBase64 = response.data.arquivo;
      } else if (response.data.pdf) {
        pdfBase64 = response.data.pdf;
      } else if (response.data.content) {
        pdfBase64 = response.data.content;
      } else {
        const possibleBase64 = Object.entries(response.data)
          .filter(([key, value]) => typeof value === 'string' && value.length > 100)
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
        for (let j = 0; j < slice.length; j++) {
          byteNumbers[j] = slice.charCodeAt(j);
        }
        byteArrays.push(new Uint8Array(byteNumbers));
      }
      const blob = new Blob(byteArrays, { type: 'application/pdf' });

      const blobUrl = URL.createObjectURL(blob);

      newWindow.document.write(`
      <html>
        <head>
          <title>DANFE - ${nfe.numero || nfe.chave}</title>
          <style>
            body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; }
            #pdf-viewer { width: 100%; height: 100%; }
          </style>
        </head>
        <body>
          <embed id="pdf-viewer" src="${blobUrl}" type="application/pdf" width="100%" height="100%">
        </body>
      </html>
    `);
      newWindow.document.close();

    } catch (error) {
      console.error('Error fetching DANFE PDF:', error);
    }
  };

  const handleDialogClose = () => {
    setShowNfeDialog(false);
  };

  return (
    <React.Fragment>
      {/* Purchase header row */}
      <TableRow sx={{
        '& > *': { borderBottom: 'unset' },
        backgroundColor: purchase.order.is_fulfilled ? '#38be26ff' : '#64a176ff',
        '&:hover': { backgroundColor: purchase.order.is_fulfilled ? '#7cb342' : '#5d836cff' }
      }}>
        <TableCell style={{ padding: 0 }}>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell colSpan={9} align="center" sx={{ fontWeight: 'bold', fontSize: '1.05rem' }}  >
          Pedido de Compra: {purchase.order.cod_pedc}
          ~ {purchase.order.fornecedor_id} {getFirstWords(purchase.order.fornecedor_descricao, 4)} - {formatCurrency(purchase.order.adjusted_total)} ~ Comprador: {purchase.order.func_nome}. Empresa: {purchase.order.cod_emp1}
          {purchase.order.is_fulfilled && <span style={{ marginLeft: '8px', color: '#2e7d32' }}>✓ Atendido</span>}

        </TableCell>
      </TableRow>

      {/* Collapsible items section */}
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={11}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>
              <Table size="small" aria-label="items">
                <TableHead>
                  <TableRow>
                    <TableCell>Data Emissão</TableCell>
                    <TableCell>Cod. item</TableCell>
                    <TableCell>Descrição do item</TableCell>
                    <TableCell>Quantidade</TableCell>
                    <TableCell>Preço Unitário</TableCell>
                    <TableCell>IPI</TableCell>
                    <TableCell>Total</TableCell>
                    <TableCell>Qtde Atendida</TableCell>
                    <TableCell>Dt Entrada</TableCell>
                    <TableCell>NFEs</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {purchase.items.map((item) => (
                    <TableRow
                      key={item.id}
                      sx={{
                        backgroundColor: item.quantidade === item.qtde_atendida
                          ? '#f4fbffff' // Light blue for fully fulfilled items
                          : (item.qtde_atendida > 0 && item.qtde_atendida < item.quantidade)
                            ? '#fff4f4ff' // Light red for partially fulfilled items
                            : 'inherit', // Default color for unfulfilled items
                        '&:hover': {
                          backgroundColor: item.quantidade === item.qtde_atendida
                            ? '#bbdefb' // Darker blue on hover
                            : (item.qtde_atendida > 0 && item.qtde_atendida < item.quantidade)
                              ? '#ffcdd2' // Darker red on hover
                              : '#f5f5f5' // Light gray on hover for default
                        }
                      }}
                    >
                      <TableCell>{formatDate(purchase.order.dt_emis)}</TableCell>
                      <TableCell
                        onClick={() => handleItemClick(item.id)}
                        sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                      >
                        {item.item_id}
                      </TableCell>
                      <TableCell>{item.descricao}</TableCell>
                      <TableCell>{formatNumber(item.quantidade)} {item.unidade_medida}</TableCell>
                      <TableCell>R$ {formatNumber(item.preco_unitario)}</TableCell>
                      <TableCell>{item.perc_ipi ? `${formatNumber(item.perc_ipi)}%` : '0%'}</TableCell>
                      <TableCell>R$ {formatNumber(item.total)}</TableCell>
                      <TableCell>{formatNumber(item.qtde_atendida)} {item.unidade_medida}</TableCell>
                      <TableCell>
                        {purchase.order.nfes.map(nf => (
                          <div key={nf.id}>
                            {nf.linha == item.linha && (
                              <>
                                {nf.dt_ent ? formatDate(nf.dt_ent) : ''}
                                {nf.qtde ? ` (${formatNumber(nf.qtde)} ${item.unidade_medida})` : ''}
                              </>
                            )}
                          </div>
                        ))}
                      </TableCell>
                      <TableCell>
                        {purchase.order.nfes.map(nf => (
                          nf.linha == item.linha && nf.num_nf ? (
                            <div key={nf.id}>{nf.num_nf}</div>
                          ) : null
                        ))}
                      </TableCell>
                      <TableCell>
                        {true ? (
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={fetchNfeData}
                            disabled={loadingNfe}
                            title="Ver detalhes das notas fiscais"
                          >
                            <SearchIcon fontSize="small" />
                          </IconButton>
                        ) : null}
                        {loadingNfe ? (
                          <CircularProgress size={24} />
                        ) : nfeData && nfeData.nfe_data && nfeData.nfe_data.length > 0 ? (
                          <IconButton
                            color="secondary"
                            onClick={() => setShowNfeDialog(true)}
                            title="Ver Notas Fiscais"
                          >
                            <ReceiptIcon />
                          </IconButton>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                {/* Footer */}
                <TableFooter>
                  <TableRow sx={{ backgroundColor: '#e9e9e9ff' }}>
                    <TableCell colSpan={11}>
                      <Box sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        width: '100%'
                      }}>
                        <Typography variant="body2" component="div" sx={{ fontWeight: 'bold', textAlign: 'left' }}>
                          Observação: {purchase.order.observacao}
                        </Typography>
                        <Typography variant="body2" component="div" sx={{ fontWeight: 'bold', textAlign: 'right' }}>
                          Total c/ ipi: {formatCurrency(purchase.order.total_pedido_com_ipi)} Total c/ desconto: {formatCurrency(purchase.order.adjusted_total)}
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                </TableFooter>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>

      {/* NFE Dialog */}
      <Dialog
        open={showNfeDialog}
        onClose={handleDialogClose}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Notas Fiscais - Pedido {purchase.order.cod_pedc}
        </DialogTitle>
        <DialogContent>
          {loadingNfe ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : nfeData && nfeData.nfe_data ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {nfeData.nfe_data.map((nfe, index) => (
                <Card key={index} variant="outlined">
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      NF-e Nº {nfe.numero}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Fornecedor:</strong> {nfe.fornecedor}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Data Emissão:</strong> {nfe.data_emissao ? new Date(nfe.data_emissao).toLocaleDateString('pt-BR') : ''}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Valor:</strong> {nfe.valor ? formatCurrency(parseFloat(nfe.valor)) : ''}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Chave:</strong> {nfe.chave}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<PictureAsPdfIcon />}
                      onClick={() => handleNfeClick(nfe)}
                      color="primary"
                    >
                      Visualizar DANFE
                    </Button>
                  </CardActions>
                </Card>
              ))}
            </Box>
          ) : (
            <Typography>Nenhuma Nota Fiscal encontrada para este pedido.</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Fechar</Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}

const UnifiedSearch = ({ onLogout }) => {
  const SEARCH_MODE_STORAGE_KEY = 'searchModePreference';
  const DEFAULT_ENHANCED_FIELDS = ['descricao', 'item_id', 'cod_pedc', 'fornecedor', 'observacao', 'num_nf'];

  const [searchParams, setSearchParams] = useState({
    query: '',
    searchPrecision: 'precisa',
    score_cutoff: 100,
    selectedFuncName: 'todos',
    searchByCodPedc: true,
    searchByFornecedor: true,
    searchByObservacao: true,
    searchByItemId: true,
    searchByDescricao: true,
    searchByAtendido: false,
    searchByNaoAtendido: false,
    searchByNumNF: false,
    min_value: '',
    max_value: '',
    valueSearchType: 'item'
  });
  const [results, setResults] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [funcNames, setFuncNames] = useState([]); // Estado para armazenar os nomes dos compradores
  const [currentPage, setCurrentPage] = useState(1);
  const [noResults, setNoResults] = useState(0);
  const [perPage, setPerPage] = useState(200);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState('');
  const [estimatedResults, setEstimatedResults] = useState(0);
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const resultsRef = useRef(null);
  const [scrollThreshold, setScrollThreshold] = useState(300);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [searchMode, setSearchMode] = useState(() => {
    if (typeof window === 'undefined') {
      return 'classic';
    }
    return localStorage.getItem(SEARCH_MODE_STORAGE_KEY) || 'classic';
  });
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  const usingEnhanced = searchMode === 'enhanced';



  const menuItems = React.useMemo(() => ([
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Buscar Pedidos', icon: <SearchIcon />, path: '/search' },
    { text: 'Analisar Cotações', icon: <CompareIcon />, path: '/quotation-analyzer' },
    { text: 'Importar Dados', icon: <UploadIcon />, path: '/import' }
  ]), []);

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleSidebarCollapse = () => setSidebarOpen(v => !v);
  const handleNav = (path) => { try { navigate(path); } catch { window.location.assign(path); } };
  const handleLogoutTop = () => { onLogout(); try { navigate('/login', { replace: true }); } catch { window.location.replace('/login'); } };

  const isScrolledToResults = useScrollTrigger({
    disableHysteresis: true,
    threshold: scrollThreshold,
  });

  // Set sidebar visibility based on scroll position
  useEffect(() => {
    setSidebarVisible(!isScrolledToResults);
  }, [isScrolledToResults]);

  const baseDrawerWidth = sidebarOpen ? DRAWER_WIDTH_OPEN : DRAWER_WIDTH_COLLAPSED;
  const drawerWidth = sidebarVisible ? baseDrawerWidth : 0;

  const drawerContent = (
    <>
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: sidebarOpen ? 'space-between' : 'center',
          py: 1,
          px: 2
        }}
      >
        {sidebarOpen && (
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            Sistema de Compras
          </Typography>
        )}
        <IconButton size="small" onClick={handleSidebarCollapse}>
          {sidebarOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Toolbar>
      <Divider />
      <Box sx={{ py: 1 }}>
        <List sx={{ px: sidebarOpen ? 1 : 0 }}>
          {menuItems.map(item => (
            <ListItemButton
              key={item.text}
              onClick={() => handleNav(item.path)}
              sx={{
                borderRadius: 2,
                mx: sidebarOpen ? 1 : 0.5,
                mb: 0.5,
                minHeight: 44,
                justifyContent: sidebarOpen ? 'flex-start' : 'center',
                '&.Mui-selected': { bgcolor: 'primary.light', '&:hover': { bgcolor: 'primary.light' } },
                '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' }
              }}
              selected={item.path === '/search'}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: sidebarOpen ? 2 : 'auto',
                  color: item.path === '/search' ? 'primary.main' : 'inherit',
                  justifyContent: 'center'
                }}
              >
                {item.icon}
              </ListItemIcon>
              {sidebarOpen && <ListItemText primary={item.text} />}
            </ListItemButton>
          ))}
        </List>
      </Box>
    </>
  );
  useEffect(() => {
    if (resultsRef.current) {
      const resultsPosition = resultsRef.current.offsetTop - 100;
      setScrollThreshold(resultsPosition > 100 ? resultsPosition : 300);
    }
  }, [results.length]);

  useEffect(() => {
    // Buscar os nomes dos compradores do backend
    const fetchFuncNames = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/purchasers`, { withCredentials: true });
        const sortedFuncNames = response.data
          .map(name => name || 'Sem nome') // Substituir nomes nulos por "Sem nome"
          .sort((a, b) => a.localeCompare(b));

        setFuncNames(sortedFuncNames);
      } catch (error) {
        console.error('Error fetching purchasers: ', error);
      }
    };

    const fetchLastUpdate = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/last_update`, { withCredentials: true });
        if (response.data && response.data.last_updated) {
          const date = new Date(response.data.last_updated);
          setLastUpdated(date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
          }));
        }
      } catch (error) {
        console.error('Error fetching last update:', error);
        setLastUpdated('Data não disponível ');
      }
    };

    fetchLastUpdate();
    fetchFuncNames();
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(SEARCH_MODE_STORAGE_KEY, searchMode);
    }
  }, [searchMode]);

  useEffect(() => {
    if (!usingEnhanced) {
      setSuggestions([]);
      return undefined;
    }

    const term = (searchParams.query || '').trim();
    if (term.length < 2) {
      setSuggestions([]);
      return undefined;
    }

    let isActive = true;
    const handler = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const { data } = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_advanced/suggestions`, {
          params: { term, limit: 10 },
          withCredentials: true
        });
        if (isActive) {
          setSuggestions((data?.suggestions || []).map(suggestion => suggestion.value));
        }
      } catch (err) {
        if (isActive) {
          console.error('Failed to fetch suggestions', err);
        }
      } finally {
        if (isActive) {
          setLoadingSuggestions(false);
        }
      }
    }, 300);

    return () => {
      isActive = false;
      clearTimeout(handler);
    };
  }, [searchParams.query, usingEnhanced]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (name === 'searchPrecision') {
      let score_cutoff;
      if (value === 'precisa') {
        score_cutoff = 100;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff
        });
      } else if (value === 'fuzzy') {
        score_cutoff = 80;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff
        });
      } else if (value === 'tentar_a_sorte') {
        score_cutoff = 60;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff,

        });
      }
    } else {
      setSearchParams({
        ...searchParams,
        [name]: type === 'checkbox' ? checked : value
      });
    }
  };

  const updateQuery = (value) => {
    setSearchParams(prev => ({
      ...prev,
      query: value
    }));
  };

  const handleModeToggle = (event) => {
    setSearchMode(event.target.checked ? 'enhanced' : 'classic');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch(1);
    }
  };
  const resolveEnhancedFields = () => {
    const selected = [];
    if (searchParams.searchByDescricao) selected.push('descricao');
    if (searchParams.searchByItemId) selected.push('item_id');
    if (searchParams.searchByCodPedc) selected.push('cod_pedc');
    if (searchParams.searchByFornecedor) selected.push('fornecedor');
    if (searchParams.searchByObservacao) selected.push('observacao');
    if (searchParams.searchByNumNF) selected.push('num_nf');
    return selected.length ? selected : DEFAULT_ENHANCED_FIELDS;
  };

  const getEstimatedResults = async () => {
    if (usingEnhanced) {
      return;
    }
    const term = (searchParams.query || '').trim();
    if (!term) {
      setEstimatedResults(0);
      return;
    }
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/count_results`, {
        params: {
          query: term,
          score_cutoff: searchParams.score_cutoff,
          searchByCodPedc: searchParams.searchByCodPedc,
          searchByFornecedor: searchParams.searchByFornecedor,
          searchByObservacao: searchParams.searchByObservacao,
          searchByItemId: searchParams.searchByItemId,
              searchByNumNF: searchParams.searchByNumNF,
          searchByDescricao: searchParams.searchByDescricao,
          selectedFuncName: searchParams.selectedFuncName
        },
        withCredentials: true
      });
      setEstimatedResults(response.data.count);
      setTotalPages(response.data.estimated_pages);
    } catch (error) {
      console.error('Error getting estimated results:', error);
    }
  };

  const handleSearch = async (page = 1) => {
    const trimmedQuery = (searchParams.query || '').trim();
    if (!trimmedQuery) {
      setResults([]);
      setNoResults(0);
      setEstimatedResults(0);
      return;
    }

    setLoading(true);
    if (!usingEnhanced) {
      await getEstimatedResults();
    }

    try {
      let response;

      if (usingEnhanced) {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_advanced`, {
          params: {
            query: trimmedQuery,
            fields: resolveEnhancedFields().join(','),
            selectedFuncName: searchParams.selectedFuncName,
            minValue: searchParams.min_value || undefined,
            maxValue: searchParams.max_value || undefined,
            valueSearchType: searchParams.valueSearchType,
            page,
            per_page: perPage
          },
          withCredentials: true
        });
      } else {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_combined`, {
          params: {
            query: trimmedQuery,
            page,
            per_page: perPage,
            score_cutoff: searchParams.score_cutoff,
            searchByCodPedc: searchParams.searchByCodPedc,
            searchByFornecedor: searchParams.searchByFornecedor,
            searchByObservacao: searchParams.searchByObservacao,
            searchByItemId: searchParams.searchByItemId,
            searchByDescricao: searchParams.searchByDescricao,
            searchByNumNF: searchParams.searchByNumNF,
            selectedFuncName: searchParams.selectedFuncName,
            minValue: searchParams.min_value,
            maxValue: searchParams.max_value,
            valueSearchType: searchParams.valueSearchType
          },
          withCredentials: true
        });
      }

      const purchases = response.data?.purchases || [];
      setResults(purchases);
      setCurrentPage(response.data?.current_page || page);
      setTotalPages(response.data?.total_pages || 1);
      setNoResults(purchases.length);

      if (usingEnhanced) {
        setEstimatedResults(response.data?.total_results ?? purchases.length);
      }
    } catch (error) {
      console.error('Error fetching data', error);
      setResults([]);
      setCurrentPage(1);
      setTotalPages(1);
      setNoResults(0);
    } finally {
      setLoading(false);
    }
  };

  const handleItemClick = (itemId) => {
    setSelectedItemId(itemId);
  };

  const handleCloseItemScreen = () => {
    setSelectedItemId(null);
  };

  const formatDate = (dateString) => {
    const options = { day: '2-digit', month: '2-digit', year: '2-digit' };
    return new Date(dateString).toLocaleDateString('pt-BR', options);
  };

const formatNumber = (number) => {
  if (number === undefined || number === null || isNaN(parseFloat(number))) {
    return '-'; 
  }
  return parseFloat(number).toFixed(2);
};
  const formatCurrency = (number) => {
    if (number === undefined || number === null) return ''; // Verifica se o número é undefined ou null
    return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const getFirstWords = (text, numWords) => {
    if (!text) return ''; // Verifica se o texto é undefined ou null
    return text.split(' ').slice(0, numWords).join(' ');
  };


  const handlePageChange = (newPage) => {
    handleSearch(newPage);
  };

  return (
    <Box sx={{ display: 'flex' }}>
      {/* AppBar */}
      <HideOnScroll threshold={scrollThreshold}>
        <AppBar
          position="fixed"
          elevation={0}
          sx={{
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            ml: { sm: `${drawerWidth}px` },
            bgcolor: 'transparent',
            color: 'text.primary',
            backdropFilter: 'blur(6px)'
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: 'none' } }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 'bold' }}>Buscar Pedidos</Typography>
            <Typography variant="body1" sx={{ flexGrow: 1, alignContent: 'left' }}>
              Pedidos de compras Ruah - atualizado em {lastUpdated} -
              <Link to="/import" style={{ marginLeft: 8, textDecoration: 'none' }}> Atualizar </Link>
            </Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={handleLogoutTop}
              startIcon={<LogoutIcon />}
              sx={{ borderRadius: 2, textTransform: 'none' }}
            >
              Logout
            </Button>
          </Toolbar>
        </AppBar>
      </HideOnScroll>

      {/* Navigation drawers */}
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        {/* Mobile temporary drawer or when sidebar is hidden */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: sidebarVisible ? 'none' : 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH_OPEN }
          }}
        >
          {drawerContent}
        </Drawer>

        {/* Desktop permanent drawer that hides on scroll */}
        {sidebarVisible && (
          <HideSidebar threshold={scrollThreshold}>
            <Drawer
              variant="permanent"
              sx={{
                display: { xs: 'none', sm: 'block' },
                '& .MuiDrawer-paper': {
                  boxSizing: 'border-box',
                  width: baseDrawerWidth,
                  transition: theme => theme.transitions.create('width', {
                    easing: theme.transitions.easing.sharp,
                    duration: theme.transitions.duration.shortest
                  })
                }
              }}
              open
            >
              {drawerContent}
            </Drawer>
          </HideSidebar>
        )}
      </Box>

      {/* Main content - adjust width based on drawer visibility */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: `calc(100% - ${drawerWidth}px)`,
          minHeight: '100vh',
          transition: theme => theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.shortest
          }),
          bgcolor: 'linear-gradient(180deg, #f7f9fc 0%, #f2f4f7 100%)'
        }}
      >
        <Toolbar />
        <div className="unified-search">
          <Box sx={{ display: 'flex', mb: 3, alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Autocomplete
              sx={{ flexGrow: 1, minWidth: 280 }}
              fullWidth
              freeSolo
              options={suggestions}
              loading={loadingSuggestions}
              inputValue={searchParams.query}
              onInputChange={(_, newValue) => updateQuery(newValue)}
              onChange={(_, newValue) => {
                if (typeof newValue === 'string') {
                  updateQuery(newValue);
                  setTimeout(() => handleSearch(1), 0);
                }
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Buscar pedidos"
                  variant="outlined"
                  size="small"
                  placeholder="Ex.: motor 123 aço"
                  onKeyDown={handleKeyDown}
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {loadingSuggestions ? <CircularProgress color="inherit" size={18} sx={{ mr: 1 }} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    )
                  }}
                />
              )}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={usingEnhanced}
                  onChange={handleModeToggle}
                  color="primary"
                />
              }
              label={usingEnhanced ? 'Busca aprimorada' : 'Busca clássica'}
              sx={{ mr: 1 }}
            />
            <Button
              variant="contained"
              color="primary"
              onClick={() => handleSearch(1)}
              startIcon={<SearchIcon />}
            >
              Buscar
            </Button>

          </Box>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 5, mb: 5 }}>
            {/* Search fields section */}
            <FormControl component="fieldset" sx={{ minWidth: '200px' }}>
              <FormLabel component="legend">Pesquisar por...</FormLabel>
              <FormControlLabel
                control={
                  <Checkbox
                    name="searchByCodPedc"
                    checked={searchParams.searchByCodPedc}
                    onChange={handleChange}
                    disabled={searchParams.searchPrecision !== 'precisa'}
                  />
                }
                label="Código do Pedido de Compra"
                sx={{ marginBottom: '-10px' }}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="searchByFornecedor"
                    checked={searchParams.searchByFornecedor}
                    onChange={handleChange}
                    disabled={searchParams.searchPrecision !== 'precisa'}
                  />
                }
                label="Nome do Fornecedor"
                sx={{ marginBottom: '-10px' }}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="searchByObservacao"
                    checked={searchParams.searchByObservacao}
                    onChange={handleChange}
                  />
                }
                label="Observação do Pedido de Compra"
                sx={{ marginBottom: '-10px' }}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="searchByItemId"
                    checked={searchParams.searchByItemId}
                    onChange={handleChange}
                    disabled={searchParams.searchPrecision !== 'precisa'}
                  />
                }
                label="Código do Item"
                sx={{ marginBottom: '-10px' }}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    name="searchByDescricao"
                    checked={searchParams.searchByDescricao}
                    onChange={handleChange}
                  />
                }
                label="Descrição do Item"
                sx={{ marginBottom: '-10px' }}
              />
              <FormControlLabel
              control={
                <Checkbox
                  name="searchByNumNF"
                  checked={searchParams.searchByNumNF}
                  onChange={handleChange}
                />
              }
              label="Número da Nota Fiscal"
              sx={{ marginBottom: '-10px' }}
            />
            </FormControl>

            {/* Search precision section */}
            <FormControl component="fieldset" sx={{ minWidth: '200px' }}>
              <FormLabel component="legend">Precisão da busca</FormLabel>
              <RadioGroup
                name="searchPrecision"
                value={searchParams.searchPrecision}
                onChange={handleChange}
              >
                <FormControlLabel
                  value="precisa"
                  control={<Radio />}
                  label="Precisa"
                  sx={{ marginBottom: '-10px' }}
                />
                <FormControlLabel
                  value="fuzzy"
                  control={<Radio />}
                  label="Busca com erro de digitação"
                  sx={{ marginBottom: '-10px' }}
                />
                <FormControlLabel
                  value="tentar_a_sorte"
                  control={<Radio />}
                  label="Estou sem sorte"
                  sx={{ marginBottom: '-10px' }}
                />
              </RadioGroup>
            </FormControl>

            {/* Purchaser section */}
            <FormControl sx={{ minWidth: '200px' }}>
              <FormLabel component="legend">Mostrar compradores</FormLabel>
              <Select
                name="selectedFuncName"
                value={searchParams.selectedFuncName}
                onChange={handleChange}
                size="small"
                fullWidth
              >
                <MenuItem value="todos">Todos os compradores</MenuItem>
                {funcNames.map((funcName) => (
                  <MenuItem key={funcName} value={funcName}>
                    {funcName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Value filter section */}
            <FormControl component="fieldset" sx={{ minWidth: '200px' }}>
              <FormLabel component="legend">Filtrar por valor</FormLabel>
              <RadioGroup
                name="valueSearchType"
                value={searchParams.valueSearchType}
                onChange={handleChange}
              >
                <FormControlLabel
                  value="item"
                  control={<Radio />}
                  label="Valor do Item"
                  sx={{ marginBottom: '-10px' }}
                />
                <FormControlLabel
                  value="order"
                  control={<Radio />}
                  label="Valor do Pedido"
                  sx={{ marginBottom: '-10px' }}
                />
              </RadioGroup>

              <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                <TextField
                  label="Valor mínimo"
                  name="min_value"
                  type="number"
                  value={searchParams.min_value}
                  onChange={handleChange}
                  size="small"
                  InputProps={{
                    startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                  }}
                />
                <TextField
                  label="Valor máximo"
                  name="max_value"
                  type="number"
                  value={searchParams.max_value}
                  onChange={handleChange}
                  size="small"
                  InputProps={{
                    startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                  }}
                />
              </Box>
            </FormControl>
          </Box>

          {loading && (
            <Box sx={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
              zIndex: 9999
            }}>
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                <div className="spinner"></div>
              </Box>
              <Typography>
                Buscando em aproximadamente {estimatedResults} resultados...
              </Typography>
            </Box>
          )}

          <Typography variant="h6" gutterBottom ref={resultsRef}>
            Mostrando {noResults} resultados. Pagina {currentPage} de {totalPages}
          </Typography>

          <TableContainer component={Paper}>
            <Table aria-label="collapsible table">
              <TableBody>
                {results.map((purchase) => (
                  <PurchaseRow
                    key={purchase.order.cod_pedc}
                    purchase={purchase}
                    formatDate={formatDate}
                    formatNumber={formatNumber}
                    formatCurrency={formatCurrency}
                    getFirstWords={getFirstWords}
                    handleItemClick={handleItemClick}
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <div className="pagination">
            <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1}>Anterior</button>
            <span>Página {currentPage} de {totalPages}</span>
            <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages}>Próxima</button>
          </div>

          {selectedItemId && <ItemScreen itemId={selectedItemId} onClose={handleCloseItemScreen} />}
        </div>
      </Box>
    </Box>
  );
};

export default UnifiedSearch;