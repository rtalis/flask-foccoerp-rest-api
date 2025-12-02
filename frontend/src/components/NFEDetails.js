import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Grid,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import BusinessIcon from "@mui/icons-material/Business";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import PaymentIcon from "@mui/icons-material/Payment";
import InventoryIcon from "@mui/icons-material/Inventory";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";

const NFEDetails = ({ open, onClose, nfeChave, nfeNumero }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nfeData, setNfeData] = useState(null);
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    if (open && nfeChave) {
      fetchNfeDetails();
    }
  }, [open, nfeChave]);

  const fetchNfeDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/get_nfe_data`,
        {
          params: { xmlKey: nfeChave },
          withCredentials: true,
        }
      );
      setNfeData(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Erro ao carregar detalhes da NFE");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return "-";
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(value);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString("pt-BR");
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

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const InfoRow = ({ label, value, copyable = false }) => (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        py: 0.75,
        borderBottom: "1px solid #f0f0f0",
      }}
    >
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ fontWeight: 500 }}
      >
        {label}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
        <Typography variant="body2" sx={{ textAlign: "right" }}>
          {value || "-"}
        </Typography>
        {copyable && value && (
          <Tooltip title="Copiar">
            <IconButton
              size="small"
              onClick={() => copyToClipboard(value)}
              sx={{ p: 0.25 }}
            >
              <ContentCopyIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    </Box>
  );

  const SectionTitle = ({ icon: Icon, title }) => (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5, mt: 2 }}>
      <Icon sx={{ fontSize: 20, color: "primary.main" }} />
      <Typography variant="subtitle2" fontWeight={600}>
        {title}
      </Typography>
    </Box>
  );

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2, maxHeight: "90vh" },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          bgcolor: "#1a1f2e",
          color: "#fff",
          py: 2,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <ReceiptLongIcon />
          <Box>
            <Typography variant="h6" fontWeight={600}>
              NFE {nfeNumero || nfeData?.numero}
            </Typography>
            {nfeData?.chave && (
              <Typography variant="caption" sx={{ opacity: 0.7 }}>
                {nfeData.chave}
              </Typography>
            )}
          </Box>
        </Box>
        <IconButton onClick={onClose} sx={{ color: "#fff" }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        {loading && (
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
        )}

        {error && (
          <Box sx={{ p: 3 }}>
            <Alert severity="error">{error}</Alert>
          </Box>
        )}

        {!loading && !error && nfeData && (
          <>
            {/* Summary Header */}
            <Box
              sx={{
                bgcolor: "#f8f9fa",
                p: 2,
                borderBottom: "1px solid #e0e0e0",
              }}
            >
              <Grid container spacing={2}>
                <Grid item xs={12} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Data Emissão
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {formatDate(nfeData.data_emissao)}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Valor Total
                  </Typography>
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    color="primary.main"
                  >
                    {formatCurrency(nfeData.valor_total)}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Status
                  </Typography>
                  <Chip
                    size="small"
                    label={nfeData.status || "Autorizada"}
                    color="success"
                    variant="outlined"
                  />
                </Grid>
                <Grid item xs={12} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Protocolo
                  </Typography>
                  <Typography variant="body2">
                    {nfeData.protocolo || "-"}
                  </Typography>
                </Grid>
              </Grid>
            </Box>

            {/* Tabs */}
            <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
              <Tabs value={activeTab} onChange={handleTabChange}>
                <Tab
                  icon={<InventoryIcon />}
                  label="Itens"
                  iconPosition="start"
                />
                <Tab
                  icon={<BusinessIcon />}
                  label="Participantes"
                  iconPosition="start"
                />
                <Tab
                  icon={<LocalShippingIcon />}
                  label="Transporte"
                  iconPosition="start"
                />
                <Tab
                  icon={<PaymentIcon />}
                  label="Financeiro"
                  iconPosition="start"
                />
              </Tabs>
            </Box>

            {/* Tab Content */}
            <Box sx={{ p: 2 }}>
              {/* Itens Tab */}
              {activeTab === 0 && (
                <Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mb: 2,
                    }}
                  >
                    <Typography variant="subtitle2" fontWeight={600}>
                      Produtos/Serviços ({nfeData.itens?.length || 0} itens)
                    </Typography>
                    <Box sx={{ display: "flex", gap: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Produtos:{" "}
                        <strong>
                          {formatCurrency(nfeData.valor_produtos)}
                        </strong>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Impostos:{" "}
                        <strong>
                          {formatCurrency(nfeData.valor_impostos)}
                        </strong>
                      </Typography>
                    </Box>
                  </Box>
                  <TableContainer
                    component={Paper}
                    elevation={0}
                    sx={{ border: "1px solid #e0e0e0" }}
                  >
                    <Table size="small">
                      <TableHead>
                        <TableRow sx={{ bgcolor: "#f5f7fa" }}>
                          <TableCell sx={{ width: 50 }}>#</TableCell>
                          <TableCell sx={{ width: 80 }}>Código</TableCell>
                          <TableCell>Descrição</TableCell>
                          <TableCell sx={{ width: 70 }}>NCM</TableCell>
                          <TableCell sx={{ width: 60 }}>CFOP</TableCell>
                          <TableCell align="right" sx={{ width: 70 }}>
                            Qtde
                          </TableCell>
                          <TableCell align="center" sx={{ width: 50 }}>
                            UN
                          </TableCell>
                          <TableCell align="right" sx={{ width: 100 }}>
                            Vlr Unit.
                          </TableCell>
                          <TableCell align="right" sx={{ width: 100 }}>
                            Total
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {nfeData.itens?.map((item, idx) => (
                          <TableRow key={idx} hover>
                            <TableCell>{item.numero_item}</TableCell>
                            <TableCell>
                              <Typography variant="caption">
                                {item.codigo || "-"}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Tooltip title={item.descricao}>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    maxWidth: 300,
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                  }}
                                >
                                  {item.descricao}
                                </Typography>
                              </Tooltip>
                            </TableCell>
                            <TableCell>
                              <Typography variant="caption">
                                {item.ncm || "-"}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography variant="caption">
                                {item.cfop || "-"}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              {item.quantidade?.toLocaleString("pt-BR") || "-"}
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
                </Box>
              )}

              {/* Participantes Tab */}
              {activeTab === 1 && (
                <Grid container spacing={3}>
                  {/* Emitente */}
                  <Grid item xs={12} md={6}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        border: "1px solid #e0e0e0",
                        borderRadius: 2,
                      }}
                    >
                      <SectionTitle
                        icon={BusinessIcon}
                        title="Emitente (Fornecedor)"
                      />
                      <InfoRow
                        label="Razão Social"
                        value={nfeData.emitente?.nome}
                      />
                      <InfoRow
                        label="CNPJ"
                        value={formatCNPJ(nfeData.emitente?.cnpj)}
                        copyable
                      />
                      <InfoRow
                        label="IE"
                        value={nfeData.emitente?.inscricao_estadual}
                      />
                      <Divider sx={{ my: 1.5 }} />
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mb: 1, display: "block" }}
                      >
                        Endereço
                      </Typography>
                      <Typography variant="body2">
                        {nfeData.emitente?.endereco?.logradouro}
                        {nfeData.emitente?.endereco?.numero &&
                          `, ${nfeData.emitente?.endereco?.numero}`}
                        {nfeData.emitente?.endereco?.complemento &&
                          ` - ${nfeData.emitente?.endereco?.complemento}`}
                      </Typography>
                      <Typography variant="body2">
                        {nfeData.emitente?.endereco?.bairro &&
                          `${nfeData.emitente?.endereco?.bairro} - `}
                        {nfeData.emitente?.endereco?.municipio}/
                        {nfeData.emitente?.endereco?.uf}
                      </Typography>
                      <Typography variant="body2">
                        CEP: {nfeData.emitente?.endereco?.cep}
                      </Typography>
                      {nfeData.emitente?.endereco?.telefone && (
                        <Typography variant="body2">
                          Tel: {nfeData.emitente?.endereco?.telefone}
                        </Typography>
                      )}
                    </Paper>
                  </Grid>

                  {/* Destinatário */}
                  <Grid item xs={12} md={6}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        border: "1px solid #e0e0e0",
                        borderRadius: 2,
                      }}
                    >
                      <SectionTitle icon={BusinessIcon} title="Destinatário" />
                      <InfoRow
                        label="Razão Social"
                        value={nfeData.destinatario?.nome}
                      />
                      <InfoRow
                        label="CNPJ/CPF"
                        value={
                          nfeData.destinatario?.cnpj
                            ? formatCNPJ(nfeData.destinatario?.cnpj)
                            : nfeData.destinatario?.cpf
                        }
                        copyable
                      />
                      <InfoRow
                        label="IE"
                        value={nfeData.destinatario?.inscricao_estadual}
                      />
                      <InfoRow
                        label="Email"
                        value={nfeData.destinatario?.email}
                      />
                      <Divider sx={{ my: 1.5 }} />
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mb: 1, display: "block" }}
                      >
                        Endereço
                      </Typography>
                      <Typography variant="body2">
                        {nfeData.destinatario?.endereco?.logradouro}
                        {nfeData.destinatario?.endereco?.numero &&
                          `, ${nfeData.destinatario?.endereco?.numero}`}
                        {nfeData.destinatario?.endereco?.complemento &&
                          ` - ${nfeData.destinatario?.endereco?.complemento}`}
                      </Typography>
                      <Typography variant="body2">
                        {nfeData.destinatario?.endereco?.bairro &&
                          `${nfeData.destinatario?.endereco?.bairro} - `}
                        {nfeData.destinatario?.endereco?.municipio}/
                        {nfeData.destinatario?.endereco?.uf}
                      </Typography>
                      <Typography variant="body2">
                        CEP: {nfeData.destinatario?.endereco?.cep}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              )}

              {/* Transporte Tab */}
              {activeTab === 2 && (
                <Box>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          border: "1px solid #e0e0e0",
                          borderRadius: 2,
                        }}
                      >
                        <SectionTitle
                          icon={LocalShippingIcon}
                          title="Transportadora"
                        />
                        <InfoRow
                          label="Modalidade"
                          value={
                            {
                              0: "Por conta do Emitente",
                              1: "Por conta do Destinatário",
                              2: "Por conta de Terceiros",
                              9: "Sem Frete",
                            }[nfeData.transporte?.modalidade] ||
                            nfeData.transporte?.modalidade
                          }
                        />
                        <InfoRow
                          label="Nome"
                          value={nfeData.transporte?.transportadora?.nome}
                        />
                        <InfoRow
                          label="CNPJ"
                          value={formatCNPJ(
                            nfeData.transporte?.transportadora?.cnpj
                          )}
                        />
                        <InfoRow
                          label="IE"
                          value={
                            nfeData.transporte?.transportadora
                              ?.inscricao_estadual
                          }
                        />
                        <InfoRow
                          label="Placa"
                          value={nfeData.transporte?.transportadora?.placa}
                        />
                        <InfoRow
                          label="Endereço"
                          value={`${
                            nfeData.transporte?.transportadora?.endereco || ""
                          } - ${
                            nfeData.transporte?.transportadora?.municipio || ""
                          }/${nfeData.transporte?.transportadora?.uf || ""}`}
                        />
                      </Paper>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          border: "1px solid #e0e0e0",
                          borderRadius: 2,
                        }}
                      >
                        <SectionTitle icon={InventoryIcon} title="Volumes" />
                        {nfeData.transporte?.volumes?.length > 0 ? (
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Qtde</TableCell>
                                <TableCell>Espécie</TableCell>
                                <TableCell align="right">Peso Bruto</TableCell>
                                <TableCell align="right">
                                  Peso Líquido
                                </TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {nfeData.transporte.volumes.map((vol, idx) => (
                                <TableRow key={idx}>
                                  <TableCell>{vol.quantidade || "-"}</TableCell>
                                  <TableCell>{vol.especie || "-"}</TableCell>
                                  <TableCell align="right">
                                    {vol.peso_bruto
                                      ? `${vol.peso_bruto} kg`
                                      : "-"}
                                  </TableCell>
                                  <TableCell align="right">
                                    {vol.peso_liquido
                                      ? `${vol.peso_liquido} kg`
                                      : "-"}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Sem informações de volumes
                          </Typography>
                        )}
                      </Paper>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {/* Financeiro Tab */}
              {activeTab === 3 && (
                <Box>
                  <Grid container spacing={3}>
                    {/* Valores */}
                    <Grid item xs={12} md={6}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          border: "1px solid #e0e0e0",
                          borderRadius: 2,
                        }}
                      >
                        <SectionTitle
                          icon={PaymentIcon}
                          title="Valores da Nota"
                        />
                        <InfoRow
                          label="Valor dos Produtos"
                          value={formatCurrency(nfeData.valor_produtos)}
                        />
                        <InfoRow
                          label="Valor do Frete"
                          value={formatCurrency(
                            nfeData.transporte?.valor_frete
                          )}
                        />
                        <InfoRow
                          label="Valor do Seguro"
                          value={formatCurrency(nfeData.valor_seguro)}
                        />
                        <InfoRow
                          label="Desconto"
                          value={formatCurrency(nfeData.valor_desconto)}
                        />
                        <InfoRow
                          label="Outras Despesas"
                          value={formatCurrency(nfeData.valor_outros)}
                        />
                        <Divider sx={{ my: 1 }} />
                        <InfoRow
                          label="Total de Impostos"
                          value={formatCurrency(nfeData.valor_impostos)}
                        />
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            py: 1,
                            bgcolor: "#e3f2fd",
                            px: 1,
                            borderRadius: 1,
                            mt: 1,
                          }}
                        >
                          <Typography variant="body2" fontWeight={600}>
                            TOTAL DA NOTA
                          </Typography>
                          <Typography
                            variant="body2"
                            fontWeight={600}
                            color="primary.main"
                          >
                            {formatCurrency(nfeData.valor_total)}
                          </Typography>
                        </Box>
                      </Paper>
                    </Grid>

                    {/* Duplicatas */}
                    <Grid item xs={12} md={6}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          border: "1px solid #e0e0e0",
                          borderRadius: 2,
                        }}
                      >
                        <SectionTitle
                          icon={PaymentIcon}
                          title="Duplicatas / Parcelas"
                        />
                        {nfeData.duplicatas?.length > 0 ? (
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Nº</TableCell>
                                <TableCell>Vencimento</TableCell>
                                <TableCell align="right">Valor</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {nfeData.duplicatas.map((dup, idx) => (
                                <TableRow key={idx}>
                                  <TableCell>{dup.numero || idx + 1}</TableCell>
                                  <TableCell>
                                    {formatDate(dup.vencimento)}
                                  </TableCell>
                                  <TableCell align="right">
                                    {formatCurrency(dup.valor)}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Sem duplicatas registradas
                          </Typography>
                        )}
                      </Paper>
                    </Grid>
                  </Grid>

                  {/* Informações Adicionais */}
                  {nfeData.informacoes_adicionais && (
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        border: "1px solid #e0e0e0",
                        borderRadius: 2,
                        mt: 2,
                      }}
                    >
                      <Typography
                        variant="subtitle2"
                        fontWeight={600}
                        sx={{ mb: 1 }}
                      >
                        Informações Adicionais
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ whiteSpace: "pre-wrap" }}
                      >
                        {nfeData.informacoes_adicionais}
                      </Typography>
                    </Paper>
                  )}
                </Box>
              )}
            </Box>
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2, borderTop: "1px solid #e0e0e0" }}>
        <Button onClick={onClose} variant="outlined">
          Fechar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default NFEDetails;
