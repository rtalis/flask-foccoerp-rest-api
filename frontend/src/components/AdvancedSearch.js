import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Autocomplete from '@mui/material/Autocomplete';
import {
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Checkbox,
  CircularProgress,
  Divider,
  Drawer,
  FormControlLabel,
  FormGroup,
  Grid,
  IconButton,
  InputAdornment,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Pagination,
  Paper,
  Select,
  Stack,
  TextField,
  Toolbar,
  Typography,
  Alert,
  Switch
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SearchIcon from '@mui/icons-material/Search';
import ManageSearchIcon from '@mui/icons-material/ManageSearch';
import CompareIcon from '@mui/icons-material/Compare';
import UploadIcon from '@mui/icons-material/Upload';
import LogoutIcon from '@mui/icons-material/Logout';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import TuneIcon from '@mui/icons-material/Tune';
import MoneyIcon from '@mui/icons-material/AttachMoney';

const DRAWER_WIDTH_OPEN = 260;
const DRAWER_WIDTH_COLLAPSED = 60;

const DEFAULT_FIELDS = new Set(['descricao', 'item_id', 'cod_pedc', 'fornecedor', 'observacao', 'num_nf']);

const AdvancedSearch = ({ onLogout }) => {
  const SEARCH_MODE_STORAGE_KEY = 'searchModePreference';
  const navigate = useNavigate();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [searchMode, setSearchMode] = useState(() => {
    if (typeof window === 'undefined') {
      return 'enhanced';
    }
    return localStorage.getItem(SEARCH_MODE_STORAGE_KEY) || 'enhanced';
  });

  const [selectedFields, setSelectedFields] = useState(() => new Set(DEFAULT_FIELDS));
  const [ignoreDiacritics, setIgnoreDiacritics] = useState(false);
  const [selectedBuyer, setSelectedBuyer] = useState('todos');
  const [buyers, setBuyers] = useState([]);

  const [minValue, setMinValue] = useState('');
  const [maxValue, setMaxValue] = useState('');
  const [valueSearchType, setValueSearchType] = useState('item');

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalResults, setTotalResults] = useState(0);
  const [perPage, setPerPage] = useState(10);

  const usingEnhanced = searchMode === 'enhanced';

  const menuItems = useMemo(() => ([
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Buscar Pedidos', icon: <SearchIcon />, path: '/search' },
    { text: 'Busca Avançada', icon: <ManageSearchIcon />, path: '/advanced-search' },
    { text: 'Analisar Cotações', icon: <CompareIcon />, path: '/quotation-analyzer' },
    { text: 'Importar Dados', icon: <UploadIcon />, path: '/import' }
  ]), []);

  useEffect(() => {
    const fetchBuyers = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/purchasers`, { withCredentials: true });
        setBuyers(['todos', ...(response.data || [])]);
      } catch (err) {
        console.error('Failed to load buyers', err);
      }
    };
    fetchBuyers();
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

    if (!query || query.trim().length < 2) {
      setSuggestions([]);
      return undefined;
    }

    let isActive = true;
    const handler = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const res = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_advanced/suggestions`, {
          params: { term: query.trim(), limit: 10 },
          withCredentials: true
        });
        if (isActive) {
          setSuggestions(res.data?.suggestions?.map(s => s.value) || []);
        }
      } catch (err) {
        if (isActive) {
          console.error('Suggestion fetch failed', err);
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
  }, [query, usingEnhanced]);

  const toggleField = (field) => {
    setSelectedFields(prev => {
      const next = new Set(prev);
      if (next.has(field)) {
        next.delete(field);
      } else {
        next.add(field);
      }
      return next;
    });
  };

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleSidebarToggle = () => setSidebarOpen((prev) => !prev);

  const handleModeToggle = (event) => {
    setSearchMode(event.target.checked ? 'enhanced' : 'classic');
  };

  const resolveLegacyFlags = () => {
    const flags = {
      searchByCodPedc: selectedFields.has('cod_pedc'),
      searchByFornecedor: selectedFields.has('fornecedor'),
      searchByObservacao: selectedFields.has('observacao'),
      searchByItemId: selectedFields.has('item_id'),
      searchByDescricao: selectedFields.has('descricao'),
      searchByNumNF: selectedFields.has('num_nf')
    };

    if (!Object.values(flags).some(Boolean)) {
      flags.searchByDescricao = true;
    }

    return flags;
  };

  const handleSearch = async (nextPage = 1) => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError('Informe um termo de busca.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let response;

      if (usingEnhanced) {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_advanced`, {
          params: {
            query: trimmedQuery,
            fields: Array.from(selectedFields).join(','),
            ignoreDiacritics,
            selectedFuncName: selectedBuyer,
            minValue: minValue || undefined,
            maxValue: maxValue || undefined,
            valueSearchType,
            page: nextPage,
            per_page: perPage
          },
          withCredentials: true
        });
      } else {
        const legacyFlags = resolveLegacyFlags();
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_advanced`, {
          params: {
            legacy: 'true',
            query: trimmedQuery,
            page: nextPage,
            per_page: perPage,
            score_cutoff: 100,
            ...legacyFlags,
            selectedFuncName: selectedBuyer,
            minValue: minValue || undefined,
            maxValue: maxValue || undefined,
            valueSearchType,
            ignoreDiacritics
          },
          withCredentials: true
        });
      }

      const purchases = response.data?.purchases || [];
      setResults(purchases);
      setTotalPages(response.data?.total_pages || 0);
      setPage(response.data?.current_page || nextPage);
      setTotalResults(usingEnhanced ? (response.data?.total_results || purchases.length) : purchases.length);
    } catch (err) {
      const message = err?.response?.data?.error || 'Erro ao realizar a busca.';
      setError(message);
      console.error('Advanced search failed', err);
    } finally {
      setLoading(false);
    }
  };

  const drawerWidth = sidebarOpen ? DRAWER_WIDTH_OPEN : DRAWER_WIDTH_COLLAPSED;

  const drawerContent = (
    <>
      <Toolbar sx={{ display: 'flex', justifyContent: sidebarOpen ? 'space-between' : 'center', px: 2 }}>
        {sidebarOpen && (
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            Sistema de Compras
          </Typography>
        )}
        <IconButton size="small" onClick={handleSidebarToggle}>
          {sidebarOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Toolbar>
      <Divider />
      <Box sx={{ py: 1 }}>
        <List sx={{ px: sidebarOpen ? 1 : 0 }}>
          {menuItems.map(item => (
            <ListItemButton
              key={item.text}
              onClick={() => navigate(item.path)}
              selected={item.path === '/advanced-search'}
              sx={{
                borderRadius: 2,
                mx: sidebarOpen ? 1 : 0.5,
                mb: 0.5,
                minHeight: 44,
                justifyContent: sidebarOpen ? 'flex-start' : 'center',
                '&.Mui-selected': { bgcolor: 'primary.light', '&:hover': { bgcolor: 'primary.light' } },
                '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' }
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: sidebarOpen ? 2 : 'auto',
                  color: item.path === '/advanced-search' ? 'primary.main' : 'inherit',
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
      <Divider />
      <Box sx={{ px: sidebarOpen ? 2 : 1, py: 2 }}>
        <Button
          variant="outlined"
          fullWidth
          color="inherit"
          startIcon={<LogoutIcon />}
          onClick={onLogout}
        >
          {sidebarOpen ? 'Sair' : ''}
        </Button>
      </Box>
    </>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ ml: { md: `${drawerWidth}px` }, width: { md: `calc(100% - ${drawerWidth}px)` } }} color="default" elevation={1}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" component="div">
              Busca Avançada de Pedidos
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Combine termos, filtros e valores para localizar itens rapidamente.
            </Typography>
          </Box>
          <Button onClick={() => navigate('/search')} variant="outlined" color="primary">
            Voltar para busca clássica
          </Button>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }} aria-label="navigation">
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth }
          }}
        >
          {drawerContent}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              transition: 'width 0.3s ease'
            }
          }}
          open
        >
          {drawerContent}
        </Drawer>
      </Box>



      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={12}>
            <Card elevation={3}>
              <CardHeader
                avatar={<TuneIcon color="primary" />}
                title="Parâmetros de busca"
                subheader="Escolha os campos e filtros para refinar os resultados"
              />
              <CardContent>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'flex-start', md: 'center' }} mb={3}>
                  <Autocomplete
                    fullWidth
                    sx={{ width: '100%' }}
                    freeSolo
                    options={suggestions}
                    loading={loadingSuggestions}
                    inputValue={query}
                    onInputChange={(_, newValue) => setQuery(newValue)}
                    onChange={(_, newValue) => {
                      if (typeof newValue === 'string') {
                        setQuery(newValue);
                        setTimeout(() => handleSearch(1), 0);
                      }
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        fullWidth
                        label="Buscar"
                        placeholder="Ex.: motor 123 aço"
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            event.preventDefault();
                            handleSearch(1);
                          }
                        }}
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
                    sx={{ ml: { md: 2 } }}
                  />
                </Stack>

                <Grid container spacing={2}>
             
                  <Grid item xs={12} md={6}>
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                      <TextField
                        label="Valor mínimo"
                        type="number"
                        value={minValue}
                        onChange={(e) => setMinValue(e.target.value)}
                        InputProps={{ startAdornment: <InputAdornment position="start"><MoneyIcon fontSize="small" /></InputAdornment> }}
                        fullWidth
                      />
                      <TextField
                        label="Valor máximo"
                        type="number"
                        value={maxValue}
                        onChange={(e) => setMaxValue(e.target.value)}
                        InputProps={{ startAdornment: <InputAdornment position="start"><MoneyIcon fontSize="small" /></InputAdornment> }}
                        fullWidth
                      />
                      <Select
                        value={valueSearchType}
                        onChange={(e) => setValueSearchType(e.target.value)}
                        displayEmpty
                        fullWidth
                      >
                        <MenuItem value="item">Valor do item</MenuItem>
                        <MenuItem value="order">Valor total do pedido</MenuItem>
                      </Select>
                    </Stack>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <FormGroup row>
                      {['descricao', 'item_id', 'cod_pedc', 'fornecedor', 'observacao', 'num_nf'].map((field) => (
                        <FormControlLabel
                          key={field}
                          control={
                            <Checkbox
                              checked={selectedFields.has(field)}
                              onChange={() => toggleField(field)}
                              name={field}
                            />
                          }
                          label={
                            field === 'num_nf' ? 'Notas fiscais' :
                            field === 'cod_pedc' ? 'Código pedido' :
                            field === 'item_id' ? 'Item' :
                            field === 'descricao' ? 'Descrição' :
                            field === 'fornecedor' ? 'Fornecedor' : 'Observação'
                          }
                        />
                      ))}
                    </FormGroup>
                    <FormControlLabel
                      control={<Checkbox checked={ignoreDiacritics} onChange={(_, checked) => setIgnoreDiacritics(checked)} />}
                      label="Ignorar acentuação"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                      <Select
                        value={selectedBuyer}
                        onChange={(e) => setSelectedBuyer(e.target.value)}
                        fullWidth
                        displayEmpty
                      >
                        {buyers.map((buyer) => (
                          <MenuItem key={buyer || 'todos'} value={buyer || 'todos'}>
                            {buyer || 'todos'}
                          </MenuItem>
                        ))}
                      </Select>
                      <Select value={perPage} onChange={(e) => setPerPage(Number(e.target.value))} fullWidth>
                        {[5, 10, 20, 50].map((size) => (
                          <MenuItem key={size} value={size}>
                            {size} por página
                          </MenuItem>
                        ))}
                      </Select>
                      <Button variant="contained" color="primary" onClick={() => handleSearch(1)}>
                        Buscar
                      </Button>
                    </Stack>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {error && (
            <Grid item xs={12}>
              <Alert severity="error">{error}</Alert>
            </Grid>
          )}

          <Grid item xs={12}>
            <Paper elevation={1} sx={{ p: 2 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} spacing={2}>
                <Box>
                  <Typography variant="h6">Resultados</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {totalResults ? `${totalResults} itens encontrados` : 'Nenhum resultado ainda.'}
                  </Typography>
                </Box>
                {totalPages > 1 && (
                  <Pagination
                    count={totalPages}
                    page={page}
                    onChange={(_, value) => {
                      setPage(value);
                      handleSearch(value);
                    }}
                    color="primary"
                  />
                )}
              </Stack>

              <Divider sx={{ my: 2 }} />

              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
                  <CircularProgress />
                </Box>
              ) : results.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Informe um termo e clique em buscar para visualizar os resultados.
                </Typography>
              ) : (
                <Stack spacing={2}>
                  {results.map((purchase) => (
                    <Card key={purchase.order.cod_pedc} variant="outlined">
                      <CardHeader
                        title={`${purchase.order.cod_pedc} — ${purchase.order.fornecedor_descricao || 'Fornecedor não informado'}`}
                        subheader={`Emitido em ${purchase.order.dt_emis || '—'} · Comprador: ${purchase.order.func_nome || '—'}`}
                        action={
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Typography variant="subtitle2" color="text.secondary">
                              Total ajustado
                            </Typography>
                            <Typography variant="h6" color="primary">
                              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(purchase.order.adjusted_total || purchase.order.total_pedido_com_ipi || 0)}
                            </Typography>
                          </Stack>
                        }
                      />
                      <CardContent>
                        <Stack spacing={1} sx={{ mb: 2 }}>
                          {purchase.order.observacao && (
                            <Typography variant="body2" color="text.secondary">
                              Observação: {purchase.order.observacao}
                            </Typography>
                          )}
                          {purchase.order.nfes && purchase.order.nfes.length > 0 && (
                            <Typography variant="body2" color="text.secondary">
                              NF-es encontradas: {purchase.order.nfes.map(nfe => nfe.num_nf).join(', ')}
                            </Typography>
                          )}
                        </Stack>
                        <Paper variant="outlined" sx={{ overflowX: 'auto' }}>
                          <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse' }}>
                            <Box component="thead" sx={{ bgcolor: 'grey.100' }}>
                              <Box component="tr">
                                <Box component="th" sx={{ textAlign: 'left', p: 1 }}>Item</Box>
                                <Box component="th" sx={{ textAlign: 'left', p: 1 }}>Descrição</Box>
                                <Box component="th" sx={{ textAlign: 'right', p: 1 }}>Qtde</Box>
                                <Box component="th" sx={{ textAlign: 'right', p: 1 }}>Valor unitário</Box>
                                <Box component="th" sx={{ textAlign: 'right', p: 1 }}>Total</Box>
                              </Box>
                            </Box>
                            <Box component="tbody">
                              {purchase.items.map((item) => (
                                <Box component="tr" key={item.id} sx={{ '&:nth-of-type(odd)': { bgcolor: 'grey.50' } }}>
                                  <Box component="td" sx={{ p: 1 }}>{item.item_id}</Box>
                                  <Box component="td" sx={{ p: 1 }}>{item.descricao}</Box>
                                  <Box component="td" sx={{ p: 1, textAlign: 'right' }}>{item.quantidade}</Box>
                                  <Box component="td" sx={{ p: 1, textAlign: 'right' }}>
                                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.preco_unitario || 0)}
                                  </Box>
                                  <Box component="td" sx={{ p: 1, textAlign: 'right' }}>
                                    {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.total || 0)}
                                  </Box>
                                </Box>
                              ))}
                            </Box>
                          </Box>
                        </Paper>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              )}
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default AdvancedSearch;
