import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import ItemScreen from './ItemScreen';
import './UnifiedSearch.css';

import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableFooter,
  Paper, Collapse, Box, Typography, IconButton, TextField, Button, Radio, RadioGroup,
  FormControlLabel, FormControl, FormLabel, Checkbox, Select, MenuItem, InputAdornment
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import SearchIcon from '@mui/icons-material/Search';
import LogoutIcon from '@mui/icons-material/Logout';

function PurchaseRow(props) {
  const { purchase, formatDate, formatNumber, formatCurrency, getFirstWords, handleItemClick } = props;
  const [open, setOpen] = useState(true); // Expanded by default

  return (
    <React.Fragment>
      {/* Purchase header row */}
      <TableRow sx={{
        '& > *': { borderBottom: 'unset' },
        backgroundColor: '#daf0ffff', // Light blue background
        '&:hover': { backgroundColor: '#b5deffff' } // Slightly darker on hover
      }}>        <TableCell>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell colSpan={9} align="center" sx={{ fontWeight: 'bold' }}  >
          Pedido de Compra: {purchase.order.cod_pedc} ~ {purchase.order.fornecedor_id} {getFirstWords(purchase.order.fornecedor_descricao, 3)} - {formatCurrency(purchase.order.total_bruto)} ~ Comprador: {purchase.order.func_nome}. Empresa: {purchase.order.cod_emp1}
        </TableCell>
      </TableRow>

      {/* Collapsible items section */}
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={10}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>

              <Table size="small" aria-label="items">
                <TableHead>
                  <TableRow>
                    <TableCell>Data Emissão</TableCell>
                    <TableCell>Cod. item</TableCell>
                    <TableCell>Descrição do item</TableCell>
                    <TableCell>Quantidade</TableCell>
                    <TableCell>Preço Unitário</TableCell>
                    <TableCell>IPI</TableCell>
                    <TableCell>Total</TableCell>
                    <TableCell>Qtde Atendida</TableCell>
                    <TableCell>Num NF</TableCell>
                    <TableCell>Dt Entrada</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {purchase.items.map((item) => (
                    <TableRow
                      key={item.id}
                      sx={{
                        backgroundColor: item.quantidade === item.qtde_atendida
                          ? '#f4fbffff' // Light blue for fully fulfilled items
                          : (item.qtde_atendida > 0 && item.qtde_atendida < item.quantidade)
                            ? '#fff4f4ff' // Light red for partially fulfilled items
                            : 'inherit', // Default color for unfulfilled items
                        '&:hover': {
                          backgroundColor: item.quantidade === item.qtde_atendida
                            ? '#bbdefb' // Darker blue on hover
                            : (item.qtde_atendida > 0 && item.qtde_atendida < item.quantidade)
                              ? '#ffcdd2' // Darker red on hover
                              : '#f5f5f5' // Light gray on hover for default
                        }
                      }}
                    >
                      <TableCell>{formatDate(purchase.order.dt_emis)}</TableCell>
                      <TableCell
                        onClick={() => handleItemClick(item.id)}
                        sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                      >
                        {item.item_id}
                      </TableCell>
                      <TableCell>{item.descricao}</TableCell>
                      <TableCell>{formatNumber(item.quantidade)} {item.unidade_medida}</TableCell>
                      <TableCell>R$ {formatNumber(item.preco_unitario)}</TableCell>
                      <TableCell>{item.perc_ipi ? `${formatNumber(item.perc_ipi)}%` : '0%'}</TableCell>
                      <TableCell>R$ {formatNumber(item.total)}</TableCell>
                      <TableCell>{formatNumber(item.qtde_atendida)} {item.unidade_medida}</TableCell>
                      <TableCell>
                        {purchase.order.nfes.map(nf => (
                          <div key={nf.id}>{nf.num_nf}</div>
                        ))}
                      </TableCell>
                      <TableCell>
                        {purchase.order.nfes.map(nf => (
                          <div key={nf.id}>{nf.dt_ent ? formatDate(nf.dt_ent) : ''}</div>
                        ))}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                <TableFooter>
                  <TableRow>
                    <TableCell colSpan={10} align="right">
                      <Typography variant="body2" color="text.secondary">
                        <Typography variant="body2" gutterBottom component="div" sx={{ fontStyle: 'italic' }}>
                          Observação: {purchase.order.observacao}              Total: R$ {formatNumber(purchase.items.reduce((acc, item) => acc + item.total, 0))}
                        </Typography>

                      </Typography>
                    </TableCell>
                  </TableRow>
                </TableFooter>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
}

const UnifiedSearch = ({ onLogout }) => {
  const [searchParams, setSearchParams] = useState({
    query: '',
    searchPrecision: 'precisa',
    score_cutoff: 100,
    selectedFuncName: 'todos',
    searchByCodPedc: true,
    searchByFornecedor: true,
    searchByObservacao: true,
    searchByItemId: true,
    searchByDescricao: true,
    searchByAtendido: false,
    searchByNaoAtendido: false,
    min_value: '',
    max_value: '',
    valueSearchType: 'item'
  });
  const [results, setResults] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [funcNames, setFuncNames] = useState([]); // Estado para armazenar os nomes dos compradores
  const [showAllItems, setShowAllItems] = useState({}); // Estado para controlar a exibição de todos os itens
  const [currentPage, setCurrentPage] = useState(1);
  const [noResults, setNoResults] = useState(0);
  const [perPage, setPerPage] = useState(200);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState('');
  const [estimatedResults, setEstimatedResults] = useState(0);


  useEffect(() => {
    // Buscar os nomes dos compradores do backend
    const fetchFuncNames = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/purchasers`, { withCredentials: true });
        const sortedFuncNames = response.data
          .map(name => name || 'Sem nome') // Substituir nomes nulos por "Sem nome"
          .sort((a, b) => a.localeCompare(b));

        setFuncNames(sortedFuncNames);
      } catch (error) {
        console.error('Error fetching purchasers: ', error);
      }
    };

    const fetchLastUpdate = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/last_update`, { withCredentials: true });
        if (response.data && response.data.last_updated) {
          const date = new Date(response.data.last_updated);
          setLastUpdated(date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
          }));
        }
      } catch (error) {
        console.error('Error fetching last update:', error);
        setLastUpdated('Data não disponível ');
      }
    };

    fetchLastUpdate();
    fetchFuncNames();
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (name === 'searchPrecision') {
      let score_cutoff;
      if (value === 'precisa') {
        score_cutoff = 100;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff
        });
      } else if (value === 'fuzzy') {
        score_cutoff = 80;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff
        });
      } else if (value === 'tentar_a_sorte') {
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
        [name]: type === 'checkbox' ? checked : value
      });
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };
  const getEstimatedResults = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/count_results`, {
        params: {
          query: searchParams.query,
          score_cutoff: searchParams.score_cutoff,
          searchByCodPedc: searchParams.searchByCodPedc,
          searchByFornecedor: searchParams.searchByFornecedor,
          searchByObservacao: searchParams.searchByObservacao,
          searchByItemId: searchParams.searchByItemId,
          searchByDescricao: searchParams.searchByDescricao,
          selectedFuncName: searchParams.selectedFuncName
        },
        withCredentials: true
      });
      setEstimatedResults(response.data.count);
      setTotalPages(response.data.estimated_pages);
    } catch (error) {
      console.error('Error getting estimated results:', error);
    }
  };

  const handleSearch = async (page = 1) => {
    setLoading(true);
    await getEstimatedResults();
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_combined`, {
        params: {
          query: searchParams.query,
          page: page,
          per_page: perPage,
          score_cutoff: searchParams.score_cutoff,
          searchByCodPedc: searchParams.searchByCodPedc,
          searchByFornecedor: searchParams.searchByFornecedor,
          searchByObservacao: searchParams.searchByObservacao,
          searchByItemId: searchParams.searchByItemId,
          searchByDescricao: searchParams.searchByDescricao,
          selectedFuncName: searchParams.selectedFuncName,
          minValue: searchParams.min_value,
          maxValue: searchParams.max_value
        },
        withCredentials: true
      });

      if (response.data && response.data.purchases) {
        setResults(response.data.purchases);
        setCurrentPage(response.data.current_page || 1);
        setTotalPages(response.data.total_pages || 1);
        setNoResults(response.data.purchases.length || 0);
      } else {
        setResults([]);
        setCurrentPage(1);
        setTotalPages(1);
        setNoResults(0);
      }
    } catch (error) {
      console.error('Error fetching data', error);
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
    const options = { day: '2-digit', month: '2-digit', year: '2-digit' };
    return new Date(dateString).toLocaleDateString('pt-BR', options);
  };

  const formatNumber = (number) => {
    return number.toFixed(2);
  };

  const formatCurrency = (number) => {
    if (number === undefined || number === null) return ''; // Verifica se o número é undefined ou null
    return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const getFirstWords = (text, numWords) => {
    if (!text) return ''; // Verifica se o texto é undefined ou null
    return text.split(' ').slice(0, numWords).join(' ');
  };

  const toggleShowAllItems = (orderId) => {
    setShowAllItems(prevState => ({
      ...prevState,
      [orderId]: !prevState[orderId]
    }));
  };

  const handlePageChange = (newPage) => {
    handleSearch(newPage);
  };

  return (
    <div className="unified-search">
      <Typography variant="h5" gutterBottom>
        Pedidos de compras Ruah - atualizado em {lastUpdated} -
        <Link to="/import" style={{ marginLeft: 8, textDecoration: 'none' }}> Atualizar</Link>
      </Typography>

      <Box sx={{ display: 'flex', mb: 3, alignItems: 'center', gap: 2 }}>
        <TextField
          name="query"
          placeholder="Search..."
          variant="outlined"
          size="small"
          fullWidth
          value={searchParams.query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
   
        />
        <Button
          variant="contained"
          color="primary"
          onClick={() => handleSearch(1)}
          startIcon={<SearchIcon />}
        >
          Buscar
        </Button>
        <Button
          variant="outlined"
          color="error"
          onClick={onLogout}
          startIcon={<LogoutIcon />}
        >
          Logout
        </Button>
      </Box>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 5, mb: 5 }}>
        {/* Search fields section */}
        <FormControl component="fieldset" sx={{ minWidth: '200px' }}>
          <FormLabel component="legend">Pesquisar por...</FormLabel>
          <FormControlLabel
            control={
              <Checkbox
                name="searchByCodPedc"
                checked={searchParams.searchByCodPedc}
                onChange={handleChange}
                disabled={searchParams.searchPrecision !== 'precisa'}
              />
            }
            label="Código do Pedido de Compra"
            sx={{ marginBottom: '-10px' }}
          />
          <FormControlLabel
            control={
              <Checkbox
                name="searchByFornecedor"
                checked={searchParams.searchByFornecedor}
                onChange={handleChange}
                disabled={searchParams.searchPrecision !== 'precisa'}
              />
            }
            label="Nome do Fornecedor"
            sx={{ marginBottom: '-10px' }}
          />
          <FormControlLabel
            control={
              <Checkbox
                name="searchByObservacao"
                checked={searchParams.searchByObservacao}
                onChange={handleChange}
              />
            }
            label="Observação do Pedido de Compra"
            sx={{ marginBottom: '-10px' }}
          />
          <FormControlLabel
            control={
              <Checkbox
                name="searchByItemId"
                checked={searchParams.searchByItemId}
                onChange={handleChange}
                disabled={searchParams.searchPrecision !== 'precisa'}
              />
            }
            label="Código do Item"
            sx={{ marginBottom: '-10px' }}
          />
          <FormControlLabel
            control={
              <Checkbox
                name="searchByDescricao"
                checked={searchParams.searchByDescricao}
                onChange={handleChange}
              />
            }
            label="Descrição do Item"
            sx={{ marginBottom: '-10px' }}
          />
        </FormControl>

        {/* Search precision section */}
        <FormControl component="fieldset" sx={{ minWidth: '200px' }}>
          <FormLabel component="legend">Precisão da busca</FormLabel>
          <RadioGroup
            name="searchPrecision"
            value={searchParams.searchPrecision}
            onChange={handleChange}
          >
            <FormControlLabel
              value="precisa"
              control={<Radio />}
              label="Precisa"
              sx={{ marginBottom: '-10px' }}
            />
            <FormControlLabel
              value="fuzzy"
              control={<Radio />}
              label="Busca com erro de digitação"
              sx={{ marginBottom: '-10px' }}
            />
            <FormControlLabel
              value="tentar_a_sorte"
              control={<Radio />}
              label="Estou sem sorte"
              sx={{ marginBottom: '-10px' }}
            />
          </RadioGroup>
        </FormControl>

        {/* Purchaser section */}
        <FormControl sx={{ minWidth: '200px' }}>
          <FormLabel component="legend">Mostrar compradores</FormLabel>
          <Select
            name="selectedFuncName"
            value={searchParams.selectedFuncName}
            onChange={handleChange}
            size="small"
            fullWidth
          >
            <MenuItem value="todos">Todos os compradores</MenuItem>
            {funcNames.map((funcName) => (
              <MenuItem key={funcName} value={funcName}>
                {funcName}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Value filter section */}
        <FormControl component="fieldset" sx={{ minWidth: '200px' }}>
          <FormLabel component="legend">Filtrar por valor</FormLabel>
          <RadioGroup
            name="valueSearchType"
            value={searchParams.valueSearchType}
            onChange={handleChange}
          >
            <FormControlLabel
              value="item"
              control={<Radio />}
              label="Valor do Item"
              sx={{ marginBottom: '-10px' }}
            />
            <FormControlLabel
              value="order"
              control={<Radio />}
              label="Valor do Pedido"
              sx={{ marginBottom: '-10px' }}
            />
          </RadioGroup>

          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
            <TextField
              label="Valor mínimo"
              name="min_value"
              type="number"
              value={searchParams.min_value}
              onChange={handleChange}
              size="small"
              InputProps={{
                startAdornment: <InputAdornment position="start">R$</InputAdornment>,
              }}
            />
            <TextField
              label="Valor máximo"
              name="max_value"
              type="number"
              value={searchParams.max_value}
              onChange={handleChange}
              size="small"
              InputProps={{
                startAdornment: <InputAdornment position="start">R$</InputAdornment>,
              }}
            />
          </Box>
        </FormControl>
      </Box>

      {loading && (
        <Box sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          zIndex: 9999
        }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
            <div className="spinner"></div>
          </Box>
          <Typography>
            Buscando em aproximadamente {estimatedResults} resultados...
          </Typography>
        </Box>
      )}

      <Typography variant="h6" gutterBottom>
        Mostrando {noResults} resultados. Pagina {currentPage} de {totalPages}
      </Typography>

      <TableContainer component={Paper}>
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
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <div className="pagination">
        <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1}>Anterior</button>
        <span>Página {currentPage} de {totalPages}</span>
        <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages}>Próxima</button>
      </div>

      {selectedItemId && <ItemScreen itemId={selectedItemId} onClose={handleCloseItemScreen} />}
    </div>
  );
};

export default UnifiedSearch;