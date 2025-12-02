import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  CircularProgress,
  Tooltip,
  Button,
  Grid,
  Divider,
  Alert,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import BusinessIcon from "@mui/icons-material/Business";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import InventoryIcon from "@mui/icons-material/Inventory";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import LinkIcon from "@mui/icons-material/Link";

const NFEDetails = ({ open, onClose, nfe, linkedPurchases = [] }) => {
  const [loading, setLoading] = useState(false);
  const [nfeDetails, setNfeDetails] = useState(null);
  const [error, setError] = useState(null);
  const [loadingDanfe, setLoadingDanfe] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open && nfe) {
      loadNfeDetails();
    }
  }, [open, nfe]);

  const loadNfeDetails = async () => {
    if (!nfe?.id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/nfe_details/${nfe.id}`,
        { withCredentials: true }
      );
      setNfeDetails(response.data);
    } catch (err) {
      console.error("Error loading NFE details:", err);
      setError("Erro ao carregar detalhes da NFE");
      // Use basic info from nfe prop if API fails
      setNfeDetails(null);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDanfe = async () => {
    if (!nfe?.chave) {
      setError("Chave de acesso não disponível");
      return;
    }

    setLoadingDanfe(true);

    try {
      const newWindow = window.open("", "_blank");
      if (!newWindow) {
        alert("Pop-up bloqueado pelo navegador.");
        setLoadingDanfe(false);
        return;
      }
      newWindow.document.write(
        "<html><head><title>Carregando DANFE...</title></head>" +
          "<body style='font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;'>" +
          "<div>Carregando DANFE...</div></body></html>"
      );

      const pdfResponse = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/get_danfe_pdf`,
        {
          params: { xmlKey: nfe.chave },
          withCredentials: true,
        }
      );

      let pdfBase64 = pdfResponse.data;
      if (typeof pdfResponse.data === "object") {
        pdfBase64 =
          pdfResponse.data.arquivo ||
          pdfResponse.data.pdf ||
          pdfResponse.data.content;
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

      newWindow.location.href = blobUrl;
    } catch (err) {
      console.error("Error loading DANFE:", err);
      setError("Erro ao carregar DANFE");
    } finally {
      setLoadingDanfe(false);
    }
  };

  const handleCopyChave = () => {
    if (nfe?.chave) {
      navigator.clipboard.writeText(nfe.chave);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString("pt-BR");
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleString("pt-BR");
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return "-";
    // Handle object values with parsedValue
    if (typeof value === "object" && value.parsedValue !== undefined) {
      value = value.parsedValue;
    }
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(value);
  };

  const formatCNPJ = (cnpj) => {
    if (!cnpj) return "-";
    const cleaned = cnpj.replace(/\D/g, "");
    if (cleaned.length !== 14) return cnpj;
    return cleaned.replace(
      /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
      "$1.$2.$3/$4-$5"
    );
  };

  const formatNumber = (value, decimals = 2) => {
    if (value === null || value === undefined) return "-";
    return new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  };

  // Use nfeDetails if available, otherwise fall back to nfe prop
  const displayData = nfeDetails || nfe;
  const items = nfeDetails?.items || [];

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 3, maxHeight: "90vh" },
      }}
    >
      <DialogTitle
        sx={{
          background: "linear-gradient(135deg, #1a1f2e 0%, #2d3548 100%)",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          py: 2,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <ReceiptLongIcon />
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              NF-e {displayData?.numero}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              Detalhes da Nota Fiscal Eletrônica
            </Typography>
          </Box>
        </Box>
        <IconButton onClick={onClose} sx={{ color: "#fff" }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        {error && (
          <Alert severity="error" sx={{ m: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: 300,
            }}
          >
            <CircularProgress />
          </Box>
        ) : (
          <Box>
            {/* NFE Header Info */}
            <Box sx={{ p: 3, bgcolor: "#f8f9fa" }}>
              <Grid container spacing={3}>
                {/* Supplier Info */}
                <Grid item xs={12} md={6}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 2,
                      height: "100%",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        mb: 2,
                      }}
                    >
                      <BusinessIcon color="primary" />
                      <Typography variant="subtitle1" fontWeight={600}>
                        Fornecedor
                      </Typography>
                    </Box>
                    <Typography variant="body1" fontWeight={500} gutterBottom>
                      {displayData?.fornecedor || "-"}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      CNPJ: {formatCNPJ(displayData?.cnpj)}
                    </Typography>
                    {nfeDetails?.emitente && (
                      <>
                        {nfeDetails.emitente.endereco && (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ mt: 1 }}
                          >
                            {nfeDetails.emitente.endereco}
                            {nfeDetails.emitente.cidade &&
                              ` - ${nfeDetails.emitente.cidade}`}
                            {nfeDetails.emitente.uf &&
                              `/${nfeDetails.emitente.uf}`}
                          </Typography>
                        )}
                      </>
                    )}
                  </Paper>
                </Grid>

                {/* NFE Info */}
                <Grid item xs={12} md={6}>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 2,
                      height: "100%",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        mb: 2,
                      }}
                    >
                      <CalendarTodayIcon color="primary" />
                      <Typography variant="subtitle1" fontWeight={600}>
                        Informações da NFE
                      </Typography>
                    </Box>
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Data de Emissão
                        </Typography>
                        <Typography variant="body2" fontWeight={500}>
                          {formatDateTime(displayData?.data_emissao)}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Valor Total
                        </Typography>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          color="primary"
                        >
                          {formatCurrency(displayData?.valor_total)}
                        </Typography>
                      </Grid>
                      <Grid item xs={12}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Chave de Acesso
                        </Typography>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                          }}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              fontFamily: "monospace",
                              fontSize: "0.75rem",
                              wordBreak: "break-all",
                            }}
                          >
                            {displayData?.chave || "-"}
                          </Typography>
                          {displayData?.chave && (
                            <Tooltip title={copied ? "Copiado!" : "Copiar"}>
                              <IconButton
                                size="small"
                                onClick={handleCopyChave}
                              >
                                <ContentCopyIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      </Grid>
                    </Grid>
                  </Paper>
                </Grid>
              </Grid>
            </Box>

            <Divider />

            {/* Items Table */}
            <Box sx={{ p: 3 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mb: 2,
                }}
              >
                <InventoryIcon color="primary" />
                <Typography variant="subtitle1" fontWeight={600}>
                  Itens da Nota Fiscal ({items.length})
                </Typography>
              </Box>

              {items.length > 0 ? (
                <TableContainer
                  component={Paper}
                  elevation={0}
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                    maxHeight: 300,
                  }}
                >
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}>
                          #
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}>
                          Código
                        </TableCell>
                        <TableCell
                          sx={{
                            fontWeight: 600,
                            bgcolor: "#f5f7fa",
                            minWidth: 250,
                          }}
                        >
                          Descrição
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}
                        >
                          Qtd
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}
                        >
                          Unid
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}
                        >
                          Valor Unit.
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}
                        >
                          Valor Total
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {items.map((item, index) => (
                        <TableRow key={item.id || index} hover>
                          <TableCell>{item.numero_item || index + 1}</TableCell>
                          <TableCell>
                            <Typography variant="body2" fontFamily="monospace">
                              {item.codigo || "-"}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Tooltip title={item.descricao || "-"}>
                              <Typography
                                variant="body2"
                                sx={{
                                  maxWidth: 300,
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {item.descricao || "-"}
                              </Typography>
                            </Tooltip>
                          </TableCell>
                          <TableCell align="right">
                            {formatNumber(item.quantidade, 4)}
                          </TableCell>
                          <TableCell align="center">
                            {item.unidade || "-"}
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(item.valor_unitario)}
                          </TableCell>
                          <TableCell align="right">
                            <Typography fontWeight={500}>
                              {formatCurrency(item.valor_total)}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    textAlign: "center",
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                    bgcolor: "#fafafa",
                  }}
                >
                  <InventoryIcon
                    sx={{ fontSize: 48, color: "text.disabled", mb: 1 }}
                  />
                  <Typography color="text.secondary">
                    Itens não disponíveis
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Os itens da nota fiscal não foram carregados
                  </Typography>
                </Paper>
              )}
            </Box>

            <Divider />

            {/* Linked Purchase Orders */}
            <Box sx={{ p: 3 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mb: 2,
                }}
              >
                <LinkIcon color="primary" />
                <Typography variant="subtitle1" fontWeight={600}>
                  Pedidos de Compra Vinculados ({linkedPurchases.length})
                </Typography>
              </Box>

              {linkedPurchases.length > 0 ? (
                <TableContainer
                  component={Paper}
                  elevation={0}
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                    maxHeight: 250,
                  }}
                >
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}>
                          Pedido
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}>
                          Data
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}>
                          Fornecedor
                        </TableCell>
                        <TableCell
                          sx={{
                            fontWeight: 600,
                            bgcolor: "#f5f7fa",
                            minWidth: 200,
                          }}
                        >
                          Item
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}
                        >
                          Valor
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={{ fontWeight: 600, bgcolor: "#f5f7fa" }}
                        >
                          Tipo
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {linkedPurchases.map((po, idx) => (
                        <TableRow key={`${po.cod_pedc}-${idx}`} hover>
                          <TableCell>
                            <Typography fontWeight={500}>
                              {po.cod_pedc}
                            </Typography>
                          </TableCell>
                          <TableCell>{formatDate(po.dt_emis)}</TableCell>
                          <TableCell>
                            <Tooltip title={po.fornecedor || "-"}>
                              <Typography
                                variant="body2"
                                sx={{
                                  maxWidth: 150,
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {po.fornecedor || "-"}
                              </Typography>
                            </Tooltip>
                          </TableCell>
                          <TableCell>
                            <Tooltip title={po.item_descricao || "-"}>
                              <Typography
                                variant="body2"
                                sx={{
                                  maxWidth: 200,
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {po.item_descricao || "-"}
                              </Typography>
                            </Tooltip>
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(po.valor)}
                          </TableCell>
                          <TableCell align="center">
                            {po.match_type === "estimated" ? (
                              <Chip
                                size="small"
                                icon={<AutoAwesomeIcon />}
                                label={`${po.match_score?.toFixed(0) || 0}%`}
                                color="secondary"
                                variant="outlined"
                              />
                            ) : (
                              <Chip
                                size="small"
                                label="Vinculado"
                                color="success"
                                variant="outlined"
                              />
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    textAlign: "center",
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                    bgcolor: "#fafafa",
                  }}
                >
                  <LocalShippingIcon
                    sx={{ fontSize: 48, color: "text.disabled", mb: 1 }}
                  />
                  <Typography color="text.secondary">
                    Nenhum pedido de compra vinculado
                  </Typography>
                </Paper>
              )}
            </Box>
          </Box>
        )}
      </DialogContent>

      <DialogActions
        sx={{ p: 2, borderTop: "1px solid", borderColor: "divider" }}
      >
        <Button onClick={onClose} color="inherit">
          Fechar
        </Button>
        <Button
          variant="contained"
          startIcon={
            loadingDanfe ? <CircularProgress size={18} /> : <PictureAsPdfIcon />
          }
          onClick={handleViewDanfe}
          disabled={loadingDanfe || !nfe?.chave}
          sx={{
            bgcolor: "#1a1f2e",
            "&:hover": { bgcolor: "#2d3548" },
          }}
        >
          Visualizar DANFE
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default NFEDetails;
