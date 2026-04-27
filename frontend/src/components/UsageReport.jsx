import React, { useState, useCallback, useMemo, useEffect } from "react";
import axios from "axios";
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Alert,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Stack,
  Skeleton,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Chip,
  TextField,
  FormControlLabel,
  Checkbox,
} from "@mui/material";
import {
  People as PeopleIcon,
  Http as HttpIcon,
  Login as LoginIcon,
  PlayArrow as PlayArrowIcon,
  TrendingUp as TrendingUpIcon,
  BarChart as BarChartIcon,
} from "@mui/icons-material";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Bar, Line, Doughnut } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

const KPICard = ({ title, value, icon, color, loading }) => (
  <Card
    elevation={0}
    sx={{
      borderRadius: 3,
      border: "1px solid",
      borderColor: "divider",
      height: "100%",
    }}
  >
    <CardContent sx={{ p: 2.5 }}>
      <Stack direction="row" alignItems="center" spacing={2}>
        <Box
          sx={{
            p: 1.5,
            borderRadius: 2,
            bgcolor: `${color}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {React.cloneElement(icon, { sx: { color, fontSize: 28 } })}
        </Box>
        <Box>
          <Typography variant="body2" color="text.secondary" fontWeight={500}>
            {title}
          </Typography>
          {loading ? (
            <Skeleton width={60} height={36} />
          ) : (
            <Typography variant="h5" fontWeight={700}>
              {typeof value === "number"
                ? value.toLocaleString("pt-BR")
                : value}
            </Typography>
          )}
        </Box>
      </Stack>
    </CardContent>
  </Card>
);

const UsageReport = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [days, setDays] = useState(30);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [includeImport, setIncludeImport] = useState(false);
  const [sortField, setSortField] = useState("request_count");
  const [sortDirection, setSortDirection] = useState("desc");

  const apiUrl = import.meta.env.VITE_API_URL;

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      
      if (startDate && endDate) {
        params.append("start_date", startDate);
        params.append("end_date", endDate);
      } else {
        params.append("days", days);
      }
      
      // Always explicitly send the include_import parameter
      params.append("include_import", includeImport ? "true" : "false");
      
      const res = await axios.get(`${apiUrl}/api/usage_report?${params}`, {
        withCredentials: true,
      });
      setData(res.data);
    } catch (err) {
      setError(
        err.response?.status === 403
          ? "Acesso negado. Apenas administradores podem acessar este relatório."
          : "Erro ao carregar relatório de uso.",
      );
    } finally {
      setLoading(false);
    }
  }, [apiUrl, days, startDate, endDate, includeImport]);

  // Auto-fetch when includeImport checkbox changes (if we have existing data)
  useEffect(() => {
    if (data) {
      fetchReport();
    }
  }, [includeImport]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortedUsers = useMemo(() => {
    if (!data?.users) return [];
    return [...data.users].sort((a, b) => {
      const mul = sortDirection === "asc" ? 1 : -1;
      if (sortField === "username" || sortField === "email") {
        return mul * (a[sortField] || "").localeCompare(b[sortField] || "");
      }
      return mul * ((a[sortField] || 0) - (b[sortField] || 0));
    });
  }, [data, sortField, sortDirection]);

  const totalLogins = useMemo(
    () => (data?.users || []).reduce((s, u) => s + u.login_count, 0),
    [data],
  );
  const totalRequests = useMemo(
    () => (data?.users || []).reduce((s, u) => s + u.request_count, 0),
    [data],
  );
  const activeUsers = useMemo(
    () => (data?.users || []).filter((u) => u.login_count > 0).length,
    [data],
  );

  // Charts
  const dailyActivityChart = useMemo(() => {
    if (!data) return null;
    const allDates = new Set([
      ...(data.daily_logins || []).map((d) => d.date),
      ...(data.daily_requests || []).map((d) => d.date),
    ]);
    const sorted = [...allDates].sort();
    const loginsMap = Object.fromEntries(
      (data.daily_logins || []).map((d) => [d.date, d.count]),
    );
    const requestsMap = Object.fromEntries(
      (data.daily_requests || []).map((d) => [d.date, d.count]),
    );

    return {
      labels: sorted.map((d) => {
        const date = new Date(d);
        return date.toLocaleDateString("pt-BR", {
          day: "2-digit",
          month: "2-digit",
        });
      }),
      datasets: [
        {
          label: "Requisições",
          data: sorted.map((d) => requestsMap[d] || 0),
          borderColor: "#2196f3",
          backgroundColor: "rgba(33, 150, 243, 0.1)",
          fill: true,
          tension: 0.4,
        },
        {
          label: "Logins",
          data: sorted.map((d) => loginsMap[d] || 0),
          borderColor: "#4caf50",
          backgroundColor: "rgba(76, 175, 80, 0.1)",
          fill: true,
          tension: 0.4,
        },
      ],
    };
  }, [data]);

  const usersBarChart = useMemo(() => {
    if (!data?.users) return null;
    const top = [...data.users]
      .sort((a, b) => b.request_count - a.request_count)
      .slice(0, 10);
    return {
      labels: top.map((u) => u.username),
      datasets: [
        {
          label: "Requisições",
          data: top.map((u) => u.request_count),
          backgroundColor: "rgba(33, 150, 243, 0.7)",
          borderRadius: 6,
        },
        {
          label: "Logins",
          data: top.map((u) => u.login_count),
          backgroundColor: "rgba(76, 175, 80, 0.7)",
          borderRadius: 6,
        },
      ],
    };
  }, [data]);

  const endpointsDoughnut = useMemo(() => {
    if (!data?.top_endpoints?.length) return null;
    const colors = [
      "#2196f3",
      "#4caf50",
      "#ff9800",
      "#e91e63",
      "#9c27b0",
      "#00bcd4",
      "#ff5722",
      "#607d8b",
      "#795548",
      "#3f51b5",
    ];
    return {
      labels: data.top_endpoints.map(
        (e) =>
          `${e.method} ${e.endpoint.length > 30 ? "..." + e.endpoint.slice(-27) : e.endpoint}`,
      ),
      datasets: [
        {
          data: data.top_endpoints.map((e) => e.count),
          backgroundColor: colors.slice(0, data.top_endpoints.length),
          borderWidth: 0,
        },
      ],
    };
  }, [data]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "top", labels: { usePointStyle: true, padding: 15 } },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { precision: 0 },
        grid: { color: "rgba(0,0,0,0.06)" },
      },
      x: { grid: { display: false } },
    },
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        spacing={2}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Relatório de Uso
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Acompanhe a atividade dos usuários no sistema
          </Typography>
        </Box>
        <Stack spacing={2} sx={{ width: { xs: "100%", sm: "auto" } }}>
          {/* Period Selector */}
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ xs: "stretch", sm: "center" }}>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Período Padrão</InputLabel>
              <Select
                value={days}
                label="Período Padrão"
                onChange={(e) => {
                  const newDays = e.target.value;
                  setDays(newDays);
                  // Calculate date range from days
                  const today = new Date();
                  const start = new Date(today.getTime() - newDays * 24 * 60 * 60 * 1000);
                  setStartDate(start.toISOString().split("T")[0]);
                  setEndDate(today.toISOString().split("T")[0]);
                }}
              >
                <MenuItem value={7}>Últimos 7 dias</MenuItem>
                <MenuItem value={15}>Últimos 15 dias</MenuItem>
                <MenuItem value={30}>Últimos 30 dias</MenuItem>
                <MenuItem value={60}>Últimos 60 dias</MenuItem>
                <MenuItem value={90}>Últimos 90 dias</MenuItem>
                <MenuItem value={180}>Últimos 180 dias</MenuItem>
                <MenuItem value={365}>Último ano</MenuItem>
              </Select>
            </FormControl>
            <Typography variant="body2" color="text.secondary" sx={{ display: { xs: "none", sm: "block" } }}>
              ou
            </Typography>
          </Stack>

          {/* Date Range Selectors */}
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ xs: "stretch", sm: "center" }}>
            <TextField
              size="small"
              type="date"
              label="Data Inicial"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ minWidth: 130 }}
            />
            <TextField
              size="small"
              type="date"
              label="Data Final"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ minWidth: 130 }}
            />
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={fetchReport}
              disabled={loading}
              sx={{ borderRadius: 2, textTransform: "none", fontWeight: 600 }}
            >
              {loading ? "Carregando..." : "Gerar Relatório"}
            </Button>
          </Stack>

          {/* Include Import Checkbox */}
          <FormControlLabel
            control={
              <Checkbox
                checked={includeImport}
                onChange={(e) => setIncludeImport(e.target.checked)}
                size="small"
              />
            }
            label="Incluir endpoint /api/import"
            sx={{ ml: 0 }}
          />
        </Stack>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Usuários Ativos"
            value={activeUsers}
            icon={<PeopleIcon />}
            color="#2196f3"
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Total de Logins"
            value={totalLogins}
            icon={<LoginIcon />}
            color="#4caf50"
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Total de Requisições"
            value={totalRequests}
            icon={<HttpIcon />}
            color="#ff9800"
            loading={loading}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Média Req/Usuário"
            value={
              activeUsers > 0 ? Math.round(totalRequests / activeUsers) : 0
            }
            icon={<TrendingUpIcon />}
            color="#e91e63"
            loading={loading}
          />
        </Grid>
      </Grid>

      {data && (
        <>
          {/* Charts */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, md: 8 }}>
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: "1px solid",
                  borderColor: "divider",
                  height: 380,
                }}
              >
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Atividade Diária
                </Typography>
                {dailyActivityChart && (
                  <Box sx={{ height: 310 }}>
                    <Line data={dailyActivityChart} options={chartOptions} />
                  </Box>
                )}
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: "1px solid",
                  borderColor: "divider",
                  height: 380,
                }}
              >
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Top Endpoints
                </Typography>
                {endpointsDoughnut ? (
                  <Box sx={{ height: 310 }}>
                    <Doughnut
                      data={endpointsDoughnut}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: "bottom",
                            labels: {
                              usePointStyle: true,
                              padding: 10,
                              font: { size: 11 },
                            },
                          },
                        },
                      }}
                    />
                  </Box>
                ) : (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 4, textAlign: "center" }}
                  >
                    Sem dados de endpoints no período.
                  </Typography>
                )}
              </Paper>
            </Grid>
          </Grid>

          {/* Bar chart - users */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12 }}>
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  borderRadius: 3,
                  border: "1px solid",
                  borderColor: "divider",
                  height: 380,
                }}
              >
                <Stack
                  direction="row"
                  alignItems="center"
                  spacing={1}
                  sx={{ mb: 1 }}
                >
                  <BarChartIcon color="primary" />
                  <Typography variant="subtitle1" fontWeight={600}>
                    Uso por Usuário (Top 10)
                  </Typography>
                </Stack>
                {usersBarChart && (
                  <Box sx={{ height: 310 }}>
                    <Bar data={usersBarChart} options={chartOptions} />
                  </Box>
                )}
              </Paper>
            </Grid>
          </Grid>

          {/* Table */}
          <Paper
            elevation={0}
            sx={{
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              overflow: "hidden",
            }}
          >
            <Box sx={{ p: 2.5, pb: 1 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                Detalhamento por Usuário
              </Typography>
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      <TableSortLabel
                        active={sortField === "username"}
                        direction={
                          sortField === "username" ? sortDirection : "asc"
                        }
                        onClick={() => handleSort("username")}
                      >
                        Usuário
                      </TableSortLabel>
                    </TableCell>
                    <TableCell>
                      <TableSortLabel
                        active={sortField === "email"}
                        direction={
                          sortField === "email" ? sortDirection : "asc"
                        }
                        onClick={() => handleSort("email")}
                      >
                        Email
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortField === "login_count"}
                        direction={
                          sortField === "login_count" ? sortDirection : "asc"
                        }
                        onClick={() => handleSort("login_count")}
                      >
                        Logins
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortField === "request_count"}
                        direction={
                          sortField === "request_count" ? sortDirection : "asc"
                        }
                        onClick={() => handleSort("request_count")}
                      >
                        Requisições
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="center">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sortedUsers.map((user) => (
                    <TableRow key={user.user_id} hover>
                      <TableCell sx={{ fontWeight: 500 }}>
                        {user.username}
                      </TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell align="right">
                        {user.login_count.toLocaleString("pt-BR")}
                      </TableCell>
                      <TableCell align="right">
                        {user.request_count.toLocaleString("pt-BR")}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={user.login_count > 0 ? "Ativo" : "Inativo"}
                          color={user.login_count > 0 ? "success" : "default"}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </>
      )}

      {!data && !loading && !error && (
        <Paper
          elevation={0}
          sx={{
            p: 6,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            textAlign: "center",
          }}
        >
          <BarChartIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            Selecione um período e clique em "Gerar Relatório"
          </Typography>
          <Typography variant="body2" color="text.disabled">
            O relatório mostrará logins, requisições e atividade dos usuários.
          </Typography>
        </Paper>
      )}
    </Container>
  );
};

export default UsageReport;
