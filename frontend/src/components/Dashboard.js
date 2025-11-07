import React, { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  AppBar,
  Toolbar,
  Button,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Radio,
  RadioGroup,
  FormControlLabel,
} from "@mui/material";
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Search as SearchIcon,
  Compare as CompareIcon,
  Upload as UploadIcon,
  Logout as LogoutIcon,
  ShoppingCart as ShoppingCartIcon,
  Receipt as ReceiptIcon,
  Business as BusinessIcon,
  TrendingUp as TrendingUpIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Refresh as RefreshIcon,
  Link as LinkIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
  KeyboardArrowDown as KeyboardArrowDownIcon,
} from "@mui/icons-material";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  ArcElement,
} from "chart.js";
import { Line, Doughnut } from "react-chartjs-2";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider, DatePicker } from "@mui/x-date-pickers";
import { ptBR } from "date-fns/locale";
import "./Dashboard.css";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  ChartTooltip,
  Legend,
  ArcElement
);

const Dashboard = ({ onLogout }) => {
  const [data, setData] = useState(null);
  const [months, setMonths] = useState(6);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [purchaseData, setPurchaseData] = useState([]);
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setMonth(new Date().getMonth() - 1)),
    end: new Date(),
  });
  const [statusFilter, setStatusFilter] = useState("all"); // 'all', 'pending', 'partial', 'complete'
  const [matchDialogOpen, setMatchDialogOpen] = useState(false);
  const [currentPurchase, setCurrentPurchase] = useState(null);
  const [currentItem, setCurrentItem] = useState(null);
  const [suggestedNFEs, setSuggestedNFEs] = useState([]);
  const [selectedNFE, setSelectedNFE] = useState(null);
  const [nfeLoading, setNfeLoading] = useState(false);
  const DRAWER_WIDTH_OPEN = 260;
  const DRAWER_WIDTH_COLLAPSED = 80;
  const baseDrawerWidth = sidebarOpen
    ? DRAWER_WIDTH_OPEN
    : DRAWER_WIDTH_COLLAPSED;

  const navigate = useNavigate();

  const menuItems = useMemo(
    () => [
      { text: "Dashboard", icon: <DashboardIcon />, path: "/dashboard" },
      { text: "Buscar Pedidos", icon: <SearchIcon />, path: "/search" },
      {
        text: "Analisar Cotações",
        icon: <CompareIcon />,
        path: "/quotation-analyzer",
      },
      { text: "Importar Dados", icon: <UploadIcon />, path: "/import" },
    ],
    []
  );

  const fetchData = async (m) => {
    try {
      setLoading(true);
      setError("");
      const res = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/dashboard_summary`,
        {
          params: { months: m, limit: m + 2 },
          withCredentials: true,
        }
      );
      const d = res.data || {};
      setData({
        summary: {
          total_orders: Number(d?.summary?.total_orders ?? 0),
          total_items: Number(d?.summary?.total_items ?? 0),
          total_value: Number(d?.summary?.total_value ?? 0),
          avg_order_value: Number(d?.summary?.avg_order_value ?? 0),
          total_suppliers: Number(d?.summary?.total_suppliers ?? 0),
        },
        daily_usage: Array.isArray(d?.daily_usage)
          ? d.daily_usage.map((x) => ({
              date: x?.date ?? "",
              logins: Number(x?.logins ?? 0),
              unique_users: Number(x?.unique_users ?? 0),
            }))
          : [],
        buyer_data: Array.isArray(d?.buyer_data)
          ? d.buyer_data.map((x) => ({
              name: String(x?.name ?? ""),
              order_count: Number(x?.order_count ?? 0),
              total_value: Number(x?.total_value ?? 0),
              avg_value: Number(x?.avg_value ?? 0),
              item_count: Number(x?.item_count ?? 0),
            }))
          : [],
        supplier_data: Array.isArray(d?.supplier_data)
          ? d.supplier_data.map((x) => ({
              name: String(x?.name ?? ""),
              order_count: Number(x?.order_count ?? 0),
              total_value: Number(x?.total_value ?? 0),
            }))
          : [],
        top_items: Array.isArray(d?.top_items)
          ? d.top_items.map((x) => ({
              item_id: String(x?.item_id ?? ""),
              descricao: String(x?.descricao ?? ""),
              total_spend: Number(x?.total_spend ?? 0),
            }))
          : [],
        recent_orders: Array.isArray(d?.recent_orders)
          ? d.recent_orders.map((x) => ({
              cod_pedc: String(x?.cod_pedc ?? ""),
              dt_emis: x?.dt_emis ?? null,
              fornecedor_descricao: String(x?.fornecedor_descricao ?? ""),
              func_nome: String(x?.func_nome ?? ""),
              total_value: Number(x?.total_value ?? 0),
            }))
          : [],
        monthly_data: Array.isArray(d?.monthly_data)
          ? d.monthly_data.map((x) => ({
              month: String(x?.month ?? ""),
              order_count: Number(x?.order_count ?? 0),
              total_value: Number(x?.total_value ?? 0),
            }))
          : [],
      });
    } catch (e) {
      console.error(e);
      setError("Erro ao carregar dados do dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsInvoiced = async (purchaseId, itemId) => {
    try {
      setNfeLoading(true);
      setMatchDialogOpen(true);

      const purchase = purchaseData.find((p) => p.id === purchaseId);
      const item = purchase?.items.find((i) => i.id === itemId);

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
      console.error("Error preparing invoice options:", err);
    } finally {
      setNfeLoading(false);
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
          mark_as_completed: true, // New flag
        },
        { withCredentials: true }
      );

      setMatchDialogOpen(false);
      setSelectedNFE(null);

      // Refresh purchase data
      //fetchPurchases();
    } catch (err) {
      console.error("Error marking as completed:", err);
    }
  };

  const handleViewDanfe = (nfeId, nfeChave) => {
    if (nfeChave) {
      window.open(
        `${process.env.REACT_APP_API_URL}/api/view_danfe_template_by_key/${nfeChave}`,
        "_blank"
      );
    } else {
      window.open(
        `${process.env.REACT_APP_API_URL}/api/view_danfe_template/${nfeId}`,
        "_blank"
      );
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
          quantity: currentItem.quantidade,
        },
        { withCredentials: true }
      );

      setMatchDialogOpen(false);
      setSelectedNFE(null);

      // Refresh purchase data
      //fetchPurchases(); disabled while not fully implemented
    } catch (err) {
      console.error("Error assigning NFE:", err);
    }
  };

  useEffect(() => {
    fetchData(months);
  }, [months]);

  // Handle date range change and load monthly chart
  const handleDateRangeChange = (type, newValue) => {
    setDateRange((prev) => ({ ...prev, [type]: newValue }));
  };

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);
  const handleSidebarCollapse = () => setSidebarOpen((v) => !v);
  const handleNav = (path) => {
    navigate(path);
  };
  const handleLogout = () => {
    onLogout();
    navigate("/login");
  };
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    const statusMap = {
      0: "pending",
      1: "partial",
      2: "fulfilled",
    };

    setStatusFilter(statusMap[newValue]);
  };

  const fmtCurrency = (v) =>
    new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(Number(v || 0));
  const fmtDate = (iso) =>
    iso ? new Date(iso).toLocaleDateString("pt-BR") : "—";

  // Monthly line (total value)
  const monthlyChart = useMemo(() => {
    const rows = Array.isArray(data?.monthly_data) ? data.monthly_data : [];
    return {
      labels: rows.map((r) => String(r?.month ?? "")),
      datasets: [
        {
          label: "Valor Total (R$)",
          data: rows.map((r) => Number(r?.total_value ?? 0)),
          borderColor: "#5b8def",
          backgroundColor: "rgba(91, 141, 239, 0.15)",
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: "#fff",
          pointBorderColor: "#5b8def",
          pointBorderWidth: 2,
        },
      ],
    };
  }, [data]);

  // Buyer purchases chart data
  const buyerPurchasesChart = useMemo(() => {
    const rows = Array.isArray(data?.buyer_data) ? data.buyer_data : [];
    if (!rows.length) return null;
    return {
      labels: rows.map((r) => String(r?.name ?? "")),
      datasets: [
        {
          label: "Número de Pedidos",
          data: rows.map((r) => Number(r?.order_count ?? 0)),
          backgroundColor: [
            "#5b8def",
            "#68c2ff",
            "#f57c00",
            "#7b1fa2",
            "#ef7171",
            "#a5b0c2",
            "#fad776",
            "#8fe3a6",
          ],
          borderWidth: 1,
        },
      ],
    };
  }, [data]);

  // buyer Items Chart data
  const buyerItemsChart = useMemo(() => {
    const rows = Array.isArray(data?.buyer_data) ? data.buyer_data : [];
    if (!rows.length) return null;
    return {
      labels: rows.map((r) => String(r?.name ?? "")),
      datasets: [
        {
          label: "Quantidade de Itens",
          data: rows.map((r) => Number(r?.item_count ?? 0)),
          backgroundColor: [
            "#6dd3c2",
            "#5b8def",
            "#fad776",
            "#c69df6",
            "#ef7171",
            "#68c2ff",
            "#a5b0c2",
            "#8fe3a6",
          ],
          borderWidth: 1,
        },
      ],
    };
  }, [data]);

  const buyerChart = useMemo(() => {
    const rows = Array.isArray(data?.buyer_data) ? data.buyer_data : [];
    if (!rows.length) return null;
    return {
      labels: rows.map((r) => String(r?.name ?? "")),
      datasets: [
        {
          label: "Valor por Comprador",
          data: rows.map((r) => Number(r?.total_value ?? 0)),
          backgroundColor: [
            "#5b8def",
            "#6dd3c2",
            "#fad776",
            "#c69df6",
            "#ef7171",
            "#68c2ff",
            "#a5b0c2",
            "#8fe3a6",
          ],
        },
      ],
    };
  }, [data]);
  const dailyUsageChart = useMemo(() => {
    const rows = Array.isArray(data?.daily_usage) ? data.daily_usage : [];
    return {
      labels: rows.map((r) => {
        if (!r?.date) return "";
        const dateObj = new Date(r.date);
        if (Number.isNaN(dateObj.getTime())) {
          return String(r.date);
        }
        return dateObj.toLocaleDateString("pt-BR", {
          day: "2-digit",
          month: "2-digit",
        });
      }),
      datasets: [
        {
          label: "Logins",
          data: rows.map((r) => Number(r?.logins ?? 0)),
          borderColor: "#5b8def",
          backgroundColor: "rgba(91, 141, 239, 0.2)",
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: "#5b8def",
        },
        {
          label: "Usuários Únicos",
          data: rows.map((r) => Number(r?.unique_users ?? 0)),
          borderColor: "#6dd3c2",
          backgroundColor: "rgba(109, 211, 194, 0.2)",
          fill: false,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: "#6dd3c2",
          borderDash: [6, 4],
        },
      ],
    };
  }, [data]);

  const drawerContent = (
    <>
      <Toolbar
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: sidebarOpen ? "space-between" : "center",
          py: 1,
          px: 2,
        }}
      >
        {sidebarOpen && (
          <Typography variant="h6" sx={{ fontWeight: "bold" }}>
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
          {menuItems.map((item) => (
            <ListItemButton
              key={item.text}
              onClick={() => handleNav(item.path)}
              sx={{
                borderRadius: 2,
                mx: sidebarOpen ? 1 : 0.5,
                mb: 0.5,
                minHeight: 44,
                justifyContent: sidebarOpen ? "flex-start" : "center",
                "&.Mui-selected": {
                  bgcolor: "primary.light",
                  "&:hover": { bgcolor: "primary.light" },
                },
                "&:hover": { bgcolor: "rgba(0,0,0,0.04)" },
              }}
              selected={item.path === "/dashboard"}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: sidebarOpen ? 2 : "auto",
                  color:
                    item.path === "/dashboard" ? "primary.main" : "inherit",
                  justifyContent: "center",
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
    if (status === "probable_match") {
      return (
        <Chip
          icon={<CheckCircleIcon />}
          label="Provável Faturado"
          color="info"
          size="small"
          variant="outlined"
          sx={{ background: "rgba(3, 169, 244, 0.1)" }}
        />
      );
    }

    // Existing status logic
    switch (status) {
      case "fulfilled":
        return (
          <Chip
            icon={<CheckCircleIcon />}
            label="Atendido"
            color="success"
            size="small"
            variant="outlined"
          />
        );
      case "partial":
        return (
          <Chip
            icon={<WarningIcon />}
            label="Parcial"
            color="warning"
            size="small"
            variant="outlined"
          />
        );
      case "pending":
      default:
        return (
          <Chip
            icon={<ErrorIcon />}
            label="Pendente"
            color="error"
            size="small"
            variant="outlined"
          />
        );
    }
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          height: "100vh",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <CircularProgress size={60} />
        <Box sx={{ ml: 2 }}>
          <Typography variant="body2">
            Carregando {months} meses de relatórios...
          </Typography>
        </Box>
      </Box>
    );
  }
  if (error) {
    return (
      <Container>
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  const drawerWidth = sidebarOpen ? DRAWER_WIDTH_OPEN : DRAWER_WIDTH_COLLAPSED;

  return (
    <Box sx={{ display: "flex" }}>
      {/* AppBar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          bgcolor: "transparent",
          color: "text.primary",
          backdropFilter: "blur(6px)",
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: "none" } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: "bold" }}>
            Dashboard
          </Typography>
          <FormControl size="small" sx={{ mr: 2, minWidth: 150 }}>
            <Select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              displayEmpty
              sx={{ borderRadius: 2, bgcolor: "white" }}
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
            sx={{ borderRadius: 2, textTransform: "none" }}
          >
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      {/* Navigation drawers */}
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        {/* Mobile temporary drawer or when sidebar is hidden */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", sm: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: DRAWER_WIDTH_OPEN,
            },
          }}
        >
          {drawerContent}
        </Drawer>

        {/* Desktop permanent drawer that hides on scroll */}

        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", sm: "block" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: baseDrawerWidth,
              transition: (theme) =>
                theme.transitions.create("width", {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.shortest,
                }),
            },
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
          minHeight: "100vh",
          bgcolor: "linear-gradient(180deg, #f7f9fc 0%, #f2f4f7 100%)",
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
              background: "linear-gradient(135deg, #5b8def 0%, #6dd3c2 100%)",
              color: "white",
              boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            }}
          >
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
              Visão Geral de Compras
            </Typography>
          </Box>

          {/* Monthly Chart  */}

          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  boxShadow: "0 8px 24px rgba(0,0,0,0.06)",
                  width: "96%",
                  maxWidth: "100%",
                }}
              >
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{ fontWeight: "bold" }}
                >
                  Total de Compras por Mês
                </Typography>
                <Box
                  sx={{
                    height: { xs: 350, md: 400 },
                    width: "100%",
                    mx: "auto",
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
                          legend: { position: "top" },
                          tooltip: {
                            backgroundColor: "white",
                            titleColor: "#222",
                            bodyColor: "#222",
                            borderColor: "#e1e1e1",
                            borderWidth: 1,
                            padding: 12,
                            boxPadding: 6,
                            usePointStyle: true,
                            callbacks: {
                              label: (ctx) =>
                                `R$ ${ctx.parsed.y.toLocaleString("pt-BR")}`,
                            },
                          },
                        },
                        scales: {
                          y: {
                            beginAtZero: true,
                            grid: {
                              borderDash: [5, 5],
                              color: "rgba(0,0,0,0.06)",
                            },
                            ticks: {
                              callback: (v) =>
                                `R$ ${Number(v).toLocaleString("pt-BR")}`,
                            },
                          },
                          x: { grid: { display: false } },
                        },
                      }}
                    />
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
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
                  <Box sx={{ display: "flex", alignItems: "center" }}>
                    <Box
                      sx={{
                        width: 50,
                        height: 50,
                        borderRadius: 2,
                        bgcolor: "rgba(91,141,239,0.15)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                      }}
                    >
                      <ShoppingCartIcon sx={{ color: "#5b8def" }} />
                    </Box>
                    <Box>
                      <Typography
                        sx={{ color: "text.secondary", fontWeight: 500 }}
                        gutterBottom
                      >
                        Pedidos
                      </Typography>
                      <Typography variant="h4">
                        {data?.summary?.total_orders || 0}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card className="summary-card" sx={{ borderRadius: 3, p: 0.5 }}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center" }}>
                    <Box
                      sx={{
                        width: 50,
                        height: 50,
                        borderRadius: 2,
                        bgcolor: "rgba(104,194,255,0.15)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                      }}
                    >
                      <ReceiptIcon sx={{ color: "#68c2ff" }} />
                    </Box>
                    <Box>
                      <Typography
                        sx={{ color: "text.secondary", fontWeight: 500 }}
                        gutterBottom
                      >
                        Itens
                      </Typography>
                      <Typography variant="h4">
                        {data?.summary?.total_items || 0}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card className="summary-card" sx={{ borderRadius: 3, p: 0.5 }}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center" }}>
                    <Box
                      sx={{
                        width: 50,
                        height: 50,
                        borderRadius: 2,
                        bgcolor: "rgba(245,124,0,0.15)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                      }}
                    >
                      <TrendingUpIcon sx={{ color: "#f57c00" }} />
                    </Box>
                    <Box>
                      <Typography
                        sx={{ color: "text.secondary", fontWeight: 500 }}
                        gutterBottom
                      >
                        Total
                      </Typography>
                      <Typography variant="h5">
                        {fmtCurrency(data?.summary?.total_value || 0)}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card className="summary-card" sx={{ borderRadius: 3, p: 0.5 }}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center" }}>
                    <Box
                      sx={{
                        width: 50,
                        height: 50,
                        borderRadius: 2,
                        bgcolor: "rgba(123,31,162,0.15)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                      }}
                    >
                      <BusinessIcon sx={{ color: "#7b1fa2" }} />
                    </Box>
                    <Box>
                      <Typography
                        sx={{ color: "text.secondary", fontWeight: 500 }}
                        gutterBottom
                      >
                        Média Pedido
                      </Typography>
                      <Typography variant="h5">
                        {fmtCurrency(data?.summary?.avg_order_value || 0)}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Charts */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} lg={4}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  boxShadow: "0 8px 24px rgba(0,0,0,0.06)",
                }}
              >
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{ fontWeight: "bold" }}
                >
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
                          legend: {
                            position: "bottom",
                            labels: { boxWidth: 12, padding: 15 },
                          },
                          tooltip: {
                            backgroundColor: "white",
                            titleColor: "#222",
                            bodyColor: "#222",
                            borderColor: "#e1e1e1",
                            borderWidth: 1,
                            padding: 12,
                            callbacks: {
                              label: (ctx) =>
                                `R$ ${ctx.raw.toLocaleString("pt-BR")}`,
                            },
                          },
                        },
                        cutout: "60%",
                      }}
                    />
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      Sem dados para exibir.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} lg={4}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  boxShadow: "0 8px 24px rgba(0,0,0,0.06)",
                }}
              >
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{ fontWeight: "bold" }}
                >
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
                          legend: {
                            position: "bottom",
                            labels: { boxWidth: 12, padding: 15 },
                          },
                          tooltip: {
                            backgroundColor: "white",
                            titleColor: "#222",
                            bodyColor: "#222",
                            borderColor: "#e1e1e1",
                            borderWidth: 1,
                            padding: 12,
                          },
                        },
                        cutout: "60%",
                      }}
                    />
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      Sem dados para o período.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} lg={4}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  boxShadow: "0 8px 24px rgba(0,0,0,0.06)",
                }}
              >
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{ fontWeight: "bold" }}
                >
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
                          legend: {
                            position: "bottom",
                            labels: { boxWidth: 12, padding: 15 },
                          },
                          tooltip: {
                            backgroundColor: "white",
                            titleColor: "#222",
                            bodyColor: "#222",
                            borderColor: "#e1e1e1",
                            borderWidth: 1,
                            padding: 12,
                          },
                        },
                        cutout: "60%",
                      }}
                    />
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      Sem dados para o período.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>
          </Grid>
          {/* Daily Usage Chart */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12}>
              <Paper
                sx={{
                  p: 3,
                  borderRadius: 3,
                  boxShadow: "0 8px 24px rgba(0,0,0,0.06)",
                  width: "96%",
                  maxWidth: "100%",
                }}
              >
                <Typography
                  variant="h6"
                  gutterBottom
                  sx={{ fontWeight: "bold" }}
                >
                  Uso Diário do Sistema
                </Typography>
                <Box
                  sx={{
                    height: { xs: 320, md: 360 },
                    width: "100%",
                    mx: "auto",
                  }}
                >
                  {data?.daily_usage?.length > 0 ? (
                    <Line
                      data={dailyUsageChart}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: { position: "top" },
                          tooltip: {
                            backgroundColor: "white",
                            titleColor: "#222",
                            bodyColor: "#222",
                            borderColor: "#e1e1e1",
                            borderWidth: 1,
                            padding: 12,
                            usePointStyle: true,
                            callbacks: {
                              label: (ctx) =>
                                `${ctx.dataset.label}: ${ctx.parsed.y}`,
                            },
                          },
                        },
                        scales: {
                          y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1, precision: 0 },
                            grid: {
                              borderDash: [5, 5],
                              color: "rgba(0,0,0,0.06)",
                            },
                          },
                          x: { grid: { display: false } },
                        },
                      }}
                    />
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      Sem dados de uso disponíveis para o período selecionado.
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
                  Pedido: {currentPurchase.cod_pedc} | Item:{" "}
                  {currentItem.item_id} - {currentItem.descricao}
                </Typography>
              )}
            </DialogTitle>
            <DialogContent>
              {nfeLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : currentItem?.nfes && currentItem.nfes.length > 0 ? (
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Este item já possui as seguintes NFEs vinculadas:
                  </Typography>
                  <Box sx={{ mb: 3 }}>
                    {currentItem.nfes.map((nfe) => (
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
                    value={selectedNFE ? selectedNFE.nfe.id : ""}
                    onChange={(e, value) => {
                      const selected = suggestedNFEs.find(
                        (nfe) => nfe.nfe.id === Number(value)
                      );
                      setSelectedNFE(selected);
                    }}
                  >
                    {suggestedNFEs.map((match) => (
                      <Paper
                        key={match.nfe.id}
                        sx={{
                          p: 2,
                          mb: 2,
                          border: "1px solid",
                          borderColor:
                            selectedNFE?.nfe.id === match.nfe.id
                              ? "primary.main"
                              : "divider",
                          borderRadius: 2,
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
                                  label={`Pontuação: ${Math.round(
                                    match.score
                                  )}%`}
                                  color={
                                    match.score > 80
                                      ? "success"
                                      : match.score > 50
                                      ? "warning"
                                      : "error"
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
                    Nenhuma NFE encontrada que corresponda a este item.
                    Verifique se o fornecedor já emitiu a NFE.
                  </Typography>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button
                onClick={() => {
                  setMatchDialogOpen(false);
                  setSelectedNFE(null);
                }}
              >
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
