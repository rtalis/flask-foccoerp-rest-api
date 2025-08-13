import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
  Box, Container, Grid, Paper, Typography, Card, CardContent, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, AppBar,
  Toolbar, Button, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  IconButton, Divider, CircularProgress, Alert, MenuItem, Select, FormControl
} from '@mui/material';
import {
  Menu as MenuIcon, Dashboard as DashboardIcon, Search as SearchIcon,
  Compare as CompareIcon, Upload as UploadIcon, Logout as LogoutIcon,
  ShoppingCart as ShoppingCartIcon, Receipt as ReceiptIcon, Business as BusinessIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, Title, Tooltip, Legend, ArcElement
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';

import './Dashboard.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend, ArcElement);

const DRAWER_WIDTH = 260;

const Dashboard = ({ onLogout }) => {
  const [data, setData] = useState(null);
  const [months, setMonths] = useState(6);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mobileOpen, setMobileOpen] = useState(false);
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
        params: { months: m, limit: 8 },
        withCredentials: true
      });
      const d = res.data || {};
      // Sanitize data to primitives
      setData({
        summary: {
          total_orders: Number(d?.summary?.total_orders ?? 0),
          total_items: Number(d?.summary?.total_items ?? 0),
          total_value: Number(d?.summary?.total_value ?? 0),
          avg_order_value: Number(d?.summary?.avg_order_value ?? 0),
          total_suppliers: Number(d?.summary?.total_suppliers ?? 0),
        },
        monthly_data: Array.isArray(d?.monthly_data) ? d.monthly_data.map(x => ({
          month: String(x?.month ?? ''),
          order_count: Number(x?.order_count ?? 0),
          total_value: Number(x?.total_value ?? 0),
        })) : [],
        buyer_data: Array.isArray(d?.buyer_data) ? d.buyer_data.map(x => ({
          name: String(x?.name ?? ''),
          order_count: Number(x?.order_count ?? 0),
          total_value: Number(x?.total_value ?? 0),
          avg_value: Number(x?.avg_value ?? 0),
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
      });
    } catch (e) {
      console.error(e);
      setError('Erro ao carregar dados do dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(months); }, [months]);

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleNav = (path) => { navigate(path); };
  const handleLogout = () => { onLogout(); navigate('/login'); };

  const fmtCurrency = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v || 0));
  const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('pt-BR') : '—');

  // Monthly line chart - focused on total values
  const monthlyChart = useMemo(() => {
    const rows = Array.isArray(data?.monthly_data) ? data.monthly_data : [];
    
    return {
      labels: rows.map(r => String(r?.month ?? '')),
      datasets: [
        {
          label: 'Valor Total (R$)',
          data: rows.map(r => Number(r?.total_value ?? 0)),
          borderColor: 'rgba(66, 135, 245, 1)',
          backgroundColor: 'rgba(66, 135, 245, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#fff',
          pointBorderColor: 'rgba(66, 135, 245, 1)',
          pointBorderWidth: 2
        }
      ]
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
        backgroundColor: ['#4285F5', '#63B3ED', '#4FD1C5', '#68D391', '#F6AD55', '#FC8181', '#B794F4', '#F687B3']
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

  const drawer = (
    <>
      <Toolbar 
        sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          py: 1.5,
          bgcolor: 'primary.main',
          color: 'white'
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>Sistema de Compras</Typography>
      </Toolbar>
      <Divider />
      <Box sx={{ py: 2 }}>
        <List>
          {menuItems.map(item => (
            <ListItemButton 
              key={item.text} 
              onClick={() => handleNav(item.path)}
              sx={{ 
                borderRadius: '0 24px 24px 0',
                mx: 2,
                mb: 1,
                '&.Mui-selected': { 
                  bgcolor: 'primary.light',
                  '&:hover': { bgcolor: 'primary.light' }
                },
                '&:hover': { bgcolor: 'rgba(0,0,0,0.04)' } 
              }}
              selected={item.path === '/dashboard'}
            >
              <ListItemIcon sx={{ color: item.path === '/dashboard' ? 'primary.main' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          ))}
        </List>
      </Box>
    </>
  );

  if (loading) {
    return <Box sx={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
      <CircularProgress size={60} />
    </Box>;
  }
  if (error) {
    return <Container><Alert severity="error" sx={{ mt: 2 }}>{error}</Alert></Container>;
  }

  return (
    <Box sx={{ display: 'flex' }}>
      {/* AppBar */}
      <AppBar 
        position="fixed" 
        sx={{ 
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` }, 
          ml: { sm: `${DRAWER_WIDTH}px` },
          boxShadow: 'none',
          borderBottom: '1px solid rgba(0,0,0,0.1)',
          bgcolor: 'white',
          color: 'text.primary'
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
          {/* Period selector */}
          <FormControl size="small" sx={{ mr: 2, minWidth: 150 }}>
            <Select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              displayEmpty
              sx={{ borderRadius: 2 }}
            >
              <MenuItem value={3}>Últimos 3 meses</MenuItem>
              <MenuItem value={6}>Últimos 6 meses</MenuItem>
              <MenuItem value={12}>Últimos 12 meses</MenuItem>
            </Select>
          </FormControl>
          <Button 
            variant="outlined" 
            color="primary" 
            onClick={handleLogout} 
            startIcon={<LogoutIcon />}
            sx={{ borderRadius: 2 }}
          >
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      {/* Permanent drawer */}
      <Box
        component="nav"
        sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH },
          }}
        >
          {drawer}
        </Drawer>
        
        {/* Desktop drawer - always visible */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main content */}
      <Box component="main" sx={{ 
        flexGrow: 1, 
        p: 3, 
        width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
        bgcolor: '#f8f9fa',
        minHeight: '100vh'
      }}>
        <Toolbar />
        <Container maxWidth="xl">
          {/* KPIs */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      width: 56, 
                      height: 56, 
                      borderRadius: 2, 
                      bgcolor: 'rgba(25, 118, 210, 0.1)', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      mr: 2
                    }}>
                      <ShoppingCartIcon sx={{ fontSize: 28, color: '#1976d2' }} />
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
              <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      width: 56, 
                      height: 56, 
                      borderRadius: 2, 
                      bgcolor: 'rgba(56, 142, 60, 0.1)', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      mr: 2
                    }}>
                      <ReceiptIcon sx={{ fontSize: 28, color: '#388e3c' }} />
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
              <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      width: 56, 
                      height: 56, 
                      borderRadius: 2, 
                      bgcolor: 'rgba(245, 124, 0, 0.1)', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      mr: 2
                    }}>
                      <TrendingUpIcon sx={{ fontSize: 28, color: '#f57c00' }} />
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
              <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ 
                      width: 56, 
                      height: 56, 
                      borderRadius: 2, 
                      bgcolor: 'rgba(123, 31, 162, 0.1)', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      mr: 2
                    }}>
                      <BusinessIcon sx={{ fontSize: 28, color: '#7b1fa2' }} />
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
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} lg={8}>
              <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>Total de Compras por Mês</Typography>
                <Box sx={{ height: 350 }}>
                  {data?.monthly_data?.length > 0 ? (
                    <Line
                      data={monthlyChart}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
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
                              label: (context) => `R$ ${context.parsed.y.toLocaleString('pt-BR')}`
                            }
                          }
                        },
                        scales: {
                          y: { 
                            beginAtZero: true,
                            grid: {
                              borderDash: [5, 5],
                              color: 'rgba(0,0,0,0.06)'
                            },
                            ticks: {
                              callback: (value) => `R$ ${value.toLocaleString('pt-BR')}`
                            }
                          },
                          x: {
                            grid: {
                              display: false
                            }
                          }
                        }
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
              <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>Compras por Comprador</Typography>
                <Box sx={{ height: 350 }}>
                  {data?.buyer_data?.length > 0 ? (
                    <Doughnut
                      data={buyerChart}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { 
                          legend: { 
                            position: 'bottom',
                            labels: {
                              boxWidth: 12,
                              padding: 15
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
          </Grid>

          {/* Tables */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>Top Fornecedores</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Fornecedor</TableCell>
                        <TableCell align="right">Pedidos</TableCell>
                        <TableCell align="right">Valor Total</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(data?.supplier_data || []).slice(0, 6).map((s, i) => (
                        <TableRow key={i}>
                          <TableCell>{safeText(s.name)}</TableCell>
                          <TableCell align="right">{safeText(s.order_count)}</TableCell>
                          <TableCell align="right">{fmtCurrency(s.total_value)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, borderRadius: 3, boxShadow: '0 4px 20px 0 rgba(0,0,0,0.05)' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>Itens com Maior Gasto</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Item</TableCell>
                        <TableCell>Descrição</TableCell>
                        <TableCell align="right">Gasto Total</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(data?.top_items || []).slice(0, 6).map((it, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{safeText(it.item_id)}</TableCell>
                          <TableCell>{safeText(it.descricao)}</TableCell>
                          <TableCell align="right">{fmtCurrency(it.total_spend)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  );
};

export default Dashboard;