import React, { useState, useEffect, useMemo, useCallback } from "react";
import axios from "axios";
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Stack,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
  Tooltip,
  Fade,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Chip
} from "@mui/material";
import {
  Assessment as AssessmentIcon,
  PlayArrow as PlayArrowIcon,
  FileDownload as FileDownloadIcon,
  WarningAmber as WarningAmberIcon,
  Close as CloseIcon
} from "@mui/icons-material";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
);

const MONTH_NAMES = [
  "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
  "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
];

const MONTH_SHORT = [
  "JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
  "JUL", "AGO", "SET", "OUT", "NOV", "DEZ",
];

const CATEGORY_COLORS = [
  "#1565c0", "#e65100", "#2e7d32", "#6a1b9a", "#c62828",
  "#00838f", "#4e342e", "#283593", "#ef6c00", "#ad1457",
  "#00695c", "#37474f",
];

const fmtCurrency = (v) => {
  if (v === 0 || v === null || v === undefined) return "-";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  }).format(v);
};

const fmtCompact = (v) => {
  if (v === 0) return "R$ 0";
  if (v >= 1000000) return `R$ ${(v / 1000000).toFixed(1)}M`;
  if (v >= 1000) return `R$ ${(v / 1000).toFixed(0)}k`;
  return `R$ ${v.toFixed(0)}`;
};

// Shared cell styles
const headerCellSx = {
  fontWeight: 700,
  fontSize: "0.7rem",
  color: "#1a1f2e",
  bgcolor: "#ffd54f",
  borderRight: "1px solid rgba(0,0,0,0.08)",
  borderBottom: "2px solid rgba(0,0,0,0.12)",
  py: 0.8,
  px: 1,
  whiteSpace: "nowrap",
  textAlign: "center",
  letterSpacing: "0.02em",
};

const dataCellSx = {
  fontSize: "0.72rem",
  py: 0.6,
  px: 1,
  borderRight: "1px solid rgba(0,0,0,0.04)",
  textAlign: "right",
  fontFamily: "'Roboto Mono', monospace",
  color: "#333",
};

const categoryCellSx = {
  fontWeight: 600,
  fontSize: "0.72rem",
  py: 0.6,
  px: 1,
  borderRight: "1px solid rgba(0,0,0,0.08)",
  textAlign: "left",
  whiteSpace: "nowrap",
  color: "#1a1f2e",
  bgcolor: "rgba(255,213,79,0.08)",
};

const totalRowCellSx = {
  fontWeight: 700,
  fontSize: "0.72rem",
  py: 0.8,
  px: 1,
  borderRight: "1px solid rgba(0,0,0,0.08)",
  textAlign: "right",
  fontFamily: "'Roboto Mono', monospace",
  bgcolor: "#fff8e1",
  color: "#1a1f2e",
  borderTop: "2px solid rgba(0,0,0,0.15)",
};

const PurchaseReport = () => {
  const apiUrl = import.meta.env.VITE_API_URL;

  // Filter state
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [loadingUsers, setLoadingUsers] = useState(true);

  // Report state
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Unmatched Dialog state
  const [unmatchedDialogOpen, setUnmatchedDialogOpen] = useState(false);
  const [savingOverrideId, setSavingOverrideId] = useState(null);

  // Generate year options (current year down to 5 years ago)
  const yearOptions = useMemo(() => {
    const current = new Date().getFullYear();
    return Array.from({ length: 6 }, (_, i) => current - i);
  }, []);

  // Fetch purchaser users on mount
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoadingUsers(true);
        const res = await axios.get(`${apiUrl}/api/purchaser-users`, {
          withCredentials: true,
        });
        const data = res.data || [];
        setUsers(data);
        if (data.length === 1) {
          setSelectedUserId(data[0].id);
        }
      } catch (e) {
        console.error("Error fetching users:", e);
        setError("Erro ao carregar lista de compradores");
      } finally {
        setLoadingUsers(false);
      }
    };
    fetchUsers();
  }, [apiUrl]);

  // Fetch report
  const fetchReport = useCallback(async () => {
    if (!selectedUserId || !year) return;
    try {
      setLoading(true);
      setError("");
      setReportData(null);
      const res = await axios.get(`${apiUrl}/api/purchase-category-report`, {
        params: { user_id: selectedUserId, year },
        withCredentials: true,
      });
      setReportData(res.data);
    } catch (e) {
      const msg = e.response?.data?.error || "Erro ao carregar relatório";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, selectedUserId, year]);

  const handleSaveOverride = async (purchaseOrderId, categoryId) => {
    if (!categoryId) return;
    try {
      setSavingOverrideId(purchaseOrderId);
      await axios.post(
        `${apiUrl}/api/purchase-category-override`,
        { purchase_order_id: purchaseOrderId, category_id: categoryId },
        { withCredentials: true }
      );
      // Re-fetch report data implicitly closes dialog nicely
      await fetchReport();
    } catch (e) {
      console.error("Error saving override", e);
      alert("Erro ao salvar categoria do pedido.");
    } finally {
      setSavingOverrideId(null);
    }
  };

  // Chart data
  const chartData = useMemo(() => {
    if (!reportData) return null;
    const { category_names, data } = reportData;

    return {
      labels: MONTH_SHORT,
      datasets: category_names.map((cat, idx) => ({
        label: cat,
        data: data[cat],
        borderColor: CATEGORY_COLORS[idx % CATEGORY_COLORS.length],
        backgroundColor: `${CATEGORY_COLORS[idx % CATEGORY_COLORS.length]}22`,
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: "#fff",
        pointBorderColor: CATEGORY_COLORS[idx % CATEGORY_COLORS.length],
        pointBorderWidth: 2,
        tension: 0.3,
        fill: false,
      })),
    };
  }, [reportData]);

  // Also create a TOTAL line dataset
  const chartDataWithTotal = useMemo(() => {
    if (!chartData || !reportData) return null;
    return {
      ...chartData,
      datasets: [
        ...chartData.datasets,
        {
          label: "TOTAL",
          data: reportData.month_totals,
          borderColor: "#212121",
          backgroundColor: "rgba(33,33,33,0.05)",
          borderWidth: 2.5,
          borderDash: [6, 3],
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: "#fff",
          pointBorderColor: "#212121",
          pointBorderWidth: 2,
          tension: 0.3,
          fill: false,
        },
      ],
    };
  }, [chartData, reportData]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          boxWidth: 12,
          padding: 14,
          font: { size: 10.5, family: "'Inter', sans-serif" },
          usePointStyle: true,
          pointStyle: "line",
        },
      },
      tooltip: {
        backgroundColor: "rgba(255,255,255,0.97)",
        titleColor: "#1a1f2e",
        bodyColor: "#333",
        borderColor: "#e0e0e0",
        borderWidth: 1,
        padding: 12,
        titleFont: { weight: "bold", size: 12 },
        bodyFont: { size: 11 },
        callbacks: {
          label: (ctx) => {
            const value = ctx.parsed.y;
            if (value === 0) return `${ctx.dataset.label}: -`;
            return `${ctx.dataset.label}: ${fmtCurrency(value)}`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: "rgba(0,0,0,0.04)" },
        ticks: {
          callback: (v) => fmtCompact(v),
          font: { size: 10 },
          maxTicksLimit: 8,
        },
      },
      x: {
        grid: { display: false },
        ticks: { font: { size: 10, weight: "bold" } },
      },
    },
  }), []);

  // Export to Excel helper
  const handleExportExcel = useCallback(() => {
    if (!reportData) return;
    try {
      const XLSX = require("xlsx");
      const { category_names, data, category_totals, category_averages, month_totals, grand_total, user_name, year: rYear } = reportData;

      const wsData = [];
      // Title
      wsData.push([`RELATÓRIO DE COMPRAS ${rYear}`]);
      wsData.push([]);

      // Header
      wsData.push(["GÊNERO", ...MONTH_NAMES, "TOTAL"]);

      // Category rows
      category_names.forEach((cat) => {
        wsData.push([cat, ...data[cat], category_totals[cat]]);
      });

      // Total row
      wsData.push(["TOTAL", ...month_totals, grand_total]);
      wsData.push([]);

      // Summary
      wsData.push(["RESUMO GÊNERO", "TOTAL", "MÉDIA MÊS"]);
      category_names.forEach((cat) => {
        wsData.push([cat, category_totals[cat], category_averages[cat]]);
      });

      const ws = XLSX.utils.aoa_to_sheet(wsData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Relatório");
      XLSX.writeFile(wb, `relatorio_compras_${rYear}_${user_name}.xlsx`);
    } catch {
      // xlsx not available, fallback to CSV
      const { category_names, data, category_totals, month_totals, grand_total } = reportData;
      let csv = `GÊNERO;${MONTH_NAMES.join(";")};TOTAL\n`;
      category_names.forEach((cat) => {
        csv += `${cat};${data[cat].join(";")};${category_totals[cat]}\n`;
      });
      csv += `TOTAL;${month_totals.join(";")};${grand_total}\n`;
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `relatorio_compras_${reportData.year}.csv`;
      link.click();
    }
  }, [reportData]);

  // --- Render ---

  return (
    <Box sx={{ minHeight: "100%", bgcolor: "#f5f6fa", p: { xs: 1.5, md: 3 } }}>
      <Container maxWidth="xl" disableGutters>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 0.5 }}>
            <AssessmentIcon sx={{ fontSize: 28, color: "#1565c0" }} />
            <Typography
              variant="h5"
              component="h1"
              sx={{ fontWeight: 700, color: "#1a1f2e", letterSpacing: "-0.02em" }}
            >
              Relatório de Compras
            </Typography>
            
            {/* Warning Badge for Unmatched Orders */}
            {reportData?.unmatched_orders?.length > 0 && (
              <Chip 
                icon={<WarningAmberIcon />}
                label={`${reportData.unmatched_orders.length} pedidos sem categoria`}
                color="warning"
                onClick={() => setUnmatchedDialogOpen(true)}
                sx={{ ml: 2, fontWeight: 600, cursor: "pointer", boxShadow: 1 }}
              />
            )}
          </Stack>
          <Typography variant="body2" sx={{ color: "rgba(26,31,46,0.55)", pl: 5.5 }}>
            Análise de compras por categoria e mês
          </Typography>
        </Box>

        {/* Filters */}
        <Paper
          elevation={0}
          sx={{
            p: 2.5,
            mb: 3,
            borderRadius: 2.5,
            border: "1px solid rgba(0,0,0,0.06)",
            bgcolor: "#fff",
          }}
        >
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            alignItems={{ sm: "center" }}
          >
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel>Comprador</InputLabel>
              <Select
                label="Comprador"
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                disabled={loadingUsers}
              >
                {users.map((u) => (
                  <MenuItem key={u.id} value={u.id}>
                    {u.system_name || u.username}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Ano</InputLabel>
              <Select
                label="Ano"
                value={year}
                onChange={(e) => setYear(e.target.value)}
              >
                {yearOptions.map((y) => (
                  <MenuItem key={y} value={y}>
                    {y}
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
              onClick={fetchReport}
              disabled={loading || !selectedUserId}
              sx={{
                height: 40,
                bgcolor: "#1565c0",
                "&:hover": { bgcolor: "#0d47a1" },
                textTransform: "none",
                fontWeight: 600,
                px: 3,
              }}
            >
              {reportData ? "Atualizar" : "Carregar"}
            </Button>

            {reportData && (
              <Tooltip title="Exportar para Excel/CSV" arrow>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<FileDownloadIcon />}
                  onClick={handleExportExcel}
                  sx={{
                    height: 40,
                    textTransform: "none",
                    borderColor: "rgba(0,0,0,0.15)",
                    color: "#555",
                  }}
                >
                  Exportar
                </Button>
              </Tooltip>
            )}
          </Stack>
        </Paper>

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loading && (
          <Paper
            elevation={0}
            sx={{ p: 4, borderRadius: 2.5, border: "1px solid rgba(0,0,0,0.06)" }}
          >
            <Skeleton variant="text" width={300} height={32} sx={{ mb: 2 }} animation="wave" />
            <Skeleton variant="rectangular" height={200} sx={{ mb: 3, borderRadius: 1 }} animation="wave" />
            <Skeleton variant="rectangular" height={250} sx={{ borderRadius: 1 }} animation="wave" />
          </Paper>
        )}

        {/* Empty state */}
        {!loading && !reportData && !error && (
          <Paper
            elevation={0}
            sx={{
              p: 6,
              textAlign: "center",
              borderRadius: 2.5,
              border: "1px solid rgba(0,0,0,0.06)",
              bgcolor: "#fff",
            }}
          >
            <AssessmentIcon sx={{ fontSize: 52, color: "rgba(21,101,192,0.15)", mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Selecione o comprador e o ano
            </Typography>
            <Typography variant="body2" color="text.disabled">
              Clique em "Carregar" para gerar o relatório de compras por categoria.
            </Typography>
          </Paper>
        )}

        {/* Report Data */}
        {reportData && !loading && (
          <Fade in timeout={400}>
            <Box>
              {/* Report Title */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  mb: 2,
                  borderRadius: 2.5,
                  border: "1px solid rgba(0,0,0,0.06)",
                  bgcolor: "#1a1f2e",
                  textAlign: "center",
                }}
              >
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 700,
                    color: "#ffd54f",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    fontSize: "1rem",
                  }}
                >
                  Relatório de Compras {reportData.year}
                </Typography>
                <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.6)" }}>
                  {reportData.user_name} — Departamento de Compras
                </Typography>
              </Paper>

              {/* Main Data Table */}
              <Paper
                elevation={0}
                sx={{
                  mb: 2,
                  borderRadius: 2.5,
                  border: "1px solid rgba(0,0,0,0.06)",
                  overflow: "hidden",
                }}
              >
                <TableContainer sx={{ maxHeight: 600 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ ...headerCellSx, textAlign: "left", minWidth: 140, position: "sticky", left: 0, zIndex: 3 }}>
                          GÊNERO
                        </TableCell>
                        {MONTH_NAMES.map((m) => (
                          <TableCell key={m} sx={{ ...headerCellSx, minWidth: 90 }}>
                            {m}
                          </TableCell>
                        ))}
                        <TableCell sx={{ ...headerCellSx, minWidth: 110, bgcolor: "#ffca28" }}>
                          TOTAL
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {reportData.category_names.map((cat, catIdx) => (
                        <TableRow
                          key={cat}
                          sx={{
                            "&:hover": { bgcolor: "rgba(21,101,192,0.03)" },
                            bgcolor: catIdx % 2 === 0 ? "#fff" : "rgba(0,0,0,0.01)",
                          }}
                        >
                          <TableCell sx={{ ...categoryCellSx, position: "sticky", left: 0, zIndex: 1, bgcolor: catIdx % 2 === 0 ? "#fff" : "#fafafa" }}>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 0.8 }}>
                              <Box
                                sx={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "50%",
                                  bgcolor: CATEGORY_COLORS[catIdx % CATEGORY_COLORS.length],
                                  flexShrink: 0,
                                }}
                              />
                              {cat}
                            </Box>
                          </TableCell>
                          {reportData.data[cat].map((val, mIdx) => (
                            <TableCell
                              key={mIdx}
                              sx={{
                                ...dataCellSx,
                                color: val > 0 ? "#1a1f2e" : "rgba(0,0,0,0.2)",
                              }}
                            >
                              {val > 0 ? fmtCurrency(val) : "-"}
                            </TableCell>
                          ))}
                          <TableCell
                            sx={{
                              ...dataCellSx,
                              fontWeight: 700,
                              bgcolor: "rgba(255,213,79,0.08)",
                              color: "#1a1f2e",
                            }}
                          >
                            {fmtCurrency(reportData.category_totals[cat])}
                          </TableCell>
                        </TableRow>
                      ))}

                      {/* TOTAL row */}
                      <TableRow>
                        <TableCell
                          sx={{
                            ...totalRowCellSx,
                            textAlign: "left",
                            fontWeight: 800,
                            position: "sticky",
                            left: 0,
                            zIndex: 1,
                          }}
                        >
                          TOTAL
                        </TableCell>
                        {reportData.month_totals.map((val, idx) => (
                          <TableCell key={idx} sx={totalRowCellSx}>
                            {val > 0 ? fmtCurrency(val) : "-"}
                          </TableCell>
                        ))}
                        <TableCell
                          sx={{
                            ...totalRowCellSx,
                            fontWeight: 800,
                            bgcolor: "#ffecb3",
                            fontSize: "0.78rem",
                          }}
                        >
                          {fmtCurrency(reportData.grand_total)}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>

              {/* Bottom Section: Summary + Chart */}
              <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
                {/* Summary Table */}
                <Paper
                  elevation={0}
                  sx={{
                    borderRadius: 2.5,
                    border: "1px solid rgba(0,0,0,0.06)",
                    overflow: "hidden",
                    flex: "0 0 auto",
                    width: { xs: "100%", lg: 380 },
                  }}
                >
                  <Box sx={{ p: 1.5, bgcolor: "#1a1f2e" }}>
                    <Typography
                      variant="subtitle2"
                      sx={{ color: "#ffd54f", fontWeight: 700, letterSpacing: "0.04em" }}
                    >
                      RESUMO GÊNERO
                    </Typography>
                  </Box>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ ...headerCellSx, textAlign: "left" }}>GÊNERO</TableCell>
                        <TableCell sx={headerCellSx}>TOTAL</TableCell>
                        <TableCell sx={headerCellSx}>MÉDIA MÊS</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {reportData.category_names.map((cat, idx) => (
                        <TableRow
                          key={cat}
                          sx={{
                            bgcolor: idx % 2 === 0 ? "#fff" : "rgba(0,0,0,0.015)",
                            "&:hover": { bgcolor: "rgba(21,101,192,0.03)" },
                          }}
                        >
                          <TableCell
                            sx={{
                              fontSize: "0.72rem",
                              fontWeight: 600,
                              py: 0.5,
                              px: 1,
                              color: "#1a1f2e",
                              borderRight: "1px solid rgba(0,0,0,0.06)",
                            }}
                          >
                            <Box sx={{ display: "flex", alignItems: "center", gap: 0.8 }}>
                              <Box
                                sx={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "50%",
                                  bgcolor: CATEGORY_COLORS[idx % CATEGORY_COLORS.length],
                                  flexShrink: 0,
                                }}
                              />
                              {cat}
                            </Box>
                          </TableCell>
                          <TableCell sx={{ ...dataCellSx, fontWeight: 600 }}>
                            {fmtCurrency(reportData.category_totals[cat])}
                          </TableCell>
                          <TableCell sx={dataCellSx}>
                            {fmtCurrency(reportData.category_averages[cat])}
                          </TableCell>
                        </TableRow>
                      ))}
                      {/* Grand total row */}
                      <TableRow>
                        <TableCell sx={{ ...totalRowCellSx, textAlign: "left", fontWeight: 800 }}>
                          TOTAL
                        </TableCell>
                        <TableCell sx={{ ...totalRowCellSx, fontWeight: 800 }}>
                          {fmtCurrency(reportData.grand_total)}
                        </TableCell>
                        <TableCell sx={totalRowCellSx}>
                          {fmtCurrency(
                            Object.values(reportData.category_averages).reduce((a, b) => a + b, 0)
                          )}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>

                  {/* Footer info */}
                  <Box sx={{ p: 1.5, borderTop: "1px solid rgba(0,0,0,0.06)", bgcolor: "rgba(0,0,0,0.015)" }}>
                    <Typography
                      variant="caption"
                      sx={{ color: "rgba(0,0,0,0.45)", display: "block", fontStyle: "italic" }}
                    >
                      {reportData.generated_at}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{ color: "#1565c0", fontWeight: 600, display: "block", mt: 0.3 }}
                    >
                      {reportData.user_name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: "rgba(0,0,0,0.45)" }}>
                      Departamento de Compras
                    </Typography>
                  </Box>
                </Paper>

                {/* Chart */}
                <Paper
                  elevation={0}
                  sx={{
                    borderRadius: 2.5,
                    border: "1px solid rgba(0,0,0,0.06)",
                    flex: 1,
                    overflow: "hidden",
                    minWidth: 0,
                  }}
                >
                  <Box sx={{ p: 1.5, bgcolor: "#1a1f2e" }}>
                    <Typography
                      variant="subtitle2"
                      sx={{ color: "#ffd54f", fontWeight: 700, letterSpacing: "0.04em" }}
                    >
                      GRÁFICO RELATÓRIO DE COMPRAS {reportData.year}
                    </Typography>
                  </Box>
                  <Box sx={{ p: 2, height: { xs: 300, md: 380 } }}>
                    {chartDataWithTotal && (
                      <Line data={chartDataWithTotal} options={chartOptions} />
                    )}
                  </Box>
                </Paper>
              </Stack>
            </Box>
          </Fade>
        )}
      </Container>
      
      {/* Unmatched Orders Dialog */}
      {reportData && (
        <Dialog 
          open={unmatchedDialogOpen} 
          onClose={() => setUnmatchedDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle sx={{ bgcolor: "#f5f6fa", borderBottom: "1px solid rgba(0,0,0,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <WarningAmberIcon color="warning" />
              <Typography variant="h6" fontWeight="bold">
                Pedidos Não Categorizados
              </Typography>
            </Box>
            <IconButton onClick={() => setUnmatchedDialogOpen(false)}>
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ p: 0 }}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: "#f9f9f9" }}>
                    <TableCell sx={{ fontWeight: "bold" }}>Pedido</TableCell>
                    <TableCell sx={{ fontWeight: "bold" }}>Data</TableCell>
                    <TableCell sx={{ fontWeight: "bold" }}>Fornecedor</TableCell>
                    <TableCell sx={{ fontWeight: "bold" }}>Última linha (Obs)</TableCell>
                    <TableCell sx={{ fontWeight: "bold" }}>Total</TableCell>
                    <TableCell sx={{ fontWeight: "bold", width: 200 }}>Categoria</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reportData.unmatched_orders?.map((order) => (
                    <TableRow key={order.id} hover>
                      <TableCell>{order.cod_pedc}</TableCell>
                      <TableCell>{order.dt_emis}</TableCell>
                      <TableCell>{order.fornecedor_descricao}</TableCell>
                      <TableCell sx={{ maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        <Tooltip title={order.observacao_last_line || "Sem observação"}>
                          <span>{order.observacao_last_line || "-"}</span>
                        </Tooltip>
                      </TableCell>
                      <TableCell>{fmtCurrency(order.total)}</TableCell>
                      <TableCell>
                        <FormControl size="small" fullWidth>
                          <Select
                            displayEmpty
                            value=""
                            onChange={(e) => handleSaveOverride(order.id, e.target.value)}
                            disabled={savingOverrideId === order.id}
                            sx={{ fontSize: "0.85rem" }}
                            renderValue={() => savingOverrideId === order.id ? "Salvando..." : "Selecionar..."}
                          >
                            {reportData.categories.map((c) => (
                              <MenuItem key={c.id} value={c.id} sx={{ fontSize: "0.85rem" }}>
                                {c.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </TableCell>
                    </TableRow>
                  ))}
                  {reportData.unmatched_orders?.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 3, color: "text.secondary" }}>
                        Nenhum pedido sem categoria.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </DialogContent>
          <DialogActions sx={{ p: 2, bgcolor: "#f5f6fa", borderTop: "1px solid rgba(0,0,0,0.06)" }}>
            <Button onClick={() => setUnmatchedDialogOpen(false)} variant="outlined">
              Fechar
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
};

export default PurchaseReport;
