import { useState, useRef } from 'react';
import axios from 'axios';
import { generateQuotationExcel } from '../utils/excelUtils';

import {
  Box,
  Button,
  Card,
  TableFooter,
  CircularProgress,
  Container,
  Divider,
  InputAdornment,
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

} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon,
  PictureAsPdf as PdfIcon,
  InsertDriveFile as FileIcon,
  Image as ImageIcon,
  TableChart as TableChartIcon,
  Search as SearchIcon,
  Download as DownloadIcon,
  Compare as CompareIcon,
  Delete as DeleteIcon,
  ArrowUpward as ArrowUpwardIcon,
  ArrowDownward as ArrowDownwardIcon

} from '@mui/icons-material';


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
  const [dragActive, setDragActive] = useState(false);
  const quotationDataRef = useRef(null);

  const resultsRef = useRef(null);

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

      // Scroll to quotation data section after data is loaded
      setTimeout(() => {
        if (quotationDataRef.current) {
          quotationDataRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 500);
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

  const getFirstWords = (text, numWords) => {
    if (!text) return ''; // Verifica se o texto é undefined ou null
    return text.split(' ').slice(0, numWords).join(' ');
  };

  const getFirstChars = (text, numChars) => {
    if (!text) return '—'; // Handle null or undefined
    return text.length > numChars ? text.substring(0, numChars) + '...' : text;
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
      formData.append('cod_cot', codCotacao);
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

      // Scroll to results section
      setTimeout(() => {
        if (resultsRef.current) {
          resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 500);
    } catch (err) {
      // Error handling
    } finally {
      setLoading(false);
    }
  };
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
      const result = generateQuotationExcel(extractedData);

      if (result.success) {
        setSnackbar({
          open: true,
          message: 'Exportação para Excel concluída!',
          severity: 'success'
        });
      } else {
        throw new Error(result.error);
      }
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
    if (value === undefined || value === null) return '—';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };


  return (
    <Container maxWidth="95%" className="quotation-extractor">
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Extração de Dados de Cotações
        </Typography>

        <Grid container spacing={2}  alignItems="stretch" sx={{ mb: 3 }}>
          <Grid item xs={12}>
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
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  fetchQuotationData();
                }
              }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>

          <Grid item xs={12}>
            <Button
              variant="contained"
              color="primary"
              startIcon={<SearchIcon />}
              onClick={fetchQuotationData}
              disabled={loading}
              fullWidth
              sx={{ height: '56px' }}
            >
              {loading ? <CircularProgress size={24} /> : 'Buscar Cotação'}
            </Button>
          </Grid>
        </Grid>



        {/* Display quotation data immediately after searching */}
        {quotationData && (
          <Box sx={{ mb: 4 }} className="fade-in" ref={quotationDataRef}>
            <Typography variant="h6" className="section-title">
              <TableChartIcon className="section-title-icon" />
              Dados da Cotação {quotationData.cod_cot}
            </Typography>

            <Card className="section-card">
              <Box className="section-content">
                <Typography variant="subtitle1" sx={{ mb: 2 }}>
                  Data de Emissão: {new Date(quotationData.dt_emissao).toLocaleDateString('pt-BR')}
                </Typography>

                <TableContainer component={Paper} className="table-container">
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                        <TableCell className="table-header-cell">Código</TableCell>
                        <TableCell className="table-header-cell">Descrição</TableCell>
                        <TableCell className="table-header-cell">Quantidade</TableCell>
                        <TableCell className="table-header-cell">Fornecedor Anterior</TableCell>
                        <TableCell className="table-header-cell">Preço Anterior</TableCell>
                        <TableCell className="table-header-cell">Data Anterior</TableCell>
                        <TableCell className="table-header-cell">Pedido</TableCell>
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
                          <TableCell>
                            <Typography variant="body2" sx={{ maxWidth: 300, whiteSpace: 'normal' }}>
                              {item.descricao}
                            </Typography>
                          </TableCell>
                          <TableCell>{item.quantidade}</TableCell>
                          <TableCell>
                            {item.last_purchase ? getFirstChars(item.last_purchase.fornecedor, 15) : '—'}
                          </TableCell>
                          <TableCell>
                            {item.last_purchase ? formatCurrency(item.last_purchase.price) : '—'}
                          </TableCell>
                          <TableCell>
                            {item.last_purchase ? new Date(item.last_purchase.date).toLocaleDateString('pt-BR') : '—'}
                          </TableCell>
                          <TableCell>
                            {item.last_purchase ? item.last_purchase.cod_pedc : '—'}
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
            </Card>
          </Box>
        )}
        <Divider sx={{ my: 4 }} />

        <Box sx={{ mb: 4 }} className="fade-in">
          <Typography variant="h6" className="section-title">
            <CloudUploadIcon className="section-title-icon" />
            Upload de Arquivos de Cotação
          </Typography>

          <Card className="section-card">
            <Box className="section-content">
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
                <Box
                  className={`dropzone ${dragActive ? 'dropzone-active' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDragActive(true);
                  }}
                  onDragLeave={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDragActive(false);
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDragActive(false);

                    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                      // Create an event-like object for the file upload handler
                      handleFileUpload({ target: { files: e.dataTransfer.files } });
                    }
                  }}
                >
                  <CloudUploadIcon className="dropzone-icon" />
                  <Typography variant="h6" gutterBottom>
                    Arraste e solte arquivos aqui
                  </Typography>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    ou clique para selecionar arquivos
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    Formatos aceitos: PDF, Excel, JPEG e PNG
                  </Typography>
                </Box>
              </label>

              {files.length > 0 && (
                <Box className="file-list">
                  {files.map((file, index) => (
                    <Box key={index} className="file-item">
                      {file.type.includes('pdf') ? (
                        <PdfIcon className="file-icon file-type-pdf" />
                      ) : file.type.includes('excel') || file.type.includes('spreadsheet') ? (
                        <DescriptionIcon className="file-icon file-type-excel" />
                      ) : file.type.includes('image') ? (
                        <ImageIcon className="file-icon file-type-image" />
                      ) : (
                        <FileIcon className="file-icon" />
                      )}
                      <Box className="file-info">
                        <Typography variant="body2" className="file-name">
                          {file.name}
                        </Typography>
                        <Typography variant="caption" className="file-meta">
                          {(file.size / 1024).toFixed(2)} KB - {file.type}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        className="file-remove"
                        onClick={() => removeFile(index)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  ))}
                </Box>
              )}

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
          </Card>
        </Box>

        {/* Display extracted data comparison table */}
        {extractedData && (
          <Box sx={{ mb: 3 }} className="fade-in" ref={resultsRef}>
            <Typography variant="h6" className="section-title">
              <CompareIcon className="section-title-icon" />
              Comparativo de Preços
            </Typography>

            <Card className="section-card">
              <Box className="section-content">
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
                <TableContainer component={Paper} sx={{ mb: 4, overflowX: 'auto' }} className="table-container">
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        {/* Item information columns */}
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Código</TableCell>
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Descrição</TableCell>
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Qtd.</TableCell>

                        {/* Last purchase info */}
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Últ. Fornecedor</TableCell>
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Últ. Preço</TableCell>
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Data</TableCell>
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f5f5f5' }}>Pedido</TableCell>

                        {/* Dynamic columns for each supplier*/}
                        {extractedData.extractedData.map((supplier, index) => (
                          <TableCell
                            align="center"
                            sx={{
                              fontWeight: 'bold',
                              backgroundColor: '#e3f2fd',
                              borderLeft: index === 0 ? '2px solid #ccc' : '1px solid #ccc',
                              borderRight: '1px solid #ccc'
                            }}
                          >
                            <Typography variant="subtitle2" noWrap>
                              {getFirstChars(supplier.supplier, 10)}
                            </Typography>
                            <Typography variant="caption" display="block">
                              {supplier.date || '—'}
                            </Typography>
                          </TableCell>
                        ))}
                        {/* Best price column */}
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#e8f5e9' }} align="center">
                          Melhor Preço
                        </TableCell>

                        {/* New columns */}
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#f0f4c3' }} align="center">
                          Variação
                        </TableCell>
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#bbdefb' }} align="center">
                          Confiança
                        </TableCell>
                        <TableCell sx={{ fontWeight: 'bold', backgroundColor: '#e1bee7', align: 'center' }} align="center">
                          Fabricante
                        </TableCell>
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
                                <TableCell>{item.item_id || '—'}</TableCell>
                                <TableCell>
                                  <Typography variant="body2" sx={{ maxWidth: 300, whiteSpace: 'normal' }}>
                                    {item.description}
                                  </Typography>
                                </TableCell>
                                <TableCell>{item.quantity || '—'}</TableCell>
                                <TableCell>
                                  {item.last_purchase ? getFirstChars(item.last_purchase.fornecedor, 10) : '—'}
                                </TableCell>
                                <TableCell>
                                  {item.last_purchase ? formatCurrency(item.last_purchase.price) : '—'}
                                </TableCell>
                                <TableCell>
                                  {item.last_purchase ? new Date(item.last_purchase.date).toLocaleDateString('pt-BR') : '—'}
                                </TableCell>
                                <TableCell>
                                  {item.last_purchase ? item.last_purchase.cod_pedc : '—'}
                                </TableCell>

                                {/* Render each supplier's price data in separate columns */}
                                {item.supplier_prices.map((supplierPrice, spIndex) => {
                                  const isBestPrice = supplierPrice && supplierPrice.price === bestPrice && supplierPrice.price > 0;
                                  return (
                                    <TableCell
                                      key={spIndex}
                                      align="center"
                                      sx={{
                                        backgroundColor: isBestPrice ? 'rgba(76, 175, 80, 0.15)' : 'inherit',
                                        fontWeight: isBestPrice ? 'bold' : 'normal',
                                        borderLeft: spIndex === 0 ? '2px solid #ccc' : '1px solid #ccc',
                                        borderRight: '1px solid #ccc'
                                      }}
                                    >
                                      {supplierPrice ? formatCurrency(supplierPrice.price) : '—'}
                                    </TableCell>
                                  );
                                })}

                                {/* Best price column */}
                                <TableCell align="center" sx={{ fontWeight: 'bold' }}>
                                  {bestPrice ? formatCurrency(bestPrice) : '—'}
                                </TableCell>
                                {/* Variation */}
                                <TableCell align="center" sx={{}}>
                                  {(() => {
                                    if (!bestPrice || !item.last_purchase || !item.last_purchase.price) return '—';

                                    const lastPrice = item.last_purchase.price;
                                    const variation = ((bestPrice - lastPrice) / lastPrice) * 100;
                                    const color = variation < 0 ? 'success.main' : (variation > 10 ? 'error.main' : 'warning.main');
                                    const icon = variation < 0 ?
                                      <ArrowDownwardIcon fontSize="small" color="success" /> :
                                      <ArrowUpwardIcon fontSize="small" color={variation > 10 ? "error" : "warning"} />;

                                    return (
                                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        {icon}
                                        <Typography color={color} sx={{ ml: 0.5 }}>
                                          {variation.toFixed(2)}%
                                        </Typography>
                                      </Box>
                                    );
                                  })()}
                                </TableCell>

                                {/* Confidence*/}
                                <TableCell align="center" sx={{}}>
                                  {(() => {
                                    if (!bestPrice) return '—';
                                    // Find the supplier with the best price
                                    const bestPriceSupplierIndex = item.supplier_prices.findIndex(sp =>
                                      sp && sp.price === bestPrice && sp.price > 0);

                                    if (bestPriceSupplierIndex === -1) return '—';

                                    const confidence = item.supplier_prices[bestPriceSupplierIndex].confidence;
                                    return confidence ? `${confidence}` : '—';
                                  })()}
                                </TableCell>

                                {/* Manufacturer */}
                                <TableCell align="center" sx={{}}>
                                  {(() => {
                                    if (!bestPrice) return '—';

                                    // Find the supplier with the best price
                                    const bestPriceSupplierIndex = item.supplier_prices.findIndex(sp =>
                                      sp && sp.price === bestPrice && sp.price > 0
                                    );
                                    if (bestPriceSupplierIndex === -1) return item.manufacturer || '—';
                                    // Get the supplier data
                                    const supplier = extractedData.extractedData[bestPriceSupplierIndex];
                                    // Find the item in that supplier's items
                                    const matchingItem = supplier.items.find(supplierItem =>
                                      (supplierItem.matchedItemDescription === item.description ||
                                        supplierItem.description === item.description) &&
                                      supplierItem.unitPrice === bestPrice
                                    );

                                    return matchingItem?.manufacturer || item.manufacturer || '—';
                                  })()}
                                </TableCell>
                              </TableRow>
                            );
                          });
                      })()}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </Card>
          </Box>
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