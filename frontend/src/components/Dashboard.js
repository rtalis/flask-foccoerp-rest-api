import React, { useState, useMemo, useCallback } from "react";
import axios from "axios";
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Stack,
  Skeleton,
  Chip,
  LinearProgress,
  TextField,
  Button,
  Divider,
} from "@mui/material";
import {
  ShoppingCart as ShoppingCartIcon,
  Receipt as ReceiptIcon,
  Business as BusinessIcon,
  TrendingUp as TrendingUpIcon,
  PlayArrow as PlayArrowIcon,
  FilterList as FilterListIcon,
  LocalShipping as LocalShippingIcon,
  Inventory as InventoryIcon,
  CheckCircle as CheckCircleIcon,
  Pending as PendingIcon,
  DateRange as DateRangeIcon,
  Dashboard as DashboardIcon,
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
import { Line, Doughnut, Bar } from "react-chartjs-2";
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

const PERIOD_OPTIONS = [
  { value: 1, label: "1 mês" },
  { value: 3, label: "3 meses" },
  { value: 6, label: "6 meses" },
  { value: 12, label: "12 meses" },
  { value: 24, label: "24 meses" },
  { value: 0, label: "Personalizado" },
];

// Helper to format date as YYYY-MM-DD
const formatDateValue = (date) => {
  if (!date) return "";
  const d = new Date(date);
  return d.toISOString().split("T")[0];
};

// Calculate default dates based on months
const getDefaultDates = (months) => {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - months);
  start.setDate(1);
  return {
    start: formatDateValue(start),
    end: formatDateValue(end),
  };
};

const Dashboard = () => {
  // Filter state
  const [months, setMonths] = useState(6);
  const [buyerFilter, setBuyerFilter] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [showCustomDates, setShowCustomDates] = useState(false);

  // Data state
  const [data, setData] = useState(null);
  const [allBuyerNames, setAllBuyerNames] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasLoaded, setHasLoaded] = useState(false);
  const [requestStartDate, setRequestStartDate] = useState("");
  const [requestEndDate, setRequestEndDate] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      // Build params based on whether custom dates are used
      const params = {
        limit: Math.max(months, 12) + 2,
      };

      // Calculate dates for the request (used for both orders and daily usage)
      let requestStartDate, requestEndDate;
      if (months === 0 && startDate && endDate) {
        // Custom date range
        requestStartDate = startDate;
        requestEndDate = endDate;
        // Calculate months for chart display
        const start = new Date(startDate);
        const end = new Date(endDate);
        const diffMonths =
          Math.ceil((end - start) / (1000 * 60 * 60 * 24 * 30)) + 1;
        params.months = Math.max(diffMonths, 1);
      } else {
        // Calculate dates from months
        const end = new Date();
        const start = new Date();
        start.setMonth(start.getMonth() - months);
        start.setDate(1);
        requestStartDate = formatDateValue(start);
        requestEndDate = formatDateValue(end);
        params.months = months;
      }
      params.start_date = requestStartDate;
      params.end_date = requestEndDate;

      // Store the request dates for use in chart grouping
      setRequestStartDate(requestStartDate);
      setRequestEndDate(requestEndDate);
      if (buyerFilter && buyerFilter !== "all") {
        params.buyer = buyerFilter;
      }

      const res = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/dashboard_summary`,
        {
          params,
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
          total_quantity: Number(d?.summary?.total_quantity ?? 0),
          fulfilled_orders: Number(d?.summary?.fulfilled_orders ?? 0),
          pending_orders: Number(d?.summary?.pending_orders ?? 0),
          fulfillment_rate: Number(d?.summary?.fulfillment_rate ?? 0),
          nfe_count: Number(d?.summary?.nfe_count ?? 0),
          nfe_total_value: Number(d?.summary?.nfe_total_value ?? 0),
        },
        buyer_data: Array.isArray(d?.buyer_data)
          ? d.buyer_data.map((x) => ({
              name: String(x?.name ?? ""),
              order_count: Number(x?.order_count ?? 0),
              total_value: Number(x?.total_value ?? 0),
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
        monthly_data: Array.isArray(d?.monthly_data)
          ? d.monthly_data.map((x) => ({
              month: String(x?.month ?? ""),
              order_count: Number(x?.order_count ?? 0),
              total_value: Number(x?.total_value ?? 0),
              item_count: Number(x?.item_count ?? 0),
              total_qty: Number(x?.total_qty ?? 0),
            }))
          : [],
        daily_usage: Array.isArray(d?.daily_usage)
          ? d.daily_usage.map((x) => ({
              date: String(x?.date ?? ""),
              logins: Number(x?.logins ?? 0),
            }))
          : [],
      });

      // Store all purchaser names from the API response (always available)
      if (Array.isArray(d?.all_purchasers) && d.all_purchasers.length > 0) {
        setAllBuyerNames(d.all_purchasers);
      }

      setHasLoaded(true);
    } catch (e) {
      console.error(e);
      setError("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, [months, buyerFilter, startDate, endDate]);

  // Handle months change - update custom dates when preset is selected
  const handleMonthsChange = (value) => {
    setMonths(value);
    if (value === 0) {
      // Custom - show date pickers with default values
      setShowCustomDates(true);
      if (!startDate || !endDate) {
        const defaults = getDefaultDates(6);
        setStartDate(defaults.start);
        setEndDate(defaults.end);
      }
    } else {
      setShowCustomDates(false);
    }
  };

  // Buyer names for filter dropdown - use stored list or current data
  const buyerNames = useMemo(() => {
    if (allBuyerNames.length > 0) return allBuyerNames;
    if (!data?.buyer_data) return [];
    return data.buyer_data.map((b) => b.name).filter(Boolean);
  }, [data, allBuyerNames]);

  // Filter monthly data to remove leading zero-value months
  const filteredMonthlyData = useMemo(() => {
    const rows = data?.monthly_data ?? [];
    // Find the first month with non-zero value
    let firstNonZeroIndex = rows.findIndex(
      (r) => r.total_value > 0 || r.order_count > 0
    );
    if (firstNonZeroIndex === -1) return rows;
    return rows.slice(firstNonZeroIndex);
  }, [data]);

  // Charts
  const monthlyChart = useMemo(() => {
    const rows = filteredMonthlyData;
    return {
      labels: rows.map((r) => r.month),
      datasets: [
        {
          label: "Valor (R$)",
          data: rows.map((r) => r.total_value),
          borderColor: "#5b8def",
          backgroundColor: "rgba(91, 141, 239, 0.1)",
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: "#fff",
          pointBorderColor: "#5b8def",
          pointBorderWidth: 2,
          yAxisID: "y",
        },
      ],
    };
  }, [filteredMonthlyData]);

  const monthlyItemsChart = useMemo(() => {
    const rows = filteredMonthlyData;
    return {
      labels: rows.map((r) => r.month),
      datasets: [
        {
          label: "Qtd. Itens",
          data: rows.map((r) => r.item_count),
          backgroundColor: "#6dd3c2",
          borderRadius: 4,
        },
      ],
    };
  }, [data]);

  const dailyUsageChart = useMemo(() => {
    const rows = data?.daily_usage ?? [];
    if (rows.length === 0) {
      return {
        labels: [],
        datasets: [{ label: "Logins", data: [], borderColor: "#5b8def" }],
      };
    }

    // Group by month if the date range is larger than 1 month
    let shouldGroupByMonth = false;
    if (requestStartDate && requestEndDate) {
      const start = new Date(requestStartDate);
      const end = new Date(requestEndDate);
      const daysDiff = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
      shouldGroupByMonth = daysDiff > 30;
    }

    if (!shouldGroupByMonth) {
      // Daily view
      return {
        labels: rows.map((r) => {
          if (!r.date) return "";
          const parts = String(r.date).split("-");
          let dObj;
          if (parts.length === 3) {
            const y = Number(parts[0]);
            const m = Number(parts[1]) - 1;
            const d = Number(parts[2]);
            dObj = new Date(y, m, d);
          } else {
            dObj = new Date(r.date);
          }
          return dObj.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit",
            year: "2-digit",
          });
        }),
        datasets: [
          {
            label: "Logins",
            data: rows.map((r) => r.logins),
            borderColor: "#5b8def",
            backgroundColor: "rgba(91, 141, 239, 0.15)",
            fill: true,
            tension: 0.35,
            pointRadius: 2,
          },
        ],
      };
    }

    // Monthly grouped view
    const monthlyData = {};
    rows.forEach((r) => {
      if (!r.date) return;
      const parts = String(r.date).split("-");
      if (parts.length === 3) {
        const y = Number(parts[0]);
        const m = Number(parts[1]);
        const monthKey = `${y}-${String(m).padStart(2, "0")}`;
        if (!monthlyData[monthKey]) {
          monthlyData[monthKey] = { logins: 0, date: new Date(y, m - 1, 1) };
        }
        monthlyData[monthKey].logins += r.logins;
      }
    });

    const sortedMonths = Object.entries(monthlyData).sort(
      ([, a], [, b]) => a.date - b.date
    );

    return {
      labels: sortedMonths.map(([, data]) => {
        return data.date.toLocaleDateString("pt-BR", {
          month: "short",
          year: "2-digit",
        });
      }),
      datasets: [
        {
          label: "Logins",
          data: sortedMonths.map(([, data]) => data.logins),
          borderColor: "#5b8def",
          backgroundColor: "rgba(91, 141, 239, 0.15)",
          fill: true,
          tension: 0.35,
          pointRadius: 4,
        },
      ],
    };
  }, [data, requestStartDate, requestEndDate]);

  const supplierChart = useMemo(() => {
    const rows = (data?.supplier_data ?? []).slice(0, 6);
    if (!rows.length) return null;
    return {
      labels: rows.map((r) => r.name?.substring(0, 20) || "—"),
      datasets: [
        {
          data: rows.map((r) => r.total_value),
          backgroundColor: [
            "#f57c00",
            "#5b8def",
            "#6dd3c2",
            "#c69df6",
            "#ef7171",
            "#fad776",
          ],
        },
      ],
    };
  }, [data]);

  const topItemsChart = useMemo(() => {
    const rows = (data?.top_items ?? []).slice(0, 8);
    if (!rows.length) return null;
    return {
      labels: rows.map((r) => r.descricao?.substring(0, 25) || r.item_id),
      datasets: [
        {
          label: "Valor",
          data: rows.map((r) => r.total_spend),
          backgroundColor: "#68c2ff",
          borderRadius: 4,
        },
      ],
    };
  }, [data]);

  const fulfillmentChart = useMemo(() => {
    if (!data?.summary) return null;
    const { fulfilled_orders, pending_orders } = data.summary;
    if (fulfilled_orders === 0 && pending_orders === 0) return null;
    return {
      labels: ["Atendidos", "Pendentes"],
      datasets: [
        {
          data: [fulfilled_orders, pending_orders],
          backgroundColor: ["#4caf50", "#ff9800"],
        },
      ],
    };
  }, [data]);

  const buyerValueChart = useMemo(() => {
    const rows = data?.buyer_data ?? [];
    if (!rows.length) return null;
    return {
      labels: rows.map((r) => r.name),
      datasets: [
        {
          data: rows.map((r) => r.total_value),
          backgroundColor: [
            "#5b8def",
            "#6dd3c2",
            "#fad776",
            "#c69df6",
            "#ef7171",
            "#68c2ff",
          ],
        },
      ],
    };
  }, [data]);

  const buyerOrdersChart = useMemo(() => {
    const rows = data?.buyer_data ?? [];
    if (!rows.length) return null;
    return {
      labels: rows.map((r) => r.name),
      datasets: [
        {
          data: rows.map((r) => r.order_count),
          backgroundColor: [
            "#68c2ff",
            "#5b8def",
            "#f57c00",
            "#7b1fa2",
            "#ef7171",
            "#a5b0c2",
          ],
        },
      ],
    };
  }, [data]);

  const fmtCurrency = (v) =>
    new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(Number(v || 0));

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "bottom",
        labels: { boxWidth: 10, padding: 12, font: { size: 11 } },
      },
      tooltip: {
        backgroundColor: "#fff",
        titleColor: "#222",
        bodyColor: "#222",
        borderColor: "#e0e0e0",
        borderWidth: 1,
        padding: 10,
        callbacks: { label: (ctx) => `R$ ${ctx.raw.toLocaleString("pt-BR")}` },
      },
    },
    cutout: "65%",
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#fff",
        titleColor: "#222",
        bodyColor: "#222",
        borderColor: "#e0e0e0",
        borderWidth: 1,
        padding: 10,
        callbacks: {
          label: (ctx) => `R$ ${ctx.parsed.y.toLocaleString("pt-BR")}`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: "rgba(0,0,0,0.05)" },
        ticks: { callback: (v) => `R$ ${(v / 1000).toFixed(0)}k` },
      },
      x: { grid: { display: false } },
    },
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y",
    layout: {
      padding: { left: 10 },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#fff",
        titleColor: "#222",
        bodyColor: "#222",
        borderColor: "#e0e0e0",
        borderWidth: 1,
        padding: 10,
        callbacks: {
          label: (ctx) => `R$ ${ctx.parsed.x.toLocaleString("pt-BR")}`,
        },
      },
    },
    scales: {
      x: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
      y: {
        grid: { display: false },
        ticks: {
          autoSkip: false,
          font: { size: 11 },
        },
      },
    },
  };

  const usageLineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#fff",
        titleColor: "#222",
        bodyColor: "#222",
        borderColor: "#e0e0e0",
        borderWidth: 1,
        padding: 10,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: "rgba(0,0,0,0.05)" },
        ticks: { stepSize: 1 },
      },
      x: { grid: { display: false } },
    },
  };

  return (
    <Box sx={{ minHeight: "100%", bgcolor: "#f8f9fb", p: 3 }}>
      <Container maxWidth="xl" disableGutters>
        {/* Filters Card */}
        <Paper sx={{ p: 2.5, mb: 3, borderRadius: 2 }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            alignItems={{ sm: "center" }}
            justifyContent="space-between"
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterListIcon color="action" />
              <Typography variant="subtitle2" color="text.secondary">
                Filtros do Relatório
              </Typography>
            </Box>

            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={2}
              alignItems="center"
              flexWrap="wrap"
            >
              <FormControl size="small" sx={{ minWidth: 130 }}>
                <InputLabel>Período</InputLabel>
                <Select
                  label="Período"
                  value={months}
                  onChange={(e) => handleMonthsChange(Number(e.target.value))}
                >
                  {PERIOD_OPTIONS.map((o) => (
                    <MenuItem key={o.value} value={o.value}>
                      {o.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Custom Date Range */}
              {showCustomDates && (
                <>
                  <TextField
                    size="small"
                    type="date"
                    label="Data Início"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    InputLabelProps={{ shrink: true }}
                    sx={{ minWidth: 140 }}
                  />
                  <TextField
                    size="small"
                    type="date"
                    label="Data Fim"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    InputLabelProps={{ shrink: true }}
                    sx={{ minWidth: 140 }}
                  />
                </>
              )}

              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Comprador</InputLabel>
                <Select
                  label="Comprador"
                  value={buyerFilter}
                  onChange={(e) => setBuyerFilter(e.target.value)}
                >
                  <MenuItem value="all">Todos</MenuItem>
                  {buyerNames.map((name) => (
                    <MenuItem key={name} value={name}>
                      {name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                disableElevation
                startIcon={
                  loading ? (
                    <CircularProgress size={18} color="inherit" />
                  ) : (
                    <PlayArrowIcon />
                  )
                }
                onClick={fetchData}
                disabled={loading || (months === 0 && (!startDate || !endDate))}
                sx={{ height: 40 }}
              >
                {hasLoaded ? "ATUALIZAR" : "CARREGAR"}
              </Button>
            </Stack>
          </Stack>
        </Paper>

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Empty state */}
        {!hasLoaded && !loading && (
          <Paper sx={{ p: 6, textAlign: "center", borderRadius: 2 }}>
            <DashboardIcon
              sx={{ fontSize: 48, color: "action.disabled", mb: 2 }}
            />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Selecione o período e clique em Carregar
            </Typography>
            <Typography variant="body2" color="text.disabled">
              Os dados serão carregados sob demanda para melhor performance.
            </Typography>
          </Paper>
        )}

        {/* Loading skeleton with shimmer */}
        {loading && (
          <>
            {/* Period chip skeleton */}
            <Box sx={{ mb: 2 }}>
              <Skeleton
                variant="rounded"
                width={120}
                height={24}
                animation="wave"
              />
            </Box>

            {/* KPI Cards - 8 cards matching the real layout */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <Grid item xs={6} sm={4} md={3} lg={1.5} key={i}>
                  <Card sx={{ borderRadius: 2 }}>
                    <CardContent
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        py: 1.5,
                        px: 2,
                      }}
                    >
                      <Skeleton
                        variant="rounded"
                        width={40}
                        height={40}
                        animation="wave"
                      />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton
                          variant="text"
                          width="70%"
                          height={14}
                          animation="wave"
                        />
                        <Skeleton
                          variant="text"
                          width="90%"
                          height={24}
                          animation="wave"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            {/* Taxa de Atendimento skeleton */}
            <Paper sx={{ p: 2.5, mb: 3, borderRadius: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 1,
                }}
              >
                <Skeleton
                  variant="text"
                  width={150}
                  height={24}
                  animation="wave"
                />
                <Skeleton
                  variant="text"
                  width={50}
                  height={24}
                  animation="wave"
                />
              </Box>
              <Skeleton
                variant="rounded"
                height={8}
                animation="wave"
                sx={{ borderRadius: 4 }}
              />
            </Paper>

            {/* Main chart - Evolução Mensal */}
            <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
              <Skeleton
                variant="text"
                width={200}
                height={28}
                animation="wave"
                sx={{ mb: 2 }}
              />
              <Skeleton
                variant="rectangular"
                height={350}
                animation="wave"
                sx={{ borderRadius: 1 }}
              />
            </Paper>

            {/* Two charts side by side - Itens por Mês & Valor por Fornecedor */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3, borderRadius: 2, height: 380 }}>
                  <Skeleton
                    variant="text"
                    width={120}
                    height={28}
                    animation="wave"
                    sx={{ mb: 2 }}
                  />
                  <Skeleton
                    variant="rectangular"
                    height={300}
                    animation="wave"
                    sx={{ borderRadius: 1 }}
                  />
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3, borderRadius: 2, height: 380 }}>
                  <Skeleton
                    variant="text"
                    width={160}
                    height={28}
                    animation="wave"
                    sx={{ mb: 2 }}
                  />
                  <Skeleton
                    variant="rectangular"
                    height={300}
                    animation="wave"
                    sx={{ borderRadius: 1 }}
                  />
                </Paper>
              </Grid>
            </Grid>

            {/* Two more charts - Top Itens & Pedidos por Comprador */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3, borderRadius: 2, height: 380 }}>
                  <Skeleton
                    variant="text"
                    width={150}
                    height={28}
                    animation="wave"
                    sx={{ mb: 2 }}
                  />
                  <Skeleton
                    variant="rectangular"
                    height={300}
                    animation="wave"
                    sx={{ borderRadius: 1 }}
                  />
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3, borderRadius: 2, height: 380 }}>
                  <Skeleton
                    variant="text"
                    width={180}
                    height={28}
                    animation="wave"
                    sx={{ mb: 2 }}
                  />
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                      height: 300,
                    }}
                  >
                    <Skeleton
                      variant="circular"
                      width={220}
                      height={220}
                      animation="wave"
                    />
                  </Box>
                </Paper>
              </Grid>
            </Grid>

            {/* Uso Diário skeleton */}
            <Paper sx={{ p: 3, borderRadius: 2 }}>
              <Skeleton
                variant="text"
                width={220}
                height={28}
                animation="wave"
                sx={{ mb: 2 }}
              />
              <Skeleton
                variant="rectangular"
                height={200}
                animation="wave"
                sx={{ borderRadius: 1 }}
              />
            </Paper>
          </>
        )}

        {/* Data loaded */}
        {hasLoaded && !loading && data && (
          <>
            {/* Period indicator */}
            <Box sx={{ mb: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
              <Chip
                label={
                  months === 0 && startDate && endDate
                    ? `${new Date(startDate).toLocaleDateString(
                        "pt-BR"
                      )} - ${new Date(endDate).toLocaleDateString("pt-BR")}`
                    : `Últimos ${months} meses`
                }
                size="small"
                color="primary"
                variant="outlined"
                icon={<DateRangeIcon />}
              />
              {buyerFilter !== "all" && (
                <Chip
                  label={buyerFilter}
                  size="small"
                  color="secondary"
                  onDelete={() => setBuyerFilter("all")}
                />
              )}
            </Box>

            {/* KPIs*/}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              {[
                {
                  label: "Pedidos",
                  value: data.summary.total_orders,
                  icon: ShoppingCartIcon,
                  color: "#5b8def",
                },
                {
                  label: "Itens",
                  value: data.summary.total_items,
                  icon: ReceiptIcon,
                  color: "#68c2ff",
                },
                {
                  label: "Quantidade",
                  value: data.summary.total_quantity.toLocaleString("pt-BR"),
                  icon: InventoryIcon,
                  color: "#6dd3c2",
                },
                {
                  label: "Fornecedores",
                  value: data.summary.total_suppliers,
                  icon: LocalShippingIcon,
                  color: "#c69df6",
                },
                {
                  label: "Total Compras",
                  value: fmtCurrency(data.summary.total_value),
                  icon: TrendingUpIcon,
                  color: "#f57c00",
                },
                {
                  label: "Média/Pedido",
                  value: fmtCurrency(data.summary.avg_order_value),
                  icon: BusinessIcon,
                  color: "#7b1fa2",
                },
                {
                  label: "Atendidos",
                  value: data.summary.fulfilled_orders,
                  icon: CheckCircleIcon,
                  color: "#4caf50",
                },
                {
                  label: "Pendentes",
                  value: data.summary.pending_orders,
                  icon: PendingIcon,
                  color: "#ff9800",
                },
              ].map((kpi) => (
                <Grid item xs={6} sm={4} md={3} lg={1.5} key={kpi.label}>
                  <Card sx={{ borderRadius: 2, height: "100%" }}>
                    <CardContent
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        py: 1.5,
                        px: 2,
                      }}
                    >
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: 1.5,
                          bgcolor: `${kpi.color}15`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}
                      >
                        <kpi.icon sx={{ color: kpi.color, fontSize: 20 }} />
                      </Box>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          noWrap
                        >
                          {kpi.label}
                        </Typography>
                        <Typography variant="subtitle1" fontWeight={600} noWrap>
                          {kpi.value}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            {/* Fulfillment Rate Bar */}
            {data.summary.total_orders > 0 && (
              <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Typography variant="subtitle2">
                    Taxa de Atendimento
                  </Typography>
                  <Typography variant="subtitle2" fontWeight={600}>
                    {data.summary.fulfillment_rate}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={data.summary.fulfillment_rate}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    bgcolor: "#e0e0e0",
                    "& .MuiLinearProgress-bar": {
                      bgcolor:
                        data.summary.fulfillment_rate >= 80
                          ? "#4caf50"
                          : data.summary.fulfillment_rate >= 50
                          ? "#ff9800"
                          : "#f44336",
                    },
                  }}
                />
              </Paper>
            )}

            {/* Monthly Value Chart */}
            <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Evolução Mensal - Valor
              </Typography>
              <Box sx={{ height: 260 }}>
                {data.monthly_data?.length > 0 ? (
                  <Line data={monthlyChart} options={lineOptions} />
                ) : (
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      height: "100%",
                    }}
                  >
                    <Typography color="text.secondary">Sem dados</Typography>
                  </Box>
                )}
              </Box>
            </Paper>

            {/* Itens por Mês */}
            <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Itens por Mês
              </Typography>
              <Box sx={{ height: 220 }}>
                {data.monthly_data?.length > 0 ? (
                  <Bar
                    data={monthlyItemsChart}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { display: false } },
                      scales: {
                        y: {
                          beginAtZero: true,
                          grid: { color: "rgba(0,0,0,0.05)" },
                        },
                        x: { grid: { display: false } },
                      },
                    }}
                  />
                ) : (
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      height: "100%",
                    }}
                  >
                    <Typography color="text.secondary">Sem dados</Typography>
                  </Box>
                )}
              </Box>
            </Paper>

            {/* Buyer & Supplier Charts */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
              <Grid item xs={12} md={4}>
                <Paper
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    height: 400,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Valor por Comprador
                  </Typography>
                  <Box sx={{ flex: 1, minHeight: 0, position: "relative" }}>
                    {buyerValueChart ? (
                      <Doughnut
                        data={buyerValueChart}
                        options={doughnutOptions}
                      />
                    ) : (
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          height: "100%",
                        }}
                      >
                        <Typography color="text.secondary">
                          Sem dados
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    height: 400,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Pedidos por Comprador
                  </Typography>
                  <Box sx={{ flex: 1, minHeight: 0, position: "relative" }}>
                    {buyerOrdersChart ? (
                      <Doughnut
                        data={buyerOrdersChart}
                        options={{
                          ...doughnutOptions,
                          plugins: {
                            ...doughnutOptions.plugins,
                            tooltip: {
                              ...doughnutOptions.plugins.tooltip,
                              callbacks: {
                                label: (ctx) => `${ctx.raw} pedidos`,
                              },
                            },
                          },
                        }}
                      />
                    ) : (
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          height: "100%",
                        }}
                      >
                        <Typography color="text.secondary">
                          Sem dados
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    height: 400,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Valor por Fornecedor
                  </Typography>
                  <Box sx={{ flex: 1, minHeight: 0, position: "relative" }}>
                    {supplierChart ? (
                      <Doughnut
                        data={supplierChart}
                        options={doughnutOptions}
                      />
                    ) : (
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          height: "100%",
                        }}
                      >
                        <Typography color="text.secondary">
                          Sem dados
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Grid>
            </Grid>

            {/* Top Items */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
              <Grid item xs={12} md={8}>
                <Paper
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    height: 420,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Top Itens por Valor
                  </Typography>
                  <Box sx={{ flex: 1, minHeight: 0 }}>
                    {topItemsChart ? (
                      <Bar data={topItemsChart} options={barOptions} />
                    ) : (
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          height: "100%",
                        }}
                      >
                        <Typography color="text.secondary">
                          Sem dados
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Grid>
              <Grid item xs={12} md={4}>
                <Paper
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    height: 420,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Status dos Pedidos
                  </Typography>
                  <Box sx={{ flex: 1, minHeight: 0, position: "relative" }}>
                    {fulfillmentChart ? (
                      <Doughnut
                        data={fulfillmentChart}
                        options={{
                          ...doughnutOptions,
                          plugins: {
                            ...doughnutOptions.plugins,
                            tooltip: {
                              ...doughnutOptions.plugins.tooltip,
                              callbacks: {
                                label: (ctx) => `${ctx.raw} pedidos`,
                              },
                            },
                          },
                        }}
                      />
                    ) : (
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          height: "100%",
                        }}
                      >
                        <Typography color="text.secondary">
                          Sem dados
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Grid>
            </Grid>

            {/* Uso Diário do Sistema */}
            <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                Uso do Sistema (Logins)
              </Typography>
              <Box sx={{ height: 220 }}>
                {data.daily_usage?.length > 0 ? (
                  <Line data={dailyUsageChart} options={usageLineOptions} />
                ) : (
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      height: "100%",
                    }}
                  >
                    <Typography color="text.secondary">Sem dados</Typography>
                  </Box>
                )}
              </Box>
            </Paper>

            {/* NFE Stats (if available) */}
            {data.summary.nfe_count > 0 && (
              <Paper sx={{ p: 4, borderRadius: 2 }}>
                <Typography
                  variant="subtitle1"
                  fontWeight={600}
                  gutterBottom
                  textAlign="center"
                >
                  Notas Fiscais Recebidas
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    gap: 8,
                    py: 3,
                    flexWrap: "wrap",
                  }}
                >
                  <Box sx={{ textAlign: "center" }}>
                    <Typography variant="h4" fontWeight={600} color="primary">
                      {data.summary.nfe_count}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      NFes no período
                    </Typography>
                  </Box>
                  <Divider orientation="vertical" flexItem />
                  <Box sx={{ textAlign: "center" }}>
                    <Typography
                      variant="h5"
                      fontWeight={600}
                      color="success.main"
                    >
                      {fmtCurrency(data.summary.nfe_total_value)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Valor total NFes
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            )}
          </>
        )}
      </Container>
    </Box>
  );
};

export default Dashboard;
