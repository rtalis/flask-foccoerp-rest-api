import React, { useState, useRef } from 'react';
import axios from 'axios';
import {
  Box,
  Button,
  Card,
  TableFooter,
  CircularProgress,
  Container,
  Divider,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  Snackbar,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip
} from '@mui/material';
import {
  Search as SearchIcon,
  Upload as UploadIcon,
  Download as DownloadIcon,
  Compare as CompareIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ArrowUpward as ArrowUpwardIcon,
  ArrowDownward as ArrowDownwardIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';
import './QuotationAnalyzer.css';

const QuotationAnalyzer = () => {
  const [codCotacao, setCodCotacao] = useState('');
  const [quotationData, setQuotationData] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [files, setFiles] = useState([]);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const fileInputRef = useRef(null);

  // Fetch quotation data from API
  const fetchQuotationData = async () => {
    if (!codCotacao) {
      setError('Por favor, informe o código da cotação');
      setSnackbar({
        open: true,
        message: 'O código da cotação é obrigatório',
        severity: 'error'
      });
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/quotation_items`, {
        params: { cod_cot: codCotacao },
        withCredentials: true
      });

      setQuotationData(response.data);
      setSnackbar({
        open: true,
        message: 'Cotação carregada com sucesso!',
        severity: 'success'
      });
    } catch (err) {
      setError(err.response?.data?.error || 'Erro ao buscar cotação');
      setSnackbar({
        open: true,
        message: 'Erro ao buscar dados da cotação',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle file upload
  const handleFileUpload = (event) => {
    const selectedFiles = Array.from(event.target.files);

    const allowedTypes = ['application/pdf', 'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'image/jpeg', 'image/png'];

    const validFiles = selectedFiles.filter(file => allowedTypes.includes(file.type));

    if (validFiles.length !== selectedFiles.length) {
      setSnackbar({
        open: true,
        message: 'Apenas arquivos PDF, Excel e imagens são permitidos',
        severity: 'warning'
      });
    }

    setFiles([...files, ...validFiles]);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Remove a file from the list
  const removeFile = (index) => {
    const newFiles = [...files];
    newFiles.splice(index, 1);
    setFiles(newFiles);
  };

  // Extract data from files
  const extractData = async () => {
    if (files.length === 0) {
      setSnackbar({
        open: true,
        message: 'Por favor, faça upload de pelo menos um arquivo',
        severity: 'warning'
      });
      return;
    }

    if (!codCotacao) {
      setSnackbar({
        open: true,
        message: 'O código da cotação é obrigatório',
        severity: 'error'
      });
      return;
    }

    setLoading(true);

    try {
      // Create a FormData object to send files
      const formData = new FormData();

      files.forEach((file, index) => {
        formData.append(`file_${index}`, file);
      });

      // Add quotation code if available
      formData.append('cod_cot', codCotacao);

      // Send to backend for processing
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/api/extract_quotation_data`,
        formData,
        {
          withCredentials: true,
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      setExtractedData(response.data);
      setSnackbar({
        open: true,
        message: 'Dados extraídos com sucesso!',
        severity: 'success'
      });
    } catch (err) {
      setError(err.response?.data?.error || 'Erro ao extrair dados');
      setSnackbar({
        open: true,
        message: 'Erro ao extrair dados dos arquivos',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Export data to Excel
  const exportToExcel = () => {
    if (!extractedData) {
      setSnackbar({
        open: true,
        message: 'Nenhum dado extraído para exportar',
        severity: 'warning'
      });
      return;
    }

    try {
      // Create comparison worksheet
      const comparisonData = [];

      extractedData.extractedData.forEach(supplierData => {
        const supplierName = supplierData.supplier;

        supplierData.items.forEach(item => {
          const itemRow = {
            'Fornecedor': supplierName,
            'Data Cotação': supplierData.date,
            'Código': item.code,
            'Descrição': item.description,
            'Quantidade': item.quantity,
            'Unidade': item.unit,
            'Preço Unitário': item.unitPrice,
            'Preço Total': item.totalPrice,
            'Fabricante': item.manufacturer || 'N/A',
            'Item Correspondente': item.matchedItemDescription || 'N/A',
            'Confiança': item.matchConfidence || 'N/A'
          };

          if (item.lastPurchase) {
            itemRow['Última Compra - Fornecedor'] = item.lastPurchase.fornecedor;
            itemRow['Última Compra - Preço'] = item.lastPurchase.price;
            itemRow['Última Compra - Data'] = new Date(item.lastPurchase.date).toLocaleDateString('pt-BR');
            itemRow['Diferença de Preço (%)'] = item.priceDifferencePercent || 'N/A';
          }

          comparisonData.push(itemRow);
        });
      });

      // Create worksheet
      const ws = XLSX.utils.json_to_sheet(comparisonData);

      // Set column widths
      const wscols = [
        { wch: 20 }, // Fornecedor
        { wch: 12 }, // Data Cotação
        { wch: 10 }, // Código
        { wch: 40 }, // Descrição
        { wch: 10 }, // Quantidade
        { wch: 8 },  // Unidade
        { wch: 12 }, // Preço Unitário
        { wch: 12 }, // Preço Total
        { wch: 15 }, // Fabricante
        { wch: 40 }, // Item Correspondente
        { wch: 10 }, // Confiança
        { wch: 20 }, // Última Compra - Fornecedor
        { wch: 15 }, // Última Compra - Preço
        { wch: 15 }, // Última Compra - Data
        { wch: 18 }  // Diferença de Preço (%)
      ];
      ws['!cols'] = wscols;

      // Create workbook and add the worksheet
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Comparação');

      // Create supplier-specific sheets
      extractedData.extractedData.forEach(supplierData => {
        const supplierName = supplierData.supplier.substring(0, 30); // Truncate name if too long
        const supplierItems = supplierData.items.map(item => ({
          'Código': item.code,
          'Descrição': item.description,
          'Quantidade': item.quantity,
          'Unidade': item.unit,
          'Preço Unitário': item.unitPrice,
          'Preço Total': item.totalPrice,
          'Fabricante': item.manufacturer || 'N/A',
          'Item Correspondente': item.matchedItemDescription || 'N/A',
          'Confiança': item.matchConfidence || 'N/A',
          'Diferença de Preço (%)': item.priceDifferencePercent || 'N/A'
        }));

        const supplierWs = XLSX.utils.json_to_sheet(supplierItems);
        XLSX.utils.book_append_sheet(wb, supplierWs, supplierName);
      });

      // Generate Excel file
      const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
      const data = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      // Save file
      saveAs(data, `Comparacao_Cotacoes_${new Date().toISOString().slice(0, 10)}.xlsx`);

      setSnackbar({
        open: true,
        message: 'Exportação para Excel concluída!',
        severity: 'success'
      });
    } catch (err) {
      setError('Erro ao exportar para Excel: ' + err.message);
      setSnackbar({
        open: true,
        message: 'Erro ao exportar para Excel',
        severity: 'error'
      });
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Format currency for display
  const formatCurrency = (value) => {
    if (value === undefined || value === null) return 'N/A';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  // Get color for price difference
  const getPriceDiffColor = (pctDiff) => {
    if (!pctDiff) return 'inherit';
    if (pctDiff < 0) return 'success.main'; // green for lower price
    if (pctDiff > 10) return 'error.main';  // red for >10% higher
    return 'warning.main'; // orange for 0-10% higher
  };

  // Get icon for price difference
  const getPriceDiffIcon = (pctDiff) => {
    if (!pctDiff) return null;
    if (pctDiff < 0) return <ArrowDownwardIcon fontSize="small" color="success" />;
    return <ArrowUpwardIcon fontSize="small" color={pctDiff > 10 ? "error" : "warning"} />;
  };

  return (
    <Container maxWidth="95%" className="quotation-extractor">
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Extração de Dados de Cotações
        </Typography>

        <Grid container spacing={2} alignItems="center" sx={{ mb: 3 }}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Código da Cotação"
              variant="outlined"
              value={codCotacao}
              onChange={(e) => setCodCotacao(e.target.value)}
              placeholder="Digite o código da cotação"
              required
              error={!codCotacao && error}
              helperText={!codCotacao && error ? "Campo obrigatório" : ""}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Button
              variant="contained"
              color="primary"
              startIcon={<SearchIcon />}
              onClick={fetchQuotationData}
              disabled={loading}
              fullWidth
            >
              {loading ? <CircularProgress size={24} /> : 'Buscar Cotação'}
            </Button>
          </Grid>
        </Grid>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Display quotation data immediately after searching */}
        {quotationData && (
          <Box sx={{ mb: 4 }}>
            <Typography variant="h5" gutterBottom>
              Cotação {quotationData.cod_cot} - {new Date(quotationData.dt_emissao).toLocaleDateString('pt-BR')}
            </Typography>

            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                    <TableCell>Código</TableCell>
                    <TableCell>Descrição</TableCell>
                    <TableCell>Quantidade</TableCell>
                    <TableCell>Fornecedor Anterior</TableCell>
                    <TableCell>Preço Anterior</TableCell>
                    <TableCell>Data Anterior</TableCell>
                    <TableCell>Pedido</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {quotationData.items.map((item, index) => (
                    <TableRow
                      key={index}
                      sx={{
                        '&:hover': { backgroundColor: '#f9f9f9' }
                      }}
                    >
                      <TableCell>{item.item_id}</TableCell>
                      <TableCell>{item.descricao}</TableCell>
                      <TableCell>{item.quantidade}</TableCell>
                      <TableCell>
                        {item.last_purchase ? item.last_purchase.fornecedor : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {item.last_purchase ? formatCurrency(item.last_purchase.price) : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {item.last_purchase ? new Date(item.last_purchase.date).toLocaleDateString('pt-BR') : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {item.last_purchase ? item.last_purchase.cod_pedc : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                <TableFooter>
                  <TableRow sx={{ backgroundColor: '#e9e9e9ff' }}>
                    <TableCell colSpan={7}>
                      <Box sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        width: '100%'
                      }}>
                        <Typography variant="body2" component="div" sx={{ fontWeight: 'bold' }}>
                          Total de Itens: {quotationData.items.length}
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                </TableFooter>
              </Table>
            </TableContainer>
          </Box>
        )}
        <Divider sx={{ my: 4 }} />

        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Upload de Arquivos de Cotação
          </Typography>

          <input
            accept=".pdf,.xls,.xlsx,.jpg,.jpeg,.png"
            style={{ display: 'none' }}
            id="raised-button-file"
            type="file"
            multiple
            ref={fileInputRef}
            onChange={handleFileUpload}
          />

          <label htmlFor="raised-button-file">
            <Button
              variant="outlined"
              component="span"
              startIcon={<UploadIcon />}
              fullWidth
              sx={{ mb: 2 }}
            >
              Selecionar Arquivos
            </Button>
          </label>

          <List dense>
            {files.map((file, index) => (
              <ListItem
                key={index}
                secondaryAction={
                  <IconButton edge="end" onClick={() => removeFile(index)}>
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <ListItemText
                  primary={file.name}
                  secondary={`${(file.size / 1024).toFixed(2)} KB - ${file.type}`}
                />
              </ListItem>
            ))}
          </List>

          <Button
            variant="contained"
            color="secondary"
            startIcon={<CompareIcon />}
            onClick={extractData}
            disabled={loading || files.length === 0 || !codCotacao}
            fullWidth
            sx={{ mt: 2 }}
          >
            {loading ? <CircularProgress size={24} /> : 'Extrair Dados dos Arquivos'}
          </Button>
        </Box>

        {extractedData && (
          <>
            <Divider sx={{ my: 4 }} />

            <Box sx={{ mb: 3 }}>
              <Typography variant="h5" gutterBottom>
                Dados Extraídos - Comparativo de Preços
              </Typography>

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={<DownloadIcon />}
                  onClick={exportToExcel}
                >
                  Exportar para Excel
                </Button>
              </Box>

              {/* Consolidated Results Table */}
              <TableContainer component={Paper} sx={{ mb: 4, overflowX: 'auto' }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      {/* Item information columns */}
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Código</TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Descrição</TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Qtd.</TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Fabricante</TableCell>

                      {/* Last purchase info */}
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Últ. Fornecedor</TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Últ. Preço</TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Data</TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Pedido</TableCell>

                      {/* Dynamic columns for each supplier with sub-columns */}
                      {extractedData.extractedData.map((supplier, index) => (
                        <React.Fragment key={index}>
                          <TableCell
                            align="center"
                            colSpan={3}
                            sx={{
                              fontWeight: 'bold',
                              backgroundColor: '#e3f2fd',
                              borderLeft: '2px solid #ccc',
                              borderRight: '2px solid #ccc',
                              borderBottom: 'none'
                            }}
                          >
                            <Typography variant="subtitle2">
                              {supplier.supplier}
                            </Typography>
                            <Typography variant="caption" display="block">
                              {supplier.date || 'N/A'}
                            </Typography>
                          </TableCell>
                        </React.Fragment>
                      ))}

                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Melhor Preço</TableCell>
                    </TableRow>

                    {/* Sub-header row for supplier details */}
                    <TableRow>
                      {/* Empty cells for item info columns */}
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>

                      {/* Supplier sub-columns */}
                      {extractedData.extractedData.map((supplier, index) => (
                        <React.Fragment key={index}>
                          <TableCell
                            align="center"
                            sx={{
                              fontWeight: 'bold',
                              backgroundColor: '#e3f2fd',
                              borderLeft: '2px solid #ccc'
                            }}
                          >
                            Preço
                          </TableCell>
                          <TableCell
                            align="center"
                            sx={{
                              fontWeight: 'bold',
                              backgroundColor: '#e3f2fd'
                            }}
                          >
                            Variação
                          </TableCell>
                          <TableCell
                            align="center"
                            sx={{
                              fontWeight: 'bold',
                              backgroundColor: '#e3f2fd',
                              borderRight: '2px solid #ccc'
                            }}
                          >
                            Conf.
                          </TableCell>
                        </React.Fragment>
                      ))}

                      <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}></TableCell>
                    </TableRow>
                  </TableHead>

                  <TableBody>
                    {/* Group items by their matched description */}
                    {(() => {
                      // Create a map of unique items
                      const uniqueItems = new Map();

                      // Process all supplier data to find unique items
                      extractedData.existingItems.forEach(item => {
                        const key = item.descricao;
                        if (!uniqueItems.has(key)) {
                          uniqueItems.set(key, {
                            item_id: item.item_id,
                            description: item.descricao,
                            quantity: item.quantidade,
                            last_purchase: item.last_purchase,
                            supplier_prices: Array(extractedData.extractedData.length).fill(null)
                          });
                        }
                      });

                      // Add items from extracted data that might not be in existingItems
                      extractedData.extractedData.forEach((supplier, supplierIndex) => {
                        supplier.items.forEach(item => {
                          const key = item.matchedItemDescription || item.description;

                          if (!uniqueItems.has(key)) {
                            uniqueItems.set(key, {
                              item_id: item.code,
                              description: key,
                              quantity: item.quantity,
                              manufacturer: item.manufacturer,
                              last_purchase: item.lastPurchase,
                              supplier_prices: Array(extractedData.extractedData.length).fill(null)
                            });
                          }

                          // Add this supplier's price for this item
                          const uniqueItem = uniqueItems.get(key);
                          uniqueItem.supplier_prices[supplierIndex] = {
                            price: item.unitPrice,
                            priceDiff: item.priceDifferencePercent,
                            confidence: item.matchConfidence
                          };

                          // Update manufacturer if available
                          if (item.manufacturer && !uniqueItem.manufacturer) {
                            uniqueItem.manufacturer = item.manufacturer;
                          }
                        });
                      });

                      // Convert the map to an array and sort by description
                      return Array.from(uniqueItems.values())
                        .sort((a, b) => a.description.localeCompare(b.description))
                        .map((item, index) => {
                          // Find the best price (lowest non-zero price)
                          const validPrices = item.supplier_prices
                            .filter(sp => sp && sp.price > 0)
                            .map(sp => sp.price);
                          const bestPrice = validPrices.length > 0 ? Math.min(...validPrices) : null;

                          return (
                            <TableRow
                              key={index}
                              sx={{
                                backgroundColor: index % 2 === 0 ? 'white' : '#fafafa',
                                '&:hover': { backgroundColor: '#f0f0f0' }
                              }}
                            >
                              <TableCell>{item.item_id || 'N/A'}</TableCell>
                              <TableCell>
                                <Typography variant="body2" sx={{ maxWidth: 300, whiteSpace: 'normal' }}>
                                  {item.description}
                                </Typography>
                              </TableCell>
                              <TableCell>{item.quantity || 'N/A'}</TableCell>
                              <TableCell>{item.manufacturer || 'N/A'}</TableCell>
                              <TableCell>
                                {item.last_purchase ? item.last_purchase.fornecedor : 'N/A'}
                              </TableCell>
                              <TableCell>
                                {item.last_purchase ? formatCurrency(item.last_purchase.price) : 'N/A'}
                              </TableCell>
                              <TableCell>
                                {item.last_purchase ? new Date(item.last_purchase.date).toLocaleDateString('pt-BR') : 'N/A'}
                              </TableCell>
                              <TableCell>
                                {item.last_purchase ? item.last_purchase.cod_pedc : 'N/A'}
                              </TableCell>

                              {/* Render each supplier's price data in separate columns */}
                              {item.supplier_prices.map((supplierPrice, spIndex) => {
                                const isBestPrice = supplierPrice && supplierPrice.price === bestPrice && supplierPrice.price > 0;
                                return (
                                  <React.Fragment key={spIndex}>
                                    {/* Price column */}
                                    <TableCell
                                      align="center"
                                      sx={{
                                        backgroundColor: isBestPrice ? 'rgba(76, 175, 80, 0.15)' : 'inherit',
                                        fontWeight: isBestPrice ? 'bold' : 'normal',
                                        borderLeft: '2px solid #ccc'
                                      }}
                                    >
                                      {supplierPrice ? formatCurrency(supplierPrice.price) : '—'}
                                    </TableCell>

                                    {/* Price difference column */}
                                    <TableCell align="center">
                                      {supplierPrice && supplierPrice.priceDiff !== undefined ? (
                                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                          {getPriceDiffIcon(supplierPrice.priceDiff)}
                                          <Typography
                                            variant="body2"
                                            color={getPriceDiffColor(supplierPrice.priceDiff)}
                                          >
                                            {supplierPrice.priceDiff > 0 ? '+' : ''}{supplierPrice.priceDiff}%
                                          </Typography>
                                        </Box>
                                      ) : '—'}
                                    </TableCell>

                                    {/* Confidence column */}
                                    <TableCell
                                      align="center"
                                      sx={{
                                        borderRight: '2px solid #ccc'
                                      }}
                                    >
                                      {supplierPrice && supplierPrice.confidence ? (
                                        <Chip
                                          label={supplierPrice.confidence}
                                          size="small"
                                          color={
                                            supplierPrice.confidence === "Alta" ? "success" :
                                              supplierPrice.confidence === "Média" ? "warning" :
                                                supplierPrice.confidence === "Baixa" ? "error" : "default"
                                          }
                                          sx={{ height: 20, fontSize: '0.7rem' }}
                                        />
                                      ) : '—'}
                                    </TableCell>
                                  </React.Fragment>
                                );
                              })}

                              {/* Best price column */}
                              <TableCell align="center" sx={{ backgroundColor: '#e8f5e9', fontWeight: 'bold' }}>
                                {bestPrice ? formatCurrency(bestPrice) : 'N/A'}
                              </TableCell>
                            </TableRow>
                          );
                        });
                    })()}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>

          </>
        )}
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default QuotationAnalyzer;