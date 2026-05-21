import React, { useState, useCallback, useMemo, useEffect } from "react";
import axios from "axios";
import {
  Box, Container, Grid, Paper, Typography, Card, CardContent,
  Alert, MenuItem, Select, FormControl, InputLabel, Stack, Skeleton,
  Button, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, TableSortLabel, Chip, useTheme
} from "@mui/material";
import {
  People as PeopleIcon,
  Http as HttpIcon,
  Timer as TimerIcon,
  WarningAmber as WarningIcon,
  PlayArrow as PlayArrowIcon,
  Search as SearchIcon,
} from "@mui/icons-material";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend, Filler } from "chart.js";
import { Bar, Line, Doughnut } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend, Filler);

const KPICard = ({ title, value, subtitle, icon, color, loading, index = 0 }) => (
  <Card
    elevation={0}
    sx={{
      borderRadius: 3,
      border: "1px solid",
      borderColor: "divider",
      height: "100%",
      background: "linear-gradient(140deg, rgba(255,255,255,0.9), rgba(255,255,255,0.6))",
      backdropFilter: "blur(6px)",
      boxShadow: "0 16px 40px rgba(15, 23, 42, 0.08)",
      animation: "cardIn 0.6s ease both",
      animationDelay: `${index * 0.08}s`,
      "@keyframes cardIn": {
        from: { opacity: 0, transform: "translateY(10px)" },
        to: { opacity: 1, transform: "translateY(0)" },
      },
    }}
  >
    <CardContent sx={{ p: 2.75 }}>
      <Stack direction="row" alignItems="center" spacing={2}>
        <Box
          sx={{
            p: 1.5,
            borderRadius: 2,
            bgcolor: `${color}18`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {React.cloneElement(icon, { sx: { color, fontSize: 28 } })}
        </Box>
        <Box>
          <Typography variant="body2" color="text.secondary" fontWeight={700} letterSpacing="0.03em">
            {title}
          </Typography>
          {loading ? (
            <Skeleton width={90} height={38} />
          ) : (
            <Typography variant="h5" fontWeight={800} sx={{ fontFamily: '"Literata", serif' }}>
              {typeof value === "number" ? value.toLocaleString("pt-BR") : value}
            </Typography>
          )}
          {subtitle && !loading && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
      </Stack>
    </CardContent>
  </Card>
);

const UsageReport = () => {
  const theme = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [days, setDays] = useState(30);
  const [sortField, setSortField] = useState("request_count");
  const [sortDirection, setSortDirection] = useState("desc");

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError("");
    const apiUrl = import.meta.env.VITE_API_URL;
    try {
      // Ajuste o caminho da API conforme seu proxy
      const res = await axios.get(`${apiUrl}/api/usage_report?days=${days}`, { withCredentials: true });
      setData(res.data);
    } catch (err) {
      setError(err.response?.status === 403 ? "Acesso negado. Apenas administradores." : "Erro ao carregar dados analíticos.");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleSort = (field) => {
    setSortDirection(sortField === field && sortDirection === "asc" ? "desc" : "asc");
    setSortField(field);
  };

  const activeUsers = useMemo(() => (data?.users || []).filter(u => u.login_count > 0).length, [data]);
  const errorRate = useMemo(() => {
    if (!data?.metrics?.total_requests) return 0;
    return ((data.metrics.total_errors / data.metrics.total_requests) * 100).toFixed(2);
  }, [data]);

  // Chart Data: Health & Traffic (Line Area)
  const activityChart = useMemo(() => {
    if (!data?.daily_stats) return null;
    return {
      labels: data.daily_stats.map(d => new Date(d.date).toLocaleDateString("pt-BR", { day: '2-digit', month: '2-digit' })),
      datasets: [
        {
          label: "Requisições",
          data: data.daily_stats.map(d => d.requests),
          borderColor: theme.palette.primary.main,
          backgroundColor: `${theme.palette.primary.main}20`,
          fill: true,
          tension: 0.4,
        },
        {
          label: "Erros (4xx/5xx)",
          data: data.daily_stats.map(d => d.errors),
          borderColor: theme.palette.error.main,
          backgroundColor: `${theme.palette.error.main}20`,
          fill: true,
          tension: 0.4,
        },
      ],
    };
  }, [data, theme]);

  // Chart Data: Top Searches (Doughnut)
  const searchDoughnut = useMemo(() => {
    if (!data?.top_searches?.length) return null;
    const colors = ["#2196f3", "#4caf50", "#ff9800", "#e91e63", "#9c27b0", "#00bcd4", "#ff5722"];
    return {
      labels: data.top_searches.map(s => s.term),
      datasets: [{
        data: data.top_searches.map(s => s.count),
        backgroundColor: colors,
        borderWidth: 0,
      }],
    };
  }, [data]);

  // Chart Data: Status Codes (Bar)
  const statusCodesChart = useMemo(() => {
    if (!data?.status_codes) return null;
    const getCodeColor = (code) => {
        if(code >= 200 && code < 300) return theme.palette.success.main;
        if(code >= 400 && code < 500) return theme.palette.warning.main;
        return theme.palette.error.main;
    };
    return {
      labels: data.status_codes.map(s => `HTTP ${s.code}`),
      datasets: [{
        label: "Ocorrências",
        data: data.status_codes.map(s => s.count),
        backgroundColor: data.status_codes.map(s => getCodeColor(s.code)),
        borderRadius: 4,
      }]
    };
  }, [data, theme]);

  const sortedUsers = useMemo(() => {
    if (!data?.users) return [];
    return [...data.users].sort((a, b) => {
      const mul = sortDirection === "asc" ? 1 : -1;
      return (typeof a[sortField] === 'string') 
        ? mul * a[sortField].localeCompare(b[sortField])
        : mul * (a[sortField] - b[sortField]);
    });
  }, [data, sortField, sortDirection]);

  return (
    <Box
      sx={{
        position: "relative",
        py: { xs: 3, md: 5 },
        background:
          "radial-gradient(1100px 520px at 10% -10%, rgba(14,116,144,0.18), transparent 60%), radial-gradient(900px 480px at 90% 0%, rgba(15,118,110,0.16), transparent 55%), #f7f6f1",
        "&:before": {
          content: '""',
          position: "absolute",
          inset: 0,
          backgroundImage:
            "repeating-linear-gradient(135deg, rgba(15,23,42,0.05) 0, rgba(15,23,42,0.05) 1px, transparent 1px, transparent 18px)",
          opacity: 0.25,
          pointerEvents: "none",
        },
      }}
    >
      <Container maxWidth="xl" sx={{ position: "relative", zIndex: 1, fontFamily: '"Space Grotesk", sans-serif' }}>
        {/* Header & Controls */}
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", md: "center" }}
          spacing={{ xs: 2.5, md: 3 }}
          sx={{ mb: 4 }}
        >
          <Stack spacing={1.2} sx={{ maxWidth: 620 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip
                label="Painel Executivo"
                size="small"
                sx={{
                  bgcolor: "rgba(15,118,110,0.12)",
                  color: "#0f766e",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                }}
              />
              <Chip
                label={`${days} dias`}
                size="small"
                sx={{
                  bgcolor: "rgba(14,116,144,0.12)",
                  color: "#0e7490",
                  fontWeight: 700,
                }}
              />
            </Stack>
            <Typography
              variant="h3"
              fontWeight={800}
              color="text.primary"
              sx={{ fontFamily: '"Literata", serif', letterSpacing: "-0.02em" }}
            >
              BI & Uso do Sistema
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Métricas de performance, buscas e tráfego do jhub em um painel de leitura rápida.
            </Typography>
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ width: { xs: "100%", md: "auto" } }}>
            <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 200 }, bgcolor: "background.paper" }}>
              <InputLabel>Recorte de Tempo</InputLabel>
              <Select value={days} label="Recorte de Tempo" onChange={(e) => setDays(e.target.value)}>
                <MenuItem value={7}>Últimos 7 dias</MenuItem>
                <MenuItem value={30}>Últimos 30 dias</MenuItem>
                <MenuItem value={90}>Últimos 90 dias</MenuItem>
              </Select>
            </FormControl>
            <Button
              variant="contained"
              onClick={fetchReport}
              disabled={loading}
              startIcon={<PlayArrowIcon />}
              sx={{
                textTransform: "none",
                borderRadius: 2,
                px: 3,
                boxShadow: "0 14px 28px rgba(15,118,110,0.25)",
                background: "linear-gradient(135deg, #0f766e, #0e7490)",
              }}
            >
              Atualizar
            </Button>
          </Stack>
        </Stack>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        {/* KPI Row */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <KPICard
              title="Total de Requisições"
              value={data?.metrics?.total_requests || 0}
              icon={<HttpIcon />}
              color={theme.palette.primary.main}
              loading={loading}
              index={0}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KPICard
              title="Usuários Ativos"
              value={activeUsers}
              subtitle="Com login no período"
              icon={<PeopleIcon />}
              color={theme.palette.success.main}
              loading={loading}
              index={1}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KPICard
              title="Latência Média"
              value={`${data?.metrics?.avg_duration_ms || 0} ms`}
              subtitle="Tempo de resposta API"
              icon={<TimerIcon />}
              color={theme.palette.info.main}
              loading={loading}
              index={2}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KPICard
              title="Taxa de Falha (4xx/5xx)"
              value={`${errorRate}%`}
              subtitle={`${data?.metrics?.total_errors || 0} erros registrados`}
              icon={<WarningIcon />}
              color={theme.palette.error.main}
              loading={loading}
              index={3}
            />
          </Grid>
        </Grid>

        {data && (
          <>
            {/* All Charts Row - responsive grid layout */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
              {/* Volume de Tráfego e Saúde - 8 cols on large, 12 on medium */}
              <Grid item xs={12} lg={8}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    background: "rgba(255,255,255,0.8)",
                    backdropFilter: "blur(8px)",
                    height: { xs: "auto", lg: 420 },
                  }}
                >
                  <Typography variant="h6" fontWeight={700} mb={2}>Volume de Tráfego e Saúde</Typography>
                  {activityChart && (
                    <Box sx={{ height: { xs: 240, md: 320 } }}>
                      <Line data={activityChart} options={{ responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false } }} />
                    </Box>
                  )}
                </Paper>
              </Grid>

              {/* Top Termos Pesquisados - 4 cols on large, 12 on medium, then wraps to row 2 */}
              <Grid item xs={12} sm={6} lg={4}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    background: "rgba(255,255,255,0.85)",
                    backdropFilter: "blur(8px)",
                    height: { xs: "auto", lg: 420 },
                  }}
                >
                  <Stack direction="row" alignItems="center" spacing={1} mb={2}>
                    <SearchIcon color="primary" />
                    <Typography variant="h6" fontWeight={700}>Top Termos Pesquisados</Typography>
                  </Stack>
                  {searchDoughnut ? (
                    <Box sx={{ height: { xs: 240, md: 300 } }}>
                      <Doughnut
                        data={searchDoughnut}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: { legend: { position: "bottom" } },
                        }}
                      />
                    </Box>
                  ) : (
                    <Typography color="text.secondary" textAlign="center" mt={8}>Nenhum termo de busca registrado.</Typography>
                  )}
                </Paper>
              </Grid>

              {/* Distribuição de Status (HTTP) - 4 cols on large, 12 on medium */}
              <Grid item xs={12} sm={6} lg={4}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    background: "rgba(255,255,255,0.85)",
                    backdropFilter: "blur(8px)",
                    height: { xs: "auto", lg: 420 },
                  }}
                >
                  <Typography variant="h6" fontWeight={700} mb={2}>Distribuição de Status (HTTP)</Typography>
                  {statusCodesChart && (
                    <Box sx={{ height: { xs: 220, md: 300 } }}>
                      <Bar data={statusCodesChart} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }} />
                    </Box>
                  )}
                </Paper>
              </Grid>

              {/* Rotas Mais Acessadas - full width, spans below */}
              <Grid item xs={12}>
                <Paper
                  elevation={0}
                  sx={{
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    background: "rgba(255,255,255,0.85)",
                    backdropFilter: "blur(8px)",
                    height: { xs: "auto" },
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <Box sx={{ p: 3, pb: 1 }}>
                    <Typography variant="h6" fontWeight={700}>Rotas Mais Acessadas</Typography>
                  </Box>
                  <TableContainer sx={{ flexGrow: 1, maxHeight: { xs: 320, md: 400 } }}>
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 700 }}>Endpoint</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Requisições</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {data.top_endpoints.map((ep, idx) => (
                          <TableRow key={idx} hover>
                            <TableCell
                              sx={{
                                fontFamily: "monospace",
                                fontSize: "0.82rem",
                                maxWidth: { xs: 200, md: 360 },
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {ep.endpoint}
                            </TableCell>
                            <TableCell align="right">{ep.count.toLocaleString()}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              </Grid>
            </Grid>

            {/* User Data Grid */}
            <Paper
              elevation={0}
              sx={{
                borderRadius: 3,
                border: "1px solid",
                borderColor: "divider",
                background: "rgba(255,255,255,0.88)",
                backdropFilter: "blur(8px)",
                overflow: "hidden",
              }}
            >
              <Box sx={{ p: 3, pb: 1 }}><Typography variant="h6" fontWeight={700}>Comportamento do Usuário</Typography></Box>
              <TableContainer sx={{ maxHeight: { xs: 420, md: 520 } }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>
                        <TableSortLabel active={sortField === "username"} direction={sortDirection} onClick={() => handleSort("username")}>Usuário</TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>
                        <TableSortLabel active={sortField === "email"} direction={sortDirection} onClick={() => handleSort("email")}>Email</TableSortLabel>
                      </TableCell>
                      <TableCell align="right">
                        <TableSortLabel active={sortField === "login_count"} direction={sortDirection} onClick={() => handleSort("login_count")}>Logins</TableSortLabel>
                      </TableCell>
                      <TableCell align="right">
                        <TableSortLabel active={sortField === "request_count"} direction={sortDirection} onClick={() => handleSort("request_count")}>Requisições</TableSortLabel>
                      </TableCell>
                      <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sortedUsers.map((user) => (
                      <TableRow key={user.user_id} hover>
                        <TableCell sx={{ fontWeight: 600 }}>{user.username}</TableCell>
                        <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>{user.email}</TableCell>
                        <TableCell align="right">{user.login_count.toLocaleString("pt-BR")}</TableCell>
                        <TableCell align="right">{user.request_count.toLocaleString("pt-BR")}</TableCell>
                        <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>
                          <Chip label={user.login_count > 0 ? "Ativo" : "Inativo"} color={user.login_count > 0 ? "success" : "default"} size="small" variant="filled" sx={{ borderRadius: 1 }} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </>
        )}
      </Container>
    </Box>
  );
};

export default UsageReport;