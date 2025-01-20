import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import ItemScreen from './ItemScreen';
import './UnifiedSearch.css'; // Adicione um arquivo CSS para estilos personalizados

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

  const handleSearch = async (page = 1) => {
    setLoading(true); // Inicia o carregamento
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
      setLoading(false); // Finaliza o carregamento
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
      <h2>
        Pedidos de compras Ruah - atualizado em {lastUpdated} -
        <Link to="/import" className="link"> Atualizar</Link>
      </h2>
      <div className="search-container">
        <button onClick={onLogout} className="logout-button">Logout</button>
        <input
          type="text"
          name="query"
          placeholder="Search..."
          value={searchParams.query}
          onChange={handleChange}
          onKeyDown={handleKeyDown} // Adiciona o manipulador de eventos onKeyDown
          className="search-input"
        />
        <button onClick={() => handleSearch(1)} className="search-button">
          <span className="icon">🔍</span>
          <span className="text">Buscar</span>
        </button>
      </div>
      <div className="checkbox-section">
        <div className="checkbox-group">
          <h3>Pesquisar por...</h3>
          <label className={searchParams.searchPrecision !== 'precisa' ? 'disabled' : ''}>
            <input
              type="checkbox"
              name="searchByCodPedc"
              checked={searchParams.searchByCodPedc}
              onChange={handleChange}
              disabled={searchParams.searchPrecision !== 'precisa'}
            />
            Código do Pedido de Compra
          </label>
          <label className={searchParams.searchPrecision !== 'precisa' ? 'disabled' : ''}>
            <input
              type="checkbox"
              name="searchByFornecedor"
              checked={searchParams.searchByFornecedor}
              onChange={handleChange}
              disabled={searchParams.searchPrecision !== 'precisa'}
            />
            Nome do Fornecedor
          </label>
          <label>
            <input
              type="checkbox"
              name="searchByObservacao"
              checked={searchParams.searchByObservacao}
              onChange={handleChange}
            />
            Observação do Pedido de Compra
          </label>

          <label className={searchParams.searchPrecision !== 'precisa' ? 'disabled' : ''}>
            <input
              type="checkbox"
              name="searchByItemId"
              checked={searchParams.searchByItemId}
              onChange={handleChange}
              disabled={searchParams.searchPrecision !== 'precisa'}
            />
            Código do Item
          </label>
          <label>
            <input
              type="checkbox"
              name="searchByDescricao"
              checked={searchParams.searchByDescricao}
              onChange={handleChange}
            />
            Descrição do Item
          </label>
        </div>

        <div className="checkbox-group">
          <h3>Precisão da busca</h3>
          <label>
            <input
              type="radio"
              name="searchPrecision"
              value="precisa"
              checked={searchParams.searchPrecision === 'precisa'}
              onChange={handleChange}
            />
            Precisa
          </label>
          <label>
            <input
              type="radio"
              name="searchPrecision"
              value="fuzzy"
              checked={searchParams.searchPrecision === 'fuzzy'}
              onChange={handleChange}
            />
            Busca com erro de digitação
          </label>
          <label>
            <input
              type="radio"
              name="searchPrecision"
              value="tentar_a_sorte"
              checked={searchParams.searchPrecision === 'tentar_a_sorte'}
              onChange={handleChange}
            />
            Estou sem sorte
          </label>
        </div>
        <div className="checkbox-group">
          <h3>Mostrar compradores</h3>
          <label>
            <input
              type="radio"
              name="selectedFuncName"
              value="todos"
              checked={searchParams.selectedFuncName === 'todos'}
              onChange={handleChange}
            />
            Todos os compradores
          </label>
          {funcNames.map((funcName) => (
            <label key={funcName}>
              <input
                type="radio"
                name="selectedFuncName"
                value={funcName}
                checked={searchParams.selectedFuncName === funcName}
                onChange={handleChange}
              />
              {funcName}
            </label>
          ))}
        </div>
        <div className="checkbox-group">
          <h3>Mostrar itens </h3>
          <label>
            <input
              type="radio"
              name="searchByAtendido"
              value="todos"
              disabled={true}
              checked={searchParams.searchByAtendido && searchParams.searchByNaoAtendido}
              onChange={() => setSearchParams({ ...searchParams, searchByAtendido: true, searchByNaoAtendido: true })}
            />
            Todos os itens
          </label>
          <label>
            <input
              disabled={true}
              type="radio"
              name="searchByAtendido"
              value="itens-concluidos"
              checked={searchParams.searchByAtendido && !searchParams.searchByNaoAtendido}
              onChange={() => setSearchParams({ ...searchParams, searchByAtendido: true, searchByNaoAtendido: false })}
            />
            Somente itens concluidos
          </label>
          <label>
            <input
              type="radio"
              disabled={true}
              name="searchByNaoAtendido"
              value="itens-pendentes"
              checked={!searchParams.searchByAtendido && searchParams.searchByNaoAtendido}
              onChange={() => setSearchParams({ ...searchParams, searchByAtendido: false, searchByNaoAtendido: true })}
            />
            Somente itens pendentes
          </label>
        </div>
        <div className="checkbox-group">
          <h3>Filtrar por valor</h3>
          <div className="value-type-selector">
            <label>
              <input
                type="radio"
                name="valueSearchType"
                value="item"
                checked={searchParams.valueSearchType === 'item'}
                onChange={handleChange}
              />
              Valor do Item
            </label>
            <label>
              <input
                type="radio"
                name="valueSearchType"
                value="order"
                checked={searchParams.valueSearchType === 'order'}
                onChange={handleChange}
              />
              Valor do Pedido
            </label>
          </div>
          <div className="value-filter">
            <div className="input-currency">
              <span className="currency-symbol">R$</span>
              <input
                type="number"
                name="min_value"
                value={searchParams.min_value}
                onChange={handleChange}
                placeholder={`Valor mínimo ${searchParams.valueSearchType === 'item' ? 'do item' : 'do pedido'}`}
                className="value-input"
              />
            </div>
            <div className="input-currency">
              <span className="currency-symbol">R$</span>
              <input
                type="number"
                name="max_value"
                value={searchParams.max_value}
                onChange={handleChange}
                placeholder={`Valor máximo ${searchParams.valueSearchType === 'item' ? 'do item' : 'do pedido'}`}
                className="value-input"
              />
            </div>
          </div>
        </div>
      </div>
      <div>
        <h3>Mostrando {noResults} resultados. Pagina {currentPage} de {totalPages}</h3></div>
      {loading ? (
        <div className="loading-icon">
          <div className="spinner"></div>
        </div>) : (
        <table className="results-table">
          <thead>
            <tr>
              <th>Data Emissão</th>
              <th>Cod. ped c.</th>
              <th>Cod. item</th>
              <th>Descrição do item</th>
              <th>Quantidade</th>
              <th>Preço Unitário</th>
              <th>Total</th>
              <th>Observação do ped.</th>
              <th>Qtde Atendida</th>
              <th>Num NF</th>
            </tr>
          </thead>
          <tbody>
            {results.map((purchase) => (
              <React.Fragment key={purchase.order.cod_pedc}>
                <tr>
                  <td colSpan="10" className="order-header">
                    Pedido de Compra: {purchase.order.cod_pedc} ~ {purchase.order.fornecedor_id} {getFirstWords(purchase.order.fornecedor_descricao, 3)} - {formatCurrency(purchase.order.total_bruto)} ~ Comprador: {purchase.order.func_nome}
                    <button className={`botao-mostrar ${(searchParams.searchByAtendido !== searchParams.searchByNaoAtendido) ? 'visible' : ''}`} onClick={() => toggleShowAllItems(purchase.order.cod_pedc)}>
                      {showAllItems[purchase.order.cod_pedc] ? 'Ocultar' : 'Mostrar todos'}
                    </button>
                  </td>
                </tr>
                {purchase.items.map((item) => (
                  <tr key={item.id} className={`item-row ${item.quantidade === item.qtde_atendida ? 'atendida' : 'nao-atendida'}`}>
                    <td>{formatDate(purchase.order.dt_emis)}</td>
                    <td>{item.cod_pedc}</td>
                    <td className="clickable" onClick={() => handleItemClick(item.id)}>{item.item_id}</td>
                    <td>{item.descricao}</td>
                    <td>{formatNumber(item.quantidade)} {item.unidade_medida}</td>
                    <td>R$ {formatNumber(item.preco_unitario)}</td>
                    <td>R$ {formatNumber(item.total)}</td>
                    <td>{purchase.order.observacao}</td>
                    <td>{formatNumber(item.qtde_atendida)} {item.unidade_medida}</td>
                    <td>{purchase.order.nfes.map(nf => nf.num_nf).join(', ')}</td>
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
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