import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
  Box, Container, Grid, Paper, Typography, Card, CardContent, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, AppBar,
  Toolbar, Button, Drawer, List, ListItemButton, ListItemIcon, ListItemText,LinearProgress,
  IconButton, Divider, CircularProgress, Alert, MenuItem, Select, FormControl, InputLabel,
  Tabs, Tab, Chip, Dialog, DialogTitle, DialogContent, DialogActions, Radio, RadioGroup, FormControlLabel
} from '@mui/material';
import {
  Menu as MenuIcon, Dashboard as DashboardIcon, Search as SearchIcon,
  ManageSearch as ManageSearchIcon, Compare as CompareIcon, Upload as UploadIcon, Logout as LogoutIcon,
  ShoppingCart as ShoppingCartIcon, Receipt as ReceiptIcon, Business as BusinessIcon,
  TrendingUp as TrendingUpIcon, ChevronLeft as ChevronLeftIcon, ChevronRight as ChevronRightIcon,
  Refresh as RefreshIcon, Link as LinkIcon,
  CheckCircle as CheckCircleIcon, Error as ErrorIcon, Warning as WarningIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
} from '@mui/icons-material';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, Title, Tooltip as ChartTooltip, Legend, ArcElement
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import { ptBR } from 'date-fns/locale';
import './Dashboard.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, ChartTooltip, Legend, ArcElement);

const DRAWER_WIDTH_OPEN = 260;
const DRAWER_WIDTH_COLLAPSED = 80;

const Dashboard = ({ onLogout }) => {
  const [data, setData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);
  const [months, setMonths] = useState(6);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [purchaseData, setPurchaseData] = useState([]);
  const [purchaseLoading, setPurchaseLoading] = useState(false);
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setMonth(new Date().getMonth() - 1)),
    end: new Date()
  });
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'pending', 'partial', 'complete'
  const [matchDialogOpen, setMatchDialogOpen] = useState(false);
  const [currentPurchase, setCurrentPurchase] = useState(null);
  const [currentItem, setCurrentItem] = useState(null);
  const [suggestedNFEs, setSuggestedNFEs] = useState([]);
  const [selectedNFE, setSelectedNFE] = useState(null);
  const [nfeLoading, setNfeLoading] = useState(false);
  const [userInfo, setUserInfo] = useState(null);

  const [suggestedMatches, setSuggestedMatches] = useState([]);
  const [suggestedMatchesLoading, setSuggestedMatchesLoading] = useState(false);


  const navigate = useNavigate();

  const menuItems = useMemo(() => ([
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Buscar Pedidos', icon: <SearchIcon />, path: '/search' },
    { text: 'Analisar Cotações', icon: <CompareIcon />, path: '/quotation-analyzer' },
    { text: 'Importar Dados', icon: <UploadIcon />, path: '/import' }
  ]), []);

  const fetchData = async (m) => {
    try {
      setLoading(true);
      setError('');
      const res = await axios.get(`${process.env.REACT_APP_API_URL}/api/dashboard_summary`, {
        params: { months: m, limit: m + 2 },
        withCredentials: true
      });
      const d = res.data || {};
      setData({
        summary: {
          total_orders: Number(d?.summary?.total_orders ?? 0),
          total_items: Number(d?.summary?.total_items ?? 0),
          total_value: Number(d?.summary?.total_value ?? 0),
          avg_order_value: Number(d?.summary?.avg_order_value ?? 0),
          total_suppliers: Number(d?.summary?.total_suppliers ?? 0),
        },
        buyer_data: Array.isArray(d?.buyer_data) ? d.buyer_data.map(x => ({
          name: String(x?.name ?? ''),
          order_count: Number(x?.order_count ?? 0),
          total_value: Number(x?.total_value ?? 0),
          avg_value: Number(x?.avg_value ?? 0),
          item_count: Number(x?.item_count ?? 0),
        })) : [],
        supplier_data: Array.isArray(d?.supplier_data) ? d.supplier_data.map(x => ({
          name: String(x?.name ?? ''),
          order_count: Number(x?.order_count ?? 0),
          total_value: Number(x?.total_value ?? 0),
        })) : [],
        top_items: Array.isArray(d?.top_items) ? d.top_items.map(x => ({
          item_id: String(x?.item_id ?? ''),
          descricao: String(x?.descricao ?? ''),
          total_spend: Number(x?.total_spend ?? 0),
        })) : [],
        recent_orders: Array.isArray(d?.recent_orders) ? d.recent_orders.map(x => ({
          cod_pedc: String(x?.cod_pedc ?? ''),
          dt_emis: x?.dt_emis ?? null,
          fornecedor_descricao: String(x?.fornecedor_descricao ?? ''),
          func_nome: String(x?.func_nome ?? ''),
          total_value: Number(x?.total_value ?? 0),
        })) : [],
        monthly_data: Array.isArray(d?.monthly_data) ? d.monthly_data.map(x => ({
          month: String(x?.month ?? ''),
          order_count: Number(x?.order_count ?? 0),
          total_value: Number(x?.total_value ?? 0),
        })) : []
      });
    } catch (e) {
      console.error(e);
      setError('Erro ao carregar dados do dashboard');
    } finally {
      setLoading(false);
    }
  };



  const fetchUserInfo = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/auth/me`, {
        withCredentials: true
      });
      setUserInfo(response.data);
    } catch (err) {
      console.error('Error fetching user info:', err);
    }
  };

  const fetchPurchases = async () => {
    try {
      setPurchaseLoading(true);
      const startFormatted = dateRange.start.toISOString().split('T')[0];
      const endFormatted = dateRange.end.toISOString().split('T')[0];

      // Fetch purchases
      const purchaseResponse = await axios.get(`${process.env.REACT_APP_API_URL}/api/user_purchases`, {
        params: {
          start_date: startFormatted,
          end_date: endFormatted,
          status: statusFilter,
          username: userInfo?.username
        },
        withCredentials: true
      });

      // Fetch probability matches
      const matchesResponse = await axios.get(`${process.env.REACT_APP_API_URL}/api/auto_match_nfes`, {
        params: {
          start_date: startFormatted,
          end_date: endFormatted,
          min_score: 0, // Get all matches to show probability for all
          limit: 100
        },
        withCredentials: true
      });

      const purchaseData = purchaseResponse.data;
      const matchesData = matchesResponse.data || [];

      const enhancedPurchaseData = purchaseData.map(purchase => {
        const match = matchesData.find(m => m.purchase_order.cod_pedc === purchase.cod_pedc);
        return {
          ...purchase,
          matchProbability: match ? match.best_match.score : null,
          matchDetails: match ? match.best_match : null,
          status: match && match.best_match.score >= 85 ? 'probable_match' : purchase.status
        };
      });

      setPurchaseData(enhancedPurchaseData);
    } catch (err) {
      console.error('Error fetching purchases:', err);
    } finally {
      setPurchaseLoading(false);
    }
  };

  const handleMarkAsInvoiced = async (purchaseId, itemId) => {
    try {
      setNfeLoading(true);
      setMatchDialogOpen(true);

      const purchase = purchaseData.find(p => p.id === purchaseId);
      const item = purchase?.items.find(i => i.id === itemId);

      setCurrentPurchase(purchase);
      setCurrentItem(item);

      // If the item already has NFEs, we'll just load them for viewing
      if (item.nfes && item.nfes.length > 0) {
        // Item already has NFEs, just load them for viewing
        setSuggestedNFEs([]);
      } else {
        // Call the API to get NFE match suggestions
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/match_purchase_nfe/${purchase.cod_pedc}`,
          { withCredentials: true }
        );

        setSuggestedNFEs(response.data.results || []);
      }
    } catch (err) {
      console.error('Error preparing invoice options:', err);
    } finally {
      setNfeLoading(false);
    }
  };

  const fetchAutoMatchedNFEs = async () => {
    try {
      setSuggestedMatchesLoading(true);
      const startFormatted = dateRange.start.toISOString().split('T')[0];
      const endFormatted = dateRange.end.toISOString().split('T')[0];

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/auto_match_nfes`, {
        params: {
          start_date: startFormatted,
          end_date: endFormatted,
          min_score: 60, // Only show high-confidence matches
          limit: 10
        },
        withCredentials: true
      });

      setSuggestedMatches(response.data);
    } catch (err) {
      console.error('Error fetching auto-matched NFEs:', err);
    } finally {
      setSuggestedMatchesLoading(false);
    }
  };

  const handleMarkAsCompleted = async () => {
    if (!currentPurchase || !currentItem) return;

    try {
      await axios.post(
        `${process.env.REACT_APP_API_URL}/api/assign_nfe_to_item`,
        {
          purchase_id: currentPurchase.id,
          item_id: currentItem.id,
          nfe_id: null, // No NFE
          quantity: currentItem.quantidade,
          mark_as_completed: true // New flag
        },
        { withCredentials: true }
      );

      setMatchDialogOpen(false);
      setSelectedNFE(null);

      // Refresh purchase data
      //fetchPurchases();

    } catch (err) {
      console.error('Error marking as completed:', err);
    }
  };

  const handleViewDanfe = (nfeId, nfeChave) => {
    if (nfeChave) {
      window.open(`${process.env.REACT_APP_API_URL}/api/view_danfe_template_by_key/${nfeChave}`, '_blank');
    } else {
      window.open(`${process.env.REACT_APP_API_URL}/api/view_danfe_template/${nfeId}`, '_blank');
    }
  };

  const handleAssignNFE = async () => {
    if (!selectedNFE || !currentPurchase || !currentItem) return;

    try {
      await axios.post(
        `${process.env.REACT_APP_API_URL}/api/assign_nfe_to_item`,
        {
          purchase_id: currentPurchase.id,
          item_id: currentItem.id,
          nfe_id: selectedNFE.nfe.id,
          quantity: currentItem.quantidade
        },
        { withCredentials: true }
      );

      setMatchDialogOpen(false);
      setSelectedNFE(null);

      // Refresh purchase data
      //fetchPurchases(); disabled while not fully implemented
    } catch (err) {
      console.error('Error assigning NFE:', err);
    }
  };

  useEffect(() => {
    fetchData(months);
  }, [months]);

  // Handle date range change and load monthly chart
  const handleDateRangeChange = (type, newValue) => {
    setDateRange(prev => ({ ...prev, [type]: newValue }));
  };


  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleSidebarCollapse = () => setSidebarOpen(v => !v);
  const handleNav = (path) => { navigate(path); };
  const handleLogout = () => { onLogout(); navigate('/login'); };
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    const statusMap = {
      0: 'pending',
      1: 'partial',
      2: 'fulfilled'
    };

    setStatusFilter(statusMap[newValue]);
  };

  const fmtCurrency = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v || 0));
  const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('pt-BR') : '—');

  // Monthly line (total value)
  const monthlyChart = useMemo(() => {
    const rows = Array.isArray(data?.monthly_data) ? data.monthly_data : [];
    return {
      labels: rows.map(r => String(r?.month ?? '')),
      datasets: [
        {
          label: 'Valor Total (R$)',
          data: rows.map(r => Number(r?.total_value ?? 0)),
          borderColor: '#5b8def',
          backgroundColor: 'rgba(91, 141, 239, 0.15)',
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: '#fff',
          pointBorderColor: '#5b8def',
          pointBorderWidth: 2
        }
      ]
    };
  }, [data]);

  // Buyer purchases chart data
  const buyerPurchasesChart = useMemo(() => {
    const rows = Array.isArray(data?.buyer_data) ? data.buyer_data : [];
    if (!rows.length) return null;
    return {
      labels: rows.map(r => String(r?.name ?? '')),
      datasets: [{
        label: 'Número de Pedidos',
        data: rows.map(r => Number(r?.order_count ?? 0)),
        backgroundColor: ['#5b8def', '#68c2ff', '#f57c00', '#7b1fa2', '#ef7171', '#a5b0c2', '#fad776', '#8fe3a6'],
        borderWidth: 1
      }]
    };
  }, [data]);

  // buyer Items Chart data
  const buyerItemsChart = useMemo(() => {
    const rows = Array.isArray(data?.buyer_data) ? data.buyer_data : [];
    if (!rows.length) return null;
    return {
      labels: rows.map(r => String(r?.name ?? '')),
      datasets: [{
        label: 'Quantidade de Itens',
        data: rows.map(r => Number(r?.item_count ?? 0)),
        backgroundColor: ['#6dd3c2', '#5b8def', '#fad776', '#c69df6', '#ef7171', '#68c2ff', '#a5b0c2', '#8fe3a6'],
        borderWidth: 1
      }]
    };
  }, [data]);

  const buyerChart = useMemo(() => {
    const rows = Array.isArray(data?.buyer_data) ? data.buyer_data : [];
    if (!rows.length) return null;
    return {
      labels: rows.map(r => String(r?.name ?? '')),
      datasets: [{
        label: 'Valor por Comprador',
        data: rows.map(r => Number(r?.total_value ?? 0)),
        backgroundColor: ['#5b8def', '#6dd3c2', '#fad776', '#c69df6', '#ef7171', '#68c2ff', '#a5b0c2', '#8fe3a6']
      }]
    };
  }, [data]);

  const safeText = (v) => {
    if (v == null) return '—';
    if (React.isValidElement(v)) return '—';
    if (v instanceof Date) return v.toLocaleDateString('pt-BR');
    const t = typeof v;
    if (t === 'string' || t === 'number' || t === 'boolean') return v;
    try { return String(v); } catch { return '—'; }
  };

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
              selected={item.path === '/dashboard'}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: sidebarOpen ? 2 : 'auto',
                  color: item.path === '/dashboard' ? 'primary.main' : 'inherit',
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

  const getStatusChip = (status, matchProbability = null) => {
    // If we have a high probability match but status isn't fulfilled yet
    if (status === 'probable_match') {
      return <Chip
        icon={<CheckCircleIcon />}
        label="Provável Faturado"
        color="info"
        size="small"
        variant="outlined"
        sx={{ background: 'rgba(3, 169, 244, 0.1)' }}
      />;
    }

    // Existing status logic
    switch (status) {
      case 'fulfilled':
        return <Chip
          icon={<CheckCircleIcon />}
          label="Atendido"
          color="success"
          size="small"
          variant="outlined"
        />;
      case 'partial':
        return <Chip
          icon={<WarningIcon />}
          label="Parcial"
          color="warning"
          size="small"
          variant="outlined"
        />;
      case 'pending':
      default:
        return <Chip
          icon={<ErrorIcon />}
          label="Pendente"
          color="error"
          size="small"
          variant="outlined"
        />;
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }
  if (error) {
    return <Container><Alert severity="error" sx={{ mt: 2 }}>{error}</Alert></Container>;
  }

  const drawerWidth = sidebarOpen ? DRAWER_WIDTH_OPEN : DRAWER_WIDTH_COLLAPSED;

  return (
    <Box sx={{ display: 'flex' }}>
      {/* AppBar */}
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
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 'bold' }}>Dashboard</Typography>
          <FormControl size="small" sx={{ mr: 2, minWidth: 150 }}>
            <Select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              displayEmpty
              sx={{ borderRadius: 2, bgcolor: 'white' }}
            >
              <MenuItem value={3}>Últimos 3 meses</MenuItem>
              <MenuItem value={6}>Últimos 6 meses</MenuItem>
              <MenuItem value={12}>Últimos 12 meses</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="contained"
            color="primary"
            onClick={handleLogout}
            startIcon={<LogoutIcon />}
            sx={{ borderRadius: 2, textTransform: 'none' }}
          >
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      {/* Navigation drawers */}
      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        {/* Mobile temporary */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH_OPEN }
          }}
        >
          {drawerContent}
        </Drawer>

        {/* Desktop permanent (retractible) */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
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
      </Box>

      {/* Main */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          bgcolor: 'linear-gradient(180deg, #f7f9fc 0%, #f2f4f7 100%)'
        }}
      >
        <Toolbar />
        <Container maxWidth="xl" sx={{ px: { xs: 0, sm: 2 } }}>
          {/* Hero strip */}
          <Box
            sx={{
              mb: 3,
              p: 3,
              borderRadius: 3,
              background: 'linear-gradient(135deg, #5b8def 0%, #6dd3c2 100%)',
              color: 'white',
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)'
            }}
          >
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
              Visão Geral de Compras
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {userInfo && `Olá, ${userInfo.username}. `}
              Acompanhe seus pedidos e faturamentos ativos.
            </Typography>
          </Box>

          {/* Purchase Tracking */}
          {/* Disabled while not working */}
          { false && (
          <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 8px 24px rgba(0,0,0,0.06)', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
              Acompanhamento de Pedidos
            </Typography>

            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
              <Tabs value={tabValue} onChange={handleTabChange} aria-label="purchase tabs">
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <ErrorIcon sx={{ mr: 1, fontSize: 20 }} />
                      Pendentes
                    </Box>
                  }
                />
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <WarningIcon sx={{ mr: 1, fontSize: 20 }} />
                      Parciais
                    </Box>
                  }
                />
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <CheckCircleIcon sx={{ mr: 1, fontSize: 20 }} />
                      Atendidos
                    </Box>
                  }
                />
              </Tabs>
            </Box>

            {/* Filter controls */}
            <Box sx={{ mb: 3, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
              <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ptBR}>
                <DatePicker
                  label="Data Inicial"
                  value={dateRange.start}
                  onChange={(newValue) => handleDateRangeChange('start', newValue)}
                  slotProps={{ textField: { size: 'small', sx: { width: 180 } } }}
                  format="dd/MM/yyyy"
                />

                <DatePicker
                  label="Data Final"
                  value={dateRange.end}
                  onChange={(newValue) => handleDateRangeChange('end', newValue)}
                  slotProps={{ textField: { size: 'small', sx: { width: 180 } } }}
                  format="dd/MM/yyyy"
                />
              </LocalizationProvider>

              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={(e) => {
                    const newStatus = e.target.value;
                    setStatusFilter(newStatus);
                    if (newStatus === 'pending') setTabValue(0);
                    else if (newStatus === 'partial') setTabValue(1);
                    else if (newStatus === 'fulfilled') setTabValue(2);
                    else setTabValue(0); // Default to first tab for 'all'
                  }}
                  label="Status"
                >
                  <MenuItem value="all">Todos</MenuItem>
                  <MenuItem value="pending">Pendentes</MenuItem>
                  <MenuItem value="partial">Parciais</MenuItem>
                  <MenuItem value="fulfilled">Atendidos</MenuItem>
                </Select>
              </FormControl>

              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                //onClick={fetchPurchases} disabled while not fully implemented
                sx={{ height: 40 }}
              >
                Atualizar
              </Button>


            </Box>

            {/* Purchases table */}
            {purchaseLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : purchaseData.length > 0 ? (
              <TableContainer>
                <Table sx={{ minWidth: 650 }}>
                  <TableHead>
                    <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                      <TableCell>Nº Pedido</TableCell>
                      <TableCell>Data</TableCell>
                      <TableCell>Fornecedor</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Valor Total</TableCell>
                      <TableCell>Ações</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {purchaseData.map((purchase) => (
                      <React.Fragment key={purchase.id}>
                        <TableRow
                          hover
                          id={`purchase-${purchase.id}`}
                          key={purchase.id}
                          sx={{
                            // Add subtle background color for high probability matches
                            backgroundColor: purchase.matchProbability >= 80 ? 'rgba(33, 150, 243, 0.05)' : 'inherit'
                          }}
                        >
                          <TableCell>{purchase.cod_pedc}</TableCell>
                          <TableCell>{fmtDate(purchase.dt_emis)}</TableCell>
                          <TableCell>{purchase.fornecedor_descricao}</TableCell>
                          <TableCell>
                            {getStatusChip(purchase.status, purchase.matchProbability)}

                            {/* Add match probability indicator if available */}
                            {purchase.matchProbability && (
                              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                                <Box sx={{
                                  width: '100%',
                                  mr: 1,
                                  height: 4,
                                  borderRadius: 2,
                                  bgcolor: 'background.paper',
                                  position: 'relative'
                                }}>
                                  <Box sx={{
                                    position: 'absolute',
                                    left: 0,
                                    top: 0,
                                    height: '100%',
                                    borderRadius: 2,
                                    width: `${purchase.matchProbability}%`,
                                    bgcolor:
                                      purchase.matchProbability > 85 ? 'info.main' :
                                        purchase.matchProbability > 70 ? 'success.main' :
                                          purchase.matchProbability > 50 ? 'warning.main' : 'error.main'
                                  }} />
                                </Box>
                                <Typography variant="caption" color="text.secondary">{Math.round(purchase.matchProbability)}%</Typography>
                              </Box>
                            )}
                          </TableCell>
                          <TableCell>{fmtCurrency(purchase.total_pedido_com_ipi)}</TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <IconButton
                                size="small"
                                onClick={() => {
                                  // Toggle expanded row
                                  const updatedData = purchaseData.map(p =>
                                    p.id === purchase.id
                                      ? { ...p, expanded: !p.expanded }
                                      : p
                                  );
                                  setPurchaseData(updatedData);
                                }}
                              >
                                {purchase.expanded ?
                                  <KeyboardArrowUpIcon /> :
                                  <KeyboardArrowDownIcon />
                                }
                              </IconButton>

                              {/* Show process button for high probability matches */}
                              {purchase.matchProbability >= 70 && purchase.status !== 'fulfilled' && (
                                <Button
                                  variant="outlined"
                                  color="primary"
                                  size="small"
                                  sx={{ ml: 1 }}
                                  startIcon={<ReceiptIcon />}
                                  onClick={() => {
                                    // If there's match details, open the dialog to process the match
                                    if (purchase.matchDetails && purchase.items.length > 0) {
                                      setCurrentPurchase(purchase);
                                      setCurrentItem(purchase.items[0]); // Select first item
                                      setSelectedNFE({
                                        nfe: purchase.matchDetails.nfe,
                                        score: purchase.matchProbability
                                      });
                                      setMatchDialogOpen(true);
                                    }
                                  }}
                                >
                                  Processar NFE
                                </Button>
                              )}
                            </Box>
                          </TableCell>
                        </TableRow>

                        {/* Expanded row for items */}
                        {purchase.expanded && (
                          <TableRow>
                            <TableCell colSpan={6} sx={{ py: 0 }}>
                              <Box sx={{ margin: 1 }}>
                                <Typography variant="subtitle2" gutterBottom component="div">
                                  Itens do Pedido
                                </Typography>
                                <Table size="small" aria-label="items">
                                  <TableHead>
                                    <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                                      <TableCell>Item</TableCell>
                                      <TableCell>Descrição</TableCell>
                                      <TableCell>Quantidade</TableCell>
                                      <TableCell>Qtd. Atendida</TableCell>
                                      <TableCell>NFEs</TableCell>
                                      <TableCell>Ações</TableCell>
                                    </TableRow>
                                  </TableHead>
                                  <TableBody>
                                    {purchase.items.map((item) => (
                                      <TableRow key={item.id}>
                                        <TableCell>{item.item_id}</TableCell>
                                        <TableCell>{item.descricao}</TableCell>
                                        <TableCell>{item.quantidade} {item.unidade_medida}</TableCell>
                                        <TableCell>
                                          {item.qtde_atendida || 0} {item.unidade_medida}
                                          {' '}
                                          ({Math.round((item.qtde_atendida || 0) / item.quantidade * 100)}%)
                                        </TableCell>

                                        <TableCell>
                                          {item.nfes && item.nfes.length > 0 ? (
                                            <Box>
                                              {item.nfes.map(nfe => (
                                                <Chip
                                                  key={nfe.id}
                                                  label={nfe.num_nf}
                                                  size="small"
                                                  sx={{ mr: 0.5, mb: 0.5 }}
                                                  variant="outlined"
                                                  onClick={() => {
                                                    // View NFE details or PDF
                                                  }}
                                                />
                                              ))}
                                            </Box>
                                          ) : (
                                            "Sem NFEs vinculadas"
                                          )}
                                        </TableCell>
                                        <TableCell>

                                          <Button
                                            variant="outlined"
                                            color="primary"
                                            size="small"
                                            startIcon={<LinkIcon />}
                                            onClick={() => handleMarkAsInvoiced(purchase.id, item.id)}
                                          >
                                            Marcar como Faturado
                                          </Button>
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                    {purchase.matchProbability && purchase.matchDetails && (
  <Box sx={{ mt: 2, mb: 1, p: 2, bgcolor: 'rgba(33, 150, 243, 0.05)', borderRadius: 2 }}>
    <Typography variant="subtitle2" gutterBottom>
      NFE Correspondente Encontrada (Probabilidade: {Math.round(purchase.matchProbability)}%)
    </Typography>
    
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6}>
        <Typography variant="body2">
          <strong>NFE:</strong> {purchase.matchDetails.nfe.numero} (Série: {purchase.matchDetails.nfe.serie})
        </Typography>
        <Typography variant="body2">
          <strong>Chave:</strong> {purchase.matchDetails.nfe.chave}
        </Typography>
        <Typography variant="body2">
          <strong>Emitente:</strong> {purchase.matchDetails.nfe.emitente}
        </Typography>
      </Grid>
      <Grid item xs={12} sm={6}>
        <Typography variant="body2">
          <strong>Data Emissão:</strong> {fmtDate(purchase.matchDetails.nfe.data_emissao)}
        </Typography>
        <Typography variant="body2">
          <strong>Valor Total:</strong> {fmtCurrency(purchase.matchDetails.nfe.valor_total)}
        </Typography>
        <Button
          variant="contained"
          color="primary"
          size="small"
          startIcon={<ReceiptIcon />}
          onClick={() => handleViewDanfe(purchase.matchDetails.nfe.id, purchase.matchDetails.nfe.chave)}
          sx={{ mt: 1 }}
        >
          Visualizar DANFE
        </Button>
      </Grid>
    </Grid>
  </Box>
)}
                                  </TableBody>
                                </Table>
                              </Box>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  Nenhum pedido encontrado para o período selecionado.
                </Typography>
              </Box>
            )}
          </Paper>
          )}
          {/* Disabled */}



          {/* Monthly Chart  */}

          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.06)',
                  width: '96%',
                  maxWidth: '100%'
                }}
              >
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                  Total de Compras por Mês
                </Typography>
                <Box
                  sx={{
                    height: { xs: 350, md: 400 },
                    width: '100%',
                    mx: 'auto'
                  }}
                >
                  {data.monthly_data?.length > 0 ? (
                    <Line
                      data={monthlyChart}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        resizeDelay: 100,
                        plugins: {
                          legend: { position: 'top' },
                          tooltip: {
                            backgroundColor: 'white',
                            titleColor: '#222',
                            bodyColor: '#222',
                            borderColor: '#e1e1e1',
                            borderWidth: 1,
                            padding: 12,
                            boxPadding: 6,
                            usePointStyle: true,
                            callbacks: {
                              label: (ctx) => `R$ ${ctx.parsed.y.toLocaleString('pt-BR')}`
                            }
                          }
                        },
                        scales: {
                          y: {
                            beginAtZero: true,
                            grid: { borderDash: [5, 5], color: 'rgba(0,0,0,0.06)' },
                            ticks: { callback: v => `R$ ${Number(v).toLocaleString('pt-BR')}` }
                          },
                          x: { grid: { display: false } }
                        }
                      }}
                    />
                  ) : (
                    <Typography variant="body2" sx={{ color: 'text.secondary', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      Sem dados para o período selecionado.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>
          </Grid>


          {/* KPIs */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card className="summary-card" sx={{ borderRadius: 3, p: 0.5 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ width: 50, height: 50, borderRadius: 2, bgcolor: 'rgba(91,141,239,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', mr: 2 }}>
                      <ShoppingCartIcon sx={{ color: '#5b8def' }} />
                    </Box>
                    <Box>
                      <Typography sx={{ color: 'text.secondary', fontWeight: 500 }} gutterBottom>Pedidos</Typography>
                      <Typography variant="h4">{data?.summary?.total_orders || 0}</Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card className="summary-card" sx={{ borderRadius: 3, p: 0.5 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ width: 50, height: 50, borderRadius: 2, bgcolor: 'rgba(104,194,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', mr: 2 }}>
                      <ReceiptIcon sx={{ color: '#68c2ff' }} />
                    </Box>
                    <Box>
                      <Typography sx={{ color: 'text.secondary', fontWeight: 500 }} gutterBottom>Itens</Typography>
                      <Typography variant="h4">{data?.summary?.total_items || 0}</Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card className="summary-card" sx={{ borderRadius: 3, p: 0.5 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ width: 50, height: 50, borderRadius: 2, bgcolor: 'rgba(245,124,0,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', mr: 2 }}>
                      <TrendingUpIcon sx={{ color: '#f57c00' }} />
                    </Box>
                    <Box>
                      <Typography sx={{ color: 'text.secondary', fontWeight: 500 }} gutterBottom>Total</Typography>
                      <Typography variant="h5">{fmtCurrency(data?.summary?.total_value || 0)}</Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card className="summary-card" sx={{ borderRadius: 3, p: 0.5 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ width: 50, height: 50, borderRadius: 2, bgcolor: 'rgba(123,31,162,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', mr: 2 }}>
                      <BusinessIcon sx={{ color: '#7b1fa2' }} />
                    </Box>
                    <Box>
                      <Typography sx={{ color: 'text.secondary', fontWeight: 500 }} gutterBottom>Média Pedido</Typography>
                      <Typography variant="h5">{fmtCurrency(data?.summary?.avg_order_value || 0)}</Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Charts */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} lg={4}>
              <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 8px 24px rgba(0,0,0,0.06)' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                  Valor total dos pedidos por Comprador
                </Typography>
                <Box sx={{ height: 350 }}>
                  {data?.buyer_data?.length > 0 ? (
                    <Doughnut
                      data={buyerChart}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } },
                          tooltip: {
                            backgroundColor: 'white',
                            titleColor: '#222',
                            bodyColor: '#222',
                            borderColor: '#e1e1e1',
                            borderWidth: 1,
                            padding: 12,
                            callbacks: {
                              label: (ctx) => `R$ ${ctx.raw.toLocaleString('pt-BR')}`
                            }
                          }
                        },
                        cutout: '60%'
                      }}
                    />
                  ) : (
                    <Typography variant="body2" sx={{ color: 'text.secondary', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      Sem dados para exibir.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} lg={4}>
              <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 8px 24px rgba(0,0,0,0.06)' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                  Quantidade de Pedidos por Comprador
                </Typography>
                <Box sx={{ height: 350 }}>
                  {data?.buyer_data?.length > 0 ? (
                    <Doughnut
                      data={buyerPurchasesChart}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } },
                          tooltip: {
                            backgroundColor: 'white',
                            titleColor: '#222',
                            bodyColor: '#222',
                            borderColor: '#e1e1e1',
                            borderWidth: 1,
                            padding: 12
                          }
                        },
                        cutout: '60%'
                      }}
                    />
                  ) : (
                    <Typography variant="body2" sx={{ color: 'text.secondary', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      Sem dados para o período.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} lg={4}>
              <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 8px 24px rgba(0,0,0,0.06)' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
                  Quantidade de Itens por Comprador
                </Typography>
                <Box sx={{ height: 350 }}>
                  {data?.buyer_data?.length > 0 ? (
                    <Doughnut
                      data={buyerItemsChart}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } },
                          tooltip: {
                            backgroundColor: 'white',
                            titleColor: '#222',
                            bodyColor: '#222',
                            borderColor: '#e1e1e1',
                            borderWidth: 1,
                            padding: 12
                          }
                        },
                        cutout: '60%'
                      }}
                    />
                  ) : (
                    <Typography variant="body2" sx={{ color: 'text.secondary', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      Sem dados para o período.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>
          </Grid>

          {/* Dialog for marking as invoiced/completed */}
          <Dialog
            open={matchDialogOpen}
            onClose={() => {
              setMatchDialogOpen(false);
              setSelectedNFE(null);
            }}
            maxWidth="md"
            fullWidth
          >
            <DialogTitle>
              Marcar Item como Faturado
              {currentPurchase && currentItem && (
                <Typography variant="subtitle2" color="text.secondary">
                  Pedido: {currentPurchase.cod_pedc} | Item: {currentItem.item_id} - {currentItem.descricao}
                </Typography>
              )}
            </DialogTitle>
            <DialogContent>
              {nfeLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : currentItem?.nfes && currentItem.nfes.length > 0 ? (
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Este item já possui as seguintes NFEs vinculadas:
                  </Typography>
                  <Box sx={{ mb: 3 }}>
                    {currentItem.nfes.map(nfe => (
                      <Chip
                        key={nfe.id}
                        label={nfe.num_nf}
                        color="primary"
                        size="medium"
                        sx={{ mr: 1, mb: 1 }}
                        onClick={() => handleViewDanfe(nfe.id, nfe.chave)}
                        icon={<ReceiptIcon />}
                      />
                    ))}
                  </Box>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<ReceiptIcon />}
                    onClick={() => handleViewDanfe(currentItem.nfes[0].id)}
                    sx={{ mr: 2 }}
                  >
                    Visualizar DANFE
                  </Button>
                </Box>
              ) : suggestedNFEs.length > 0 ? (
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Escolha uma das opções:
                  </Typography>

                  <Box sx={{ mb: 3 }}>
                    <Button
                      variant="contained"
                      color="success"
                      onClick={handleMarkAsCompleted}
                      startIcon={<CheckCircleIcon />}
                      sx={{ mr: 2, mb: 2 }}
                    >
                      Marcar como Concluído (sem NFE)
                    </Button>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="subtitle1" gutterBottom>
                    Ou selecione uma NFE para vincular:
                  </Typography>

                  <RadioGroup
                    value={selectedNFE ? selectedNFE.nfe.id : ''}
                    onChange={(e, value) => {
                      const selected = suggestedNFEs.find(nfe => nfe.nfe.id === Number(value));
                      setSelectedNFE(selected);
                    }}
                  >
                    {suggestedNFEs.map((match) => (
                      <Paper
                        key={match.nfe.id}
                        sx={{
                          p: 2,
                          mb: 2,
                          border: '1px solid',
                          borderColor: selectedNFE?.nfe.id === match.nfe.id ? 'primary.main' : 'divider',
                          borderRadius: 2
                        }}
                      >
                        <FormControlLabel
                          value={match.nfe.id}
                          control={<Radio />}
                          label={
                            <Box>
                              <Typography variant="subtitle1">
                                NFE {match.nfe.numero} (Série {match.nfe.serie})
                              </Typography>
                              <Typography variant="body2">
                                Chave: {match.nfe.chave}
                              </Typography>
                              <Typography variant="body2">
                                Emitente: {match.nfe.emitente}
                              </Typography>
                              <Typography variant="body2">
                                Data: {fmtDate(match.nfe.data_emissao)}
                              </Typography>
                              <Typography variant="body2">
                                Valor: {fmtCurrency(match.nfe.valor_total)}
                              </Typography>
                              <Box sx={{ mt: 1 }}>
                                <Chip
                                  label={`Pontuação: ${Math.round(match.score)}%`}
                                  color={
                                    match.score > 80 ? 'success' :
                                      match.score > 50 ? 'warning' : 'error'
                                  }
                                  size="small"
                                />
                              </Box>
                            </Box>
                          }
                        />
                      </Paper>
                    ))}
                  </RadioGroup>
                </Box>
              ) : (
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Escolha uma das opções:
                  </Typography>

                  <Button
                    variant="contained"
                    color="success"
                    onClick={handleMarkAsCompleted}
                    startIcon={<CheckCircleIcon />}
                    sx={{ mr: 2, mt: 2 }}
                  >
                    Marcar como Concluído (sem NFE)
                  </Button>

                  <Typography variant="body2" sx={{ mt: 3 }}>
                    Nenhuma NFE encontrada que corresponda a este item. Verifique se o fornecedor já emitiu a NFE.
                  </Typography>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => {
                setMatchDialogOpen(false);
                setSelectedNFE(null);
              }}>
                Cancelar
              </Button>
              {suggestedNFEs.length > 0 && (
                <Button
                  variant="contained"
                  color="primary"
                  disabled={!selectedNFE}
                  onClick={handleAssignNFE}
                >
                  Vincular NFE e Marcar como Faturado
                </Button>
              )}
            </DialogActions>
          </Dialog>
        </Container>
      </Box>
    </Box>
  );
};

export default Dashboard;