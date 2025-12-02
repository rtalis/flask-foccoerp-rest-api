import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import ItemScreen from "./ItemScreen";
import "./UnifiedSearch.css";

import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableFooter,
  Paper,
  Collapse,
  Box,
  Typography,
  IconButton,
  TextField,
  Button,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  Checkbox,
  Select,
  MenuItem,
  InputAdornment,
  Divider,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Card,
  CardContent,
  CardActions,
  Switch,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Skeleton,
  Tooltip,
} from "@mui/material";
import Autocomplete from "@mui/material/Autocomplete";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import SearchIcon from "@mui/icons-material/Search";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ReceiptIcon from "@mui/icons-material/Receipt";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import TuneIcon from "@mui/icons-material/Tune";
import RefreshIcon from "@mui/icons-material/Refresh";
import ScheduleIcon from "@mui/icons-material/Schedule";

function PurchaseRow(props) {
  const {
    purchase,
    formatDate,
    formatNumber,
    formatCurrency,
    getFirstWords,
    handleItemClick,
    hideFulfilledItems = false,
  } = props;
  const [open, setOpen] = useState(true); // Expanded by default
  const [nfeData, setNfeData] = useState(null);
  const [loadingNfe, setLoadingNfe] = useState(false);
  const [showNfeDialog, setShowNfeDialog] = useState(false);
  const [showNfNotFoundDialog, setShowNfNotFoundDialog] = useState(false);
  const [nfNotFoundInfo, setNfNotFoundInfo] = useState(null);
  const [loadingDanfeNf, setLoadingDanfeNf] = useState(null); // Track which NF is loading

  const normalizeNumber = (value) => {
    if (value === null || value === undefined) {
      return undefined;
    }
    if (typeof value === "object") {
      if (value === null) {
        return undefined;
      }
      if (value.parsedValue !== undefined && value.parsedValue !== null) {
        const parsed = Number(value.parsedValue);
        if (!Number.isNaN(parsed)) {
          return parsed;
        }
      }
      if (value.source !== undefined && value.source !== null) {
        const parsed = Number(value.source);
        if (!Number.isNaN(parsed)) {
          return parsed;
        }
      }
      if (value.value !== undefined && value.value !== null) {
        const parsed = Number(value.value);
        if (!Number.isNaN(parsed)) {
          return parsed;
        }
      }
      return undefined;
    }
    const numeric = Number(value);
    return Number.isNaN(numeric) ? undefined : numeric;
  };

  useEffect(() => {
    setOpen(!hideFulfilledItems);
  }, [hideFulfilledItems]);

  const fetchNfeData = async () => {
    setLoadingNfe(true);
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/nfe_by_purchase`,
        {
          params: { cod_pedc: purchase.order.cod_pedc },
          withCredentials: true,
        }
      );
      setNfeData(response.data);
      setShowNfeDialog(true);
    } catch (error) {
      console.error("Error fetching NFE data:", error);
    } finally {
      setLoadingNfe(false);
    }
  };

  /** Inicial implementationm, TODO a more robust version  */

  const handleNfeClick = async (nfe) => {
    try {
      const newWindow = window.open("", "_blank");
      if (!newWindow) {
        alert(
          "Pop-up bloqueado pelo navegador. Por favor, permita pop-ups para este site."
        );
        return;
      }
      newWindow.document.write(`
      <html>
        <head>
          <title>Visualizando DANFE</title>
          <style>
            body { 
              font-family: Arial, sans-serif; 
              display: flex;
              justify-content: center;
              align-items: center;
              height: 100vh;
              margin: 0;
              flex-direction: column;
            }
            .loading { margin-bottom: 20px; }
          </style>
        </head>
        <body>
          <div class="loading">Carregando DANFE...</div>
                          <div className="spinner"></div>

        </body>
      </html>
    `);
      newWindow.document.close();

      // First ensure the NFE data is stored in the database
      await axios.get(`${process.env.REACT_APP_API_URL}/api/get_nfe_data`, {
        params: { xmlKey: nfe.chave },
        withCredentials: true,
      });

      // Then get the PDF
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/get_danfe_pdf`,
        {
          params: { xmlKey: nfe.chave },
          withCredentials: true,
        }
      );

      if (!response.data) {
        newWindow.document.body.innerHTML =
          '<div style="color:red;">Erro ao carregar o PDF. Dados inválidos recebidos.</div>';
        return;
      }
      let pdfBase64;
      if (typeof response.data === "string") {
        pdfBase64 = response.data;
      } else if (response.data.arquivo) {
        pdfBase64 = response.data.arquivo;
      } else if (response.data.pdf) {
        pdfBase64 = response.data.pdf;
      } else if (response.data.content) {
        pdfBase64 = response.data.content;
      } else {
        const possibleBase64 = Object.entries(response.data)
          .filter(
            ([key, value]) => typeof value === "string" && value.length > 100
          )
          .sort((a, b) => b[1].length - a[1].length)[0];

        if (possibleBase64) {
          pdfBase64 = possibleBase64[1];
        } else {
          newWindow.document.body.innerHTML =
            '<div style="color:red;">Erro ao carregar o PDF. Formato de resposta não reconhecido.</div>';
          return;
        }
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

      newWindow.document.write(`
      <html>
        <head>
          <title>DANFE - ${nfe.numero || nfe.chave}</title>
          <style>
            body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; }
            #pdf-viewer { width: 100%; height: 100%; }
          </style>
        </head>
        <body>
          <embed id="pdf-viewer" src="${blobUrl}" type="application/pdf" width="100%" height="100%">
        </body>
      </html>
    `);
      newWindow.document.close();
    } catch (error) {
      console.error("Error fetching DANFE PDF:", error);
    }
  };

  const handleDialogClose = () => {
    setShowNfeDialog(false);
  };

  // Handle clicking on the DANFE icon next to an NFE number
  const handleDanfeIconClick = async (nfEntry) => {
    setLoadingDanfeNf(nfEntry.num_nf); // Set loading for this specific NF
    try {
      // First, try to find the NFE in the database by its number
      // Pass supplier info and entry date for accurate matching when multiple NFEs exist
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/get_nfe_by_number`,
        {
          params: {
            num_nf: nfEntry.num_nf,
            fornecedor_id: purchase.order.fornecedor_id,
            fornecedor_nome: purchase.order.fornecedor_descricao,
            dt_ent: nfEntry.dt_ent,
          },
          withCredentials: true,
        }
      );

      if (response.data && response.data.found && response.data.chave) {
        // NFE found in database, open DANFE directly
        setLoadingDanfeNf(null); // Clear loading before opening new window
        handleNfeClick({
          chave: response.data.chave,
          numero: response.data.numero || nfEntry.num_nf,
        });
      } else {
        // NFE not found, try to sync from SIEG first
        await syncAndRetryDanfe(nfEntry);
      }
    } catch (error) {
      // If error (likely 404), try to sync from SIEG and retry
      console.log("NFE not found in database, syncing from SIEG...");
      await syncAndRetryDanfe(nfEntry);
    } finally {
      setLoadingDanfeNf(null); // Always clear loading state
    }
  };

  // Sync NFEs from SIEG and retry finding the DANFE
  const syncAndRetryDanfe = async (nfEntry) => {
    try {
      // Call nfe_by_purchase to sync NFEs from SIEG to database
      await axios.get(`${process.env.REACT_APP_API_URL}/api/nfe_by_purchase`, {
        params: { cod_pedc: purchase.order.cod_pedc },
        withCredentials: true,
      });

      // Now retry finding the NFE in the database
      const retryResponse = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/get_nfe_by_number`,
        {
          params: {
            num_nf: nfEntry.num_nf,
            fornecedor_id: purchase.order.fornecedor_id,
            fornecedor_nome: purchase.order.fornecedor_descricao,
            dt_ent: nfEntry.dt_ent,
          },
          withCredentials: true,
        }
      );

      if (
        retryResponse.data &&
        retryResponse.data.found &&
        retryResponse.data.chave
      ) {
        // NFE found after sync, open DANFE
        handleNfeClick({
          chave: retryResponse.data.chave,
          numero: retryResponse.data.numero || nfEntry.num_nf,
        });
      } else {
        setNfNotFoundInfo({
          num_nf: nfEntry.num_nf,
          fornecedor: purchase.order.fornecedor_descricao,
          cod_pedc: purchase.order.cod_pedc,
        });
        setShowNfNotFoundDialog(true);
      }
    } catch (syncError) {
      console.error("Error syncing NFEs:", syncError);
      setNfNotFoundInfo({
        num_nf: nfEntry.num_nf,
        fornecedor: purchase.order.fornecedor_descricao,
        cod_pedc: purchase.order.cod_pedc,
      });
      setShowNfNotFoundDialog(true);
    }
  };

  return (
    <React.Fragment>
      {/* Purchase header row */}
      <TableRow
        sx={{
          "& > *": { borderBottom: "unset" },
          backgroundColor: purchase.order.is_fulfilled
            ? "#1e2631ff"
            : "#165da5ff",
          "&:hover": {
            backgroundColor: purchase.order.is_fulfilled
              ? "#273241ff"
              : "#1b69b8ff",
          },
        }}
      >
        <TableCell style={{ padding: 0 }}>
          <IconButton
            size="small"
            onClick={() => setOpen(!open)}
            disabled={hideFulfilledItems}
            sx={{ color: "#fff" }}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell
          colSpan={9}
          align="center"
          sx={{ fontWeight: "bold", fontSize: "1.05rem", color: "#ffffffe3" }}
        >
          Pedido de Compra: {purchase.order.cod_pedc}~{" "}
          {purchase.order.fornecedor_id}{" "}
          {getFirstWords(purchase.order.fornecedor_descricao, 4)} -{" "}
          {formatCurrency(purchase.order.adjusted_total)} ~ Comprador:{" "}
          {purchase.order.func_nome}. Empresa: {purchase.order.cod_emp1}
          {purchase.order.is_fulfilled && (
            <span style={{ marginLeft: "8px", color: "#4caf50" }}>
              ✓ Atendido
            </span>
          )}
        </TableCell>
      </TableRow>

      {/* Collapsible items section */}
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={11}>
          <Collapse
            in={!hideFulfilledItems && open}
            timeout="auto"
            unmountOnExit
          >
            <Box sx={{ margin: 1 }}>
              <Table size="small" aria-label="items">
                <TableHead>
                  <TableRow sx={{ backgroundColor: "#f5f7fa" }}>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Data Emissão
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Cod. item
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Descrição do item
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Quantidade
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Preço Unitário
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      IPI
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Total
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Qtde Atendida
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      Dt Entrada
                    </TableCell>
                    <TableCell
                      align="center"
                      sx={{ fontWeight: 600, color: "#1a1f2e" }}
                    >
                      NFEs
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {purchase.items.map((item) => {
                    const qty = normalizeNumber(item?.quantidade);
                    const attended = normalizeNumber(item?.qtde_atendida);
                    const canceled = normalizeNumber(item?.qtde_canc);
                    const unitPrice = normalizeNumber(item?.preco_unitario);
                    const total = normalizeNumber(item?.total);
                    const percIpi = normalizeNumber(item?.perc_ipi);
                    const isFullyFulfilled =
                      qty !== undefined &&
                      attended !== undefined &&
                      qty === attended;
                    const isOverfulfilled =
                      qty !== undefined &&
                      attended !== undefined &&
                      attended > qty;
                    const isPartiallyFulfilled =
                      qty !== undefined &&
                      attended !== undefined &&
                      attended > 0 &&
                      attended < qty;
                    const isFullyCanceled =
                      qty !== undefined &&
                      canceled !== undefined &&
                      canceled >= qty &&
                      qty > 0;
                    return (
                      <TableRow
                        key={item.id}
                        sx={{
                          backgroundColor: isOverfulfilled
                            ? "#fff8e1"
                            : isFullyFulfilled
                            ? "#e3f2fd"
                            : isPartiallyFulfilled
                            ? "#fce4ec"
                            : "inherit",
                          "&:hover": {
                            backgroundColor: isOverfulfilled
                              ? "#ffecb3"
                              : isFullyFulfilled
                              ? "#bbdefb"
                              : isPartiallyFulfilled
                              ? "#f8bbd0"
                              : "#f5f7fa",
                          },
                        }}
                      >
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          {formatDate(purchase.order.dt_emis)}
                        </TableCell>
                        <TableCell
                          align="center"
                          onClick={() => handleItemClick(item.id)}
                          sx={{
                            cursor: "pointer",
                            "&:hover": { textDecoration: "underline" },
                            ...(isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}),
                          }}
                        >
                          {item.item_id}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          {item.descricao}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          {formatNumber(qty)} {item.unidade_medida}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          R$ {formatNumber(unitPrice)}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          {percIpi !== undefined
                            ? `${formatNumber(percIpi)}%`
                            : "0%"}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          R$ {formatNumber(total)}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          {formatNumber(attended)} {item.unidade_medida}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          {purchase.order.nfes.map((nf) => (
                            <div key={nf.id}>
                              {nf.linha == item.linha && (
                                <>
                                  {nf.dt_ent ? formatDate(nf.dt_ent) : ""}
                                  {nf.qtde
                                    ? ` (${formatNumber(
                                        normalizeNumber(nf?.qtde)
                                      )} ${item.unidade_medida})`
                                    : ""}
                                </>
                              )}
                            </div>
                          ))}
                        </TableCell>
                        <TableCell
                          align="center"
                          sx={
                            isFullyCanceled
                              ? {
                                  textDecoration: "line-through",
                                  color: "#9e9e9e",
                                }
                              : {}
                          }
                        >
                          {(() => {
                            const actualNfes = purchase.order.nfes.filter(
                              (nf) => nf.linha == item.linha && nf.num_nf
                            );
                            if (actualNfes.length > 0) {
                              return (
                                <div
                                  style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    alignItems: "center",
                                    gap: "4px",
                                  }}
                                >
                                  {actualNfes.map((nf) => (
                                    <div
                                      key={nf.id}
                                      style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "4px",
                                      }}
                                    >
                                      <span>{nf.num_nf}</span>
                                      <Tooltip
                                        title={
                                          loadingDanfeNf === nf.num_nf
                                            ? "Carregando..."
                                            : "Visualizar DANFE"
                                        }
                                      >
                                        <span>
                                          <IconButton
                                            size="small"
                                            color="primary"
                                            onClick={() =>
                                              handleDanfeIconClick(nf)
                                            }
                                            disabled={
                                              loadingDanfeNf === nf.num_nf
                                            }
                                            sx={{ padding: "2px" }}
                                          >
                                            {loadingDanfeNf === nf.num_nf ? (
                                              <CircularProgress size={16} />
                                            ) : (
                                              <PictureAsPdfIcon
                                                fontSize="small"
                                                sx={{ fontSize: "16px" }}
                                              />
                                            )}
                                          </IconButton>
                                        </span>
                                      </Tooltip>
                                    </div>
                                  ))}
                                </div>
                              );
                            } else if (item.estimated_nfe) {
                              // Split multiple NFE numbers by " + "
                              const nfeNumbers = item.estimated_nfe.nfe_numero
                                ? item.estimated_nfe.nfe_numero.split(" + ")
                                : [];
                              return (
                                <div
                                  style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    alignItems: "center",
                                    gap: "4px",
                                  }}
                                >
                                  {nfeNumbers.map((nfeNum, idx) => (
                                    <div
                                      key={idx}
                                      style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "4px",
                                      }}
                                    >
                                      <Tooltip
                                        title={`NF estimada por IA (${item.estimated_nfe.match_score?.toFixed(
                                          0
                                        )}% match)${
                                          item.estimated_nfe.nfe_fornecedor
                                            ? ` - ${item.estimated_nfe.nfe_fornecedor}`
                                            : ""
                                        }`}
                                      >
                                        <span
                                          style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "4px",
                                            color: "#9c27b0",
                                            fontStyle: "italic",
                                          }}
                                        >
                                          <span>✨</span>
                                          <span>{nfeNum.trim()}</span>
                                        </span>
                                      </Tooltip>
                                      <Tooltip
                                        title={
                                          loadingDanfeNf === nfeNum.trim()
                                            ? "Carregando..."
                                            : "Visualizar DANFE"
                                        }
                                      >
                                        <span>
                                          <IconButton
                                            size="small"
                                            color="primary"
                                            onClick={() =>
                                              handleDanfeIconClick({
                                                num_nf: nfeNum.trim(),
                                              })
                                            }
                                            disabled={
                                              loadingDanfeNf === nfeNum.trim()
                                            }
                                            sx={{ padding: "2px" }}
                                          >
                                            {loadingDanfeNf ===
                                            nfeNum.trim() ? (
                                              <CircularProgress size={16} />
                                            ) : (
                                              <PictureAsPdfIcon
                                                fontSize="small"
                                                sx={{ fontSize: "16px" }}
                                              />
                                            )}
                                          </IconButton>
                                        </span>
                                      </Tooltip>
                                    </div>
                                  ))}
                                </div>
                              );
                            }
                            // Show search button when no actual NFE and no estimation
                            return (
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "4px",
                                }}
                              >
                                <IconButton
                                  size="small"
                                  color="primary"
                                  onClick={fetchNfeData}
                                  disabled={loadingNfe}
                                  title="Buscar notas fiscais"
                                >
                                  {loadingNfe ? (
                                    <CircularProgress size={16} />
                                  ) : (
                                    <SearchIcon fontSize="small" />
                                  )}
                                </IconButton>
                                {nfeData &&
                                  nfeData.nfe_data &&
                                  nfeData.nfe_data.length > 0 && (
                                    <IconButton
                                      size="small"
                                      color="secondary"
                                      onClick={() => setShowNfeDialog(true)}
                                      title="Ver Notas Fiscais"
                                    >
                                      <ReceiptIcon fontSize="small" />
                                    </IconButton>
                                  )}
                              </div>
                            );
                          })()}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
                {/* Footer */}
                <TableFooter>
                  <TableRow sx={{ backgroundColor: "#f5f7fa" }}>
                    <TableCell colSpan={10}>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          width: "100%",
                        }}
                      >
                        <Typography
                          variant="body2"
                          component="div"
                          sx={{
                            fontWeight: "bold",
                            textAlign: "left",
                            color: "#1a1f2e",
                          }}
                        >
                          Observação: {purchase.order.observacao}
                        </Typography>
                        <Typography
                          variant="body2"
                          component="div"
                          sx={{
                            fontWeight: "bold",
                            textAlign: "right",
                            color: "#1a1f2e",
                          }}
                        >
                          Total c/ ipi:{" "}
                          {formatCurrency(purchase.order.total_pedido_com_ipi)}{" "}
                          Total c/ desconto:{" "}
                          {formatCurrency(purchase.order.adjusted_total)}
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                </TableFooter>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>

      {/* NFE Dialog */}
      <Dialog
        open={showNfeDialog}
        onClose={handleDialogClose}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Notas Fiscais - Pedido {purchase.order.cod_pedc}
        </DialogTitle>
        <DialogContent>
          {loadingNfe ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
              <CircularProgress />
            </Box>
          ) : nfeData && nfeData.nfe_data ? (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {nfeData.nfe_data.map((nfe, index) => (
                <Card key={index} variant="outlined">
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      NF-e Nº {nfe.numero}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Fornecedor:</strong> {nfe.fornecedor}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Data Emissão:</strong>{" "}
                      {nfe.data_emissao
                        ? new Date(nfe.data_emissao).toLocaleDateString("pt-BR")
                        : ""}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Valor:</strong>{" "}
                      {nfe.valor ? formatCurrency(parseFloat(nfe.valor)) : ""}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Chave:</strong> {nfe.chave}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<PictureAsPdfIcon />}
                      onClick={() => handleNfeClick(nfe)}
                      color="primary"
                    >
                      Visualizar DANFE
                    </Button>
                  </CardActions>
                </Card>
              ))}
            </Box>
          ) : (
            <Typography>
              Nenhuma Nota Fiscal encontrada para este pedido.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Fechar</Button>
        </DialogActions>
      </Dialog>

      {/* NF Not Found Dialog */}
      <Dialog
        open={showNfNotFoundDialog}
        onClose={() => setShowNfNotFoundDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <ReceiptIcon color="warning" />
          Nota Fiscal Não Encontrada
        </DialogTitle>
        <DialogContent>
          <Box sx={{ py: 2 }}>
            <Typography variant="body1" gutterBottom>
              A nota fiscal <strong>{nfNotFoundInfo?.num_nf}</strong> não foi
              encontrada no sistema SIEG.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Isso pode ocorrer por alguns motivos:
            </Typography>
            <Box component="ul" sx={{ mt: 1, pl: 2 }}>
              <Typography component="li" variant="body2" color="text.secondary">
                <strong>Nota Fiscal de Serviço (NFS-e):</strong> O sistema SIEG
                atualmente não suporta notas fiscais de serviço, apenas NF-e
                (produtos).
              </Typography>
              <Typography
                component="li"
                variant="body2"
                color="text.secondary"
                sx={{ mt: 1 }}
              >
                <strong>Nota ainda não sincronizada:</strong> A nota pode não
                ter sido transmitida ou processada ainda.
              </Typography>
              <Typography
                component="li"
                variant="body2"
                color="text.secondary"
                sx={{ mt: 1 }}
              >
                <strong>Fornecedor diferente:</strong> A nota pode ter sido
                emitida por um CNPJ diferente do cadastrado.
              </Typography>
            </Box>
            {nfNotFoundInfo && (
              <Box sx={{ mt: 3, p: 2, bgcolor: "grey.100", borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Detalhes da busca:
                </Typography>
                <Typography variant="body2">
                  Pedido: <strong>{nfNotFoundInfo.cod_pedc}</strong>
                </Typography>
                <Typography variant="body2">
                  Fornecedor: <strong>{nfNotFoundInfo.fornecedor}</strong>
                </Typography>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowNfNotFoundDialog(false)}>Fechar</Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}

const UnifiedSearch = () => {
  const SEARCH_MODE_STORAGE_KEY = "searchModePreference";
  const SEARCH_PARAMS_STORAGE_KEY = "searchParamsPreference";
  const SHOW_SUGGESTIONS_STORAGE_KEY = "showSuggestionsPreference";
  const PER_PAGE_OPTIONS = [50, 100, 200, 300, 500];
  const DEFAULT_ENHANCED_FIELDS = [
    "descricao",
    "item_id",
    "cod_pedc",
    "fornecedor",
    "observacao",
    "num_nf",
  ];
  const DEFAULT_SEARCH_PARAMS = {
    query: "",
    searchPrecision: "precisa",
    score_cutoff: 100,
    selectedFuncName: "todos",
    searchByCodPedc: true,
    searchByFornecedor: true,
    searchByObservacao: true,
    searchByItemId: true,
    searchByDescricao: true,
    searchByAtendido: false,
    searchByNaoAtendido: false,
    searchByNumNF: true,
    min_value: "",
    max_value: "",
    valueSearchType: "item",
    ignoreDiacritics: true,
    exactSearch: false,
  };

  const getStoredSearchParams = () => {
    if (typeof window === "undefined") {
      return { ...DEFAULT_SEARCH_PARAMS };
    }
    try {
      const stored = localStorage.getItem(SEARCH_PARAMS_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return { ...DEFAULT_SEARCH_PARAMS, ...parsed };
      }
    } catch (error) {
      console.warn("Erro ao recuperar filtros salvos", error);
    }
    return { ...DEFAULT_SEARCH_PARAMS };
  };

  const [searchParams, setSearchParams] = useState(getStoredSearchParams);
  const [results, setResults] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [funcNames, setFuncNames] = useState([]); // Estado para armazenar os nomes dos compradores
  const [currentPage, setCurrentPage] = useState(1);
  const [noResults, setNoResults] = useState(0);
  const [perPage, setPerPage] = useState(100);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState("");
  const [estimatedResults, setEstimatedResults] = useState(0);
  const resultsRef = useRef(null);
  const [searchMode, setSearchMode] = useState(() => {
    if (typeof window === "undefined") {
      return "enhanced";
    }
    return localStorage.getItem(SEARCH_MODE_STORAGE_KEY) || "enhanced";
  });
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [showSuggestionsToggle, setShowSuggestionsToggle] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    const stored = localStorage.getItem(SHOW_SUGGESTIONS_STORAGE_KEY);
    return stored === "true";
  });
  const [showFulfilled, setShowFulfilled] = useState(true);

  const usingEnhanced = searchMode === "enhanced";

  // Format date to readable format (e.g., "15 de Janeiro de 2025, 14:30")
  const formatLastUpdated = (dateStr) => {
    if (!dateStr) return "—";
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;

      const months = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
      ];

      const day = date.getDate();
      const month = months[date.getMonth()];
      const year = date.getFullYear();
      const hours = date.getHours().toString().padStart(2, "0");
      const minutes = date.getMinutes().toString().padStart(2, "0");

      return `${day} de ${month} de ${year}, ${hours}:${minutes}`;
    } catch {
      return dateStr;
    }
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(
        SEARCH_PARAMS_STORAGE_KEY,
        JSON.stringify(searchParams)
      );
    }
  }, [searchParams]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(
        SHOW_SUGGESTIONS_STORAGE_KEY,
        JSON.stringify(showSuggestionsToggle)
      );
    }
  }, [showSuggestionsToggle]);

  useEffect(() => {
    if (resultsRef.current) {
      const resultsPosition = resultsRef.current.offsetTop - 100;
    }
  }, [results.length]);

  useEffect(() => {
    // Buscar os nomes dos compradores do backend
    const fetchFuncNames = async () => {
      try {
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/purchasers`,
          { withCredentials: true }
        );
        const sortedFuncNames = response.data
          .map((name) => name || "Sem nome") // Substituir nomes nulos por "Sem nome"
          .sort((a, b) => a.localeCompare(b));

        setFuncNames(sortedFuncNames);
      } catch (error) {
        console.error("Error fetching purchasers: ", error);
      }
    };

    const fetchLastUpdate = async () => {
      try {
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/last_update`,
          { withCredentials: true }
        );
        if (response.data && response.data.last_updated) {
          const date = new Date(response.data.last_updated);
          setLastUpdated(
            date.toLocaleDateString("pt-BR", {
              day: "2-digit",
              month: "2-digit",
              year: "numeric",
              timeZone: "UTC",
            })
          );
        }
      } catch (error) {
        console.error("Error fetching last update:", error);
        setLastUpdated("Data não disponível ");
      }
    };

    fetchLastUpdate();
    fetchFuncNames();
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(SEARCH_MODE_STORAGE_KEY, searchMode);
    }
  }, [searchMode]);

  useEffect(() => {
    if (!usingEnhanced || !showSuggestionsToggle) {
      setSuggestions([]);
      return undefined;
    }

    const term = (searchParams.query || "").trim();
    if (term.length < 2) {
      setSuggestions([]);
      return undefined;
    }

    let isActive = true;
    const handler = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const { data } = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/search_advanced/suggestions`,
          {
            params: { term, limit: 10 },
            withCredentials: true,
          }
        );
        if (isActive) {
          setSuggestions(
            (data?.suggestions || []).map((suggestion) => suggestion.value)
          );
        }
      } catch (err) {
        if (isActive) {
          console.error("Failed to fetch suggestions", err);
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
  }, [searchParams.query, usingEnhanced, showSuggestionsToggle]);

  useEffect(() => {
    setNoResults(results.length);
  }, [results]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (name === "searchPrecision") {
      let score_cutoff;
      if (value === "precisa") {
        score_cutoff = 100;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff,
        });
      } else if (value === "fuzzy") {
        score_cutoff = 80;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff,
        });
      } else if (value === "tentar_a_sorte") {
        score_cutoff = 60;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff,
        });
      }
    } else {
      setSearchParams({
        ...searchParams,
        [name]: type === "checkbox" ? checked : value,
      });
    }
  };

  const updateQuery = (value) => {
    setSearchParams((prev) => ({
      ...prev,
      query: value,
    }));
  };

  const handleModeToggle = (event) => {
    setSearchMode(event.target.checked ? "enhanced" : "classic");
  };

  const handleRestoreDefaults = () => {
    setSearchParams({ ...DEFAULT_SEARCH_PARAMS });
    setShowFulfilled(true);
    setSearchMode("enhanced");
    setShowSuggestionsToggle(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch(1);
    }
  };
  const resolveEnhancedFields = () => {
    const selected = [];
    if (searchParams.searchByDescricao) selected.push("descricao");
    if (searchParams.searchByItemId) selected.push("item_id");
    if (searchParams.searchByCodPedc) selected.push("cod_pedc");
    if (searchParams.searchByFornecedor) selected.push("fornecedor");
    if (searchParams.searchByObservacao) selected.push("observacao");
    if (searchParams.searchByNumNF) selected.push("num_nf");
    return selected.length ? selected : DEFAULT_ENHANCED_FIELDS;
  };

  const getEstimatedResults = async () => {
    if (usingEnhanced) {
      return;
    }
    const term = (searchParams.query || "").trim();
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/count_results`,
        {
          params: {
            query: term || undefined,
            score_cutoff: searchParams.score_cutoff,
            searchByCodPedc: searchParams.searchByCodPedc,
            searchByFornecedor: searchParams.searchByFornecedor,
            searchByObservacao: searchParams.searchByObservacao,
            searchByItemId: searchParams.searchByItemId,
            searchByNumNF: searchParams.searchByNumNF,
            searchByDescricao: searchParams.searchByDescricao,
            selectedFuncName: searchParams.selectedFuncName,
          },
          withCredentials: true,
        }
      );
      setEstimatedResults(response.data.count);
      setTotalPages(response.data.estimated_pages);
    } catch (error) {
      console.error("Error getting estimated results:", error);
    }
  };

  const handleSearch = async (page = 1, perPageOverride) => {
    const trimmedQuery = (searchParams.query || "").trim();
    const perPageToUse = perPageOverride ?? perPage;

    setLoading(true);
    if (!usingEnhanced) {
      await getEstimatedResults();
    }

    try {
      let response;

      if (usingEnhanced) {
        response = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/search_advanced`,
          {
            params: {
              query: trimmedQuery || undefined,
              fields: resolveEnhancedFields().join(","),
              selectedFuncName: searchParams.selectedFuncName,
              minValue: searchParams.min_value || undefined,
              maxValue: searchParams.max_value || undefined,
              valueSearchType: searchParams.valueSearchType,
              exactSearch: searchParams.exactSearch,
              page,
              per_page: perPageToUse,
            },
            withCredentials: true,
          }
        );
      } else {
        response = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/search_combined`,
          {
            params: {
              query: trimmedQuery,
              page,
              per_page: perPageToUse,
              score_cutoff: searchParams.score_cutoff,
              searchByCodPedc: searchParams.searchByCodPedc,
              searchByFornecedor: searchParams.searchByFornecedor,
              searchByObservacao: searchParams.searchByObservacao,
              searchByItemId: searchParams.searchByItemId,
              searchByDescricao: searchParams.searchByDescricao,
              searchByNumNF: searchParams.searchByNumNF,
              selectedFuncName: searchParams.selectedFuncName,
              minValue: searchParams.min_value,
              maxValue: searchParams.max_value,
              valueSearchType: searchParams.valueSearchType,
            },
            withCredentials: true,
          }
        );
      }

      const purchases = response.data?.purchases || [];
      setResults(purchases);
      setCurrentPage(response.data?.current_page || page);
      setTotalPages(response.data?.total_pages || 1);

      if (usingEnhanced) {
        setEstimatedResults(response.data?.total_results ?? purchases.length);
      }
    } catch (error) {
      console.error("Error fetching data", error);
      setResults([]);
      setCurrentPage(1);
      setTotalPages(1);
      setNoResults(0);
    } finally {
      setLoading(false);
    }
  };

  const handleItemClick = (itemId) => {
    setSelectedItemId(itemId);
  };

  const handleCloseItemScreen = () => {
    setSelectedItemId(null);
  };

  const formatDate = (dateString) => {
    const options = { day: "2-digit", month: "2-digit", year: "2-digit" };
    return new Date(dateString).toLocaleDateString(options);
  };

  const formatNumber = (number) => {
    if (number === undefined || number === null || isNaN(parseFloat(number))) {
      return "-";
    }
    return parseFloat(number).toFixed(2);
  };
  const formatCurrency = (number) => {
    if (number === undefined || number === null) return ""; // Verifica se o número é undefined ou null
    return number.toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  };

  const getFirstWords = (text, numWords) => {
    if (!text) return ""; // Verifica se o texto é undefined ou null
    return text.split(" ").slice(0, numWords).join(" ");
  };

  const handlePageChange = (newPage) => {
    handleSearch(newPage);
  };

  const handlePerPageChange = (event) => {
    const value = Number(event.target.value);
    setPerPage(value);
    setCurrentPage(1);
    handleSearch(1, value);
  };

  const searchFieldColumns = [
    [
      {
        name: "searchByCodPedc",
        label: "Código do Pedido de Compra",
        disabled: searchParams.searchPrecision !== "precisa",
      },
      {
        name: "searchByFornecedor",
        label: "Nome do Fornecedor",
        disabled: searchParams.searchPrecision !== "precisa",
      },
    ],
    [
      {
        name: "searchByObservacao",
        label: "Observação do Pedido de Compra",
        disabled: false,
      },
      {
        name: "searchByItemId",
        label: "Código do Item",
        disabled: searchParams.searchPrecision !== "precisa",
      },
    ],
    [
      {
        name: "searchByDescricao",
        label: "Descrição do Item",
        disabled: false,
      },
      {
        name: "searchByNumNF",
        label: "Número da Nota Fiscal",
        disabled: false,
      },
    ],
  ];

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fa" }}>
      {/* Header Section */}
      <Paper
        elevation={0}
        sx={{
          p: 3,
          mx: { xs: 2, md: 3 },
          mt: { xs: 2, md: 3 },
          mb: 3,
          background: "linear-gradient(135deg, #1a1f2e 0%, #2d3548 100%)",
          borderRadius: 3,
          color: "#fff",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
              Buscar Pedidos de Compra
            </Typography>
            <Typography
              variant="body2"
              sx={{ color: "rgba(255,255,255,0.7)", maxWidth: 450 }}
            >
              Pesquise por código, fornecedor, descrição de item ou nota fiscal.
            </Typography>
          </Box>

          {/* Last Update Info */}
          <Paper
            elevation={0}
            sx={{
              px: 2.5,
              py: 1.5,
              bgcolor: "rgba(255,255,255,0.15)",
              borderRadius: 2,
              border: "1px solid rgba(255,255,255,0.2)",
              minWidth: 200,
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 2,
              }}
            >
              <Box>
                <Typography
                  variant="caption"
                  sx={{
                    color: "rgba(255,255,255,0.8)",
                    display: "block",
                    fontWeight: 500,
                  }}
                >
                  Última atualização
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    mt: 0.5,
                  }}
                >
                  <ScheduleIcon sx={{ fontSize: 16, color: "#fff" }} />
                  <Typography
                    variant="body2"
                    sx={{ fontWeight: 700, color: "#fff" }}
                  >
                    {formatLastUpdated(lastUpdated)}
                  </Typography>
                </Box>
              </Box>
              <Button
                component={Link}
                to="/import"
                variant="outlined"
                size="small"
                startIcon={<RefreshIcon />}
                sx={{
                  color: "#fff",
                  borderColor: "rgba(255,255,255,0.4)",
                  textTransform: "none",
                  fontWeight: 600,
                  "&:hover": {
                    borderColor: "#fff",
                    bgcolor: "rgba(255,255,255,0.1)",
                  },
                }}
              >
                Atualizar
              </Button>
            </Box>
          </Paper>
        </Box>
      </Paper>

      <Box sx={{ px: { xs: 2, md: 3 }, pb: 3 }}>
        {/* Search Box */}
        <Paper
          elevation={0}
          sx={{
            p: 3,
            mb: 3,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box
            sx={{
              display: "flex",
              gap: 2,
              alignItems: "center",
              flexWrap: "wrap",
              mb: 3,
            }}
          >
            <Autocomplete
              sx={{ flexGrow: 1, minWidth: 300 }}
              freeSolo
              options={showSuggestionsToggle ? suggestions : []}
              loading={showSuggestionsToggle && loadingSuggestions}
              inputValue={searchParams.query}
              onInputChange={(_, newValue) => updateQuery(newValue)}
              onChange={(_, newValue, reason) => {
                if (typeof newValue === "string") {
                  updateQuery(newValue);
                  if (reason === "selectOption") {
                    setTimeout(() => handleSearch(1), 0);
                  }
                }
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Buscar pedidos"
                  placeholder="Ex.: motor 123, fornecedor, código..."
                  variant="outlined"
                  size="small"
                  onKeyDown={handleKeyDown}
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {showSuggestionsToggle && loadingSuggestions ? (
                          <CircularProgress color="inherit" size={18} />
                        ) : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
            />
            <Button
              variant="contained"
              onClick={() => handleSearch(1)}
              startIcon={<SearchIcon />}
              sx={{
                px: 3,
                py: 1,
                textTransform: "none",
                fontWeight: 600,
                bgcolor: "#1a1f2e",
                "&:hover": { bgcolor: "#2d3548" },
              }}
            >
              Buscar
            </Button>
          </Box>

          {/* Quick Filters - Pesquisar por... */}
          <Box sx={{ mb: 2 }}>
            <Typography
              variant="subtitle2"
              color="text.secondary"
              sx={{ mb: 1 }}
            >
              Pesquisar por...
            </Typography>
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                gap: 1,
                alignItems: "center",
              }}
            >
              {searchFieldColumns.flat().map((field) => (
                <FormControlLabel
                  key={field.name}
                  control={
                    <Checkbox
                      name={field.name}
                      checked={searchParams[field.name]}
                      onChange={handleChange}
                      disabled={field.disabled}
                      size="small"
                    />
                  }
                  label={<Typography variant="body2">{field.label}</Typography>}
                  sx={{ mr: 2 }}
                />
              ))}
            </Box>
          </Box>

          {/* Quick Filters Row 2 - Buyer selector and Busca exata */}
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 2,
              alignItems: "center",
            }}
          >
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <Select
                value={searchParams.selectedFuncName}
                onChange={handleChange}
                name="selectedFuncName"
                displayEmpty
              >
                <MenuItem value="todos">Todos os compradores</MenuItem>
                {funcNames.map((funcName) => (
                  <MenuItem key={funcName} value={funcName}>
                    {funcName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Checkbox
                  name="exactSearch"
                  checked={searchParams.exactSearch}
                  onChange={handleChange}
                  size="small"
                />
              }
              label={<Typography variant="body2">Busca exata</Typography>}
            />

            <Button
              variant="text"
              color="inherit"
              size="small"
              onClick={handleRestoreDefaults}
              sx={{ textTransform: "none", ml: "auto" }}
            >
              Limpar filtros
            </Button>
          </Box>
        </Paper>

        {/* Advanced Filters Accordion */}
        <Accordion
          elevation={0}
          sx={{
            mb: 3,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            "&:before": { display: "none" },
            "&.Mui-expanded": { margin: 0, mb: 3 },
          }}
          disableGutters
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{
              borderRadius: 3,
              "&.Mui-expanded": {
                borderBottomLeftRadius: 0,
                borderBottomRightRadius: 0,
              },
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <TuneIcon fontSize="small" color="action" />
              <Typography variant="subtitle2" fontWeight={600}>
                Filtros Avançados
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            <Divider sx={{ mb: 3 }} />
            <Grid container spacing={4}>
              {/* Search Mode Options */}
              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 2 }}>
                  Modo de busca
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={usingEnhanced}
                      onChange={handleModeToggle}
                      color="primary"
                      size="small"
                    />
                  }
                  label={
                    <Typography variant="body2">
                      {usingEnhanced ? "Busca aprimorada" : "Busca clássica"}
                    </Typography>
                  }
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={showSuggestionsToggle}
                      onChange={(e) => {
                        setShowSuggestionsToggle(e.target.checked);
                        if (!e.target.checked) setSuggestions([]);
                      }}
                      size="small"
                      disabled={!usingEnhanced}
                    />
                  }
                  label={
                    <Typography variant="body2">Mostrar sugestões</Typography>
                  }
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={!showFulfilled}
                      onChange={() => setShowFulfilled(!showFulfilled)}
                      color="warning"
                      size="small"
                    />
                  }
                  label={
                    <Typography variant="body2">Ocultar concluídos</Typography>
                  }
                />
              </Grid>

              {/* Value Filters */}
              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 2 }}>
                  Filtrar por valor
                </Typography>
                <RadioGroup
                  name="valueSearchType"
                  value={searchParams.valueSearchType}
                  onChange={handleChange}
                  row
                >
                  <FormControlLabel
                    value="item"
                    control={<Radio size="small" />}
                    label={<Typography variant="body2">Item</Typography>}
                  />
                  <FormControlLabel
                    value="order"
                    control={<Radio size="small" />}
                    label={<Typography variant="body2">Pedido</Typography>}
                  />
                </RadioGroup>
                <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                  <TextField
                    label="Mín"
                    name="min_value"
                    type="number"
                    value={searchParams.min_value}
                    onChange={handleChange}
                    size="small"
                    fullWidth
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">R$</InputAdornment>
                      ),
                    }}
                  />
                  <TextField
                    label="Máx"
                    name="max_value"
                    type="number"
                    value={searchParams.max_value}
                    onChange={handleChange}
                    size="small"
                    fullWidth
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">R$</InputAdornment>
                      ),
                    }}
                  />
                </Box>
              </Grid>

              {/* Search Precision (classic mode) */}
              <Grid item xs={12} md={4}>
                {!usingEnhanced && (
                  <>
                    <Typography
                      variant="subtitle2"
                      fontWeight={600}
                      sx={{ mb: 2 }}
                    >
                      Precisão da busca
                    </Typography>
                    <RadioGroup
                      name="searchPrecision"
                      value={searchParams.searchPrecision}
                      onChange={handleChange}
                    >
                      <FormControlLabel
                        value="precisa"
                        control={<Radio size="small" />}
                        label={<Typography variant="body2">Precisa</Typography>}
                      />
                      <FormControlLabel
                        value="fuzzy"
                        control={<Radio size="small" />}
                        label={
                          <Typography variant="body2">
                            Com tolerância
                          </Typography>
                        }
                      />
                      <FormControlLabel
                        value="tentar_a_sorte"
                        control={<Radio size="small" />}
                        label={<Typography variant="body2">Ampla</Typography>}
                      />
                    </RadioGroup>
                  </>
                )}
                {usingEnhanced && (
                  <>
                    <Typography
                      variant="subtitle2"
                      fontWeight={600}
                      sx={{ mb: 2 }}
                    >
                      Outras opções
                    </Typography>
                    <FormControlLabel
                      control={
                        <Checkbox
                          name="ignoreDiacritics"
                          checked={searchParams.ignoreDiacritics}
                          onChange={handleChange}
                          size="small"
                        />
                      }
                      label={
                        <Typography variant="body2">
                          Ignorar acentuação
                        </Typography>
                      }
                    />
                  </>
                )}
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Empty State - Show when no results and not loading */}
        {results.length === 0 && !loading && (
          <Paper
            elevation={0}
            sx={{
              p: 6,
              mb: 3,
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              textAlign: "center",
            }}
          >
            <SearchIcon sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Digite um termo para buscar
            </Typography>
            <Typography variant="body2" color="text.disabled">
              Pesquise por código, fornecedor, descrição de item ou nota fiscal
            </Typography>
          </Paper>
        )}

        {/* Loading State */}
        {loading && (
          <Box sx={{ mb: 3 }}>
            <Box sx={{ textAlign: "center", mb: 3 }}>
              <Skeleton
                variant="text"
                width={300}
                height={32}
                sx={{ mx: "auto" }}
                animation="wave"
              />
            </Box>
            {[1, 2, 3, 4, 5].map((i) => (
              <Paper
                key={i}
                elevation={0}
                sx={{
                  mb: 2,
                  overflow: "hidden",
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Box
                  sx={{
                    bgcolor: "#2d3548",
                    p: 2,
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                  }}
                >
                  <Skeleton
                    variant="circular"
                    width={24}
                    height={24}
                    animation="wave"
                    sx={{ bgcolor: "rgba(255,255,255,0.1)" }}
                  />
                  <Skeleton
                    variant="text"
                    width="80%"
                    height={28}
                    animation="wave"
                    sx={{ bgcolor: "rgba(255,255,255,0.1)" }}
                  />
                </Box>
                <Box sx={{ p: 2 }}>
                  {[1, 2].map((j) => (
                    <Box
                      key={j}
                      sx={{
                        display: "flex",
                        gap: 2,
                        py: 1,
                        borderBottom: j < 2 ? "1px solid #f0f0f0" : "none",
                      }}
                    >
                      <Skeleton variant="text" width={80} animation="wave" />
                      <Skeleton variant="text" width={60} animation="wave" />
                      <Skeleton variant="text" width={200} animation="wave" />
                      <Skeleton variant="text" width={80} animation="wave" />
                      <Skeleton variant="text" width={100} animation="wave" />
                    </Box>
                  ))}
                </Box>
              </Paper>
            ))}
          </Box>
        )}

        {/* Results Summary */}
        {!loading && results.length > 0 && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
              flexWrap: "wrap",
              gap: 2,
            }}
          >
            <Typography variant="body2" color="text.secondary" ref={resultsRef}>
              <strong>{noResults}</strong> resultados encontrados • Página{" "}
              <strong>{currentPage}</strong> de <strong>{totalPages}</strong>
            </Typography>

            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Por página:
              </Typography>
              <Select
                value={perPage}
                onChange={handlePerPageChange}
                size="small"
                sx={{ minWidth: 80 }}
              >
                {PER_PAGE_OPTIONS.map((option) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
            </Box>
          </Box>
        )}

        {/* Results Table */}
        {results.length > 0 && (
          <TableContainer
            component={Paper}
            elevation={0}
            sx={{
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              mb: 3,
            }}
          >
            <Table aria-label="collapsible table">
              <TableBody>
                {results.map((purchase) => (
                  <PurchaseRow
                    key={purchase.order.cod_pedc}
                    purchase={purchase}
                    formatDate={formatDate}
                    formatNumber={formatNumber}
                    formatCurrency={formatCurrency}
                    getFirstWords={getFirstWords}
                    handleItemClick={handleItemClick}
                    hideFulfilledItems={
                      !showFulfilled && purchase.order.is_fulfilled
                    }
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: 1,
            }}
          >
            <Button
              variant="outlined"
              size="small"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              sx={{ textTransform: "none" }}
            >
              Anterior
            </Button>
            <Typography variant="body2" sx={{ mx: 2 }}>
              Página {currentPage} de {totalPages}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              sx={{ textTransform: "none" }}
            >
              Próxima
            </Button>
          </Box>
        )}

        {selectedItemId && (
          <ItemScreen itemId={selectedItemId} onClose={handleCloseItemScreen} />
        )}
      </Box>
    </Box>
  );
};

export default UnifiedSearch;
