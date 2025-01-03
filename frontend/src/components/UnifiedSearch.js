import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ItemScreen from './ItemScreen';
import './UnifiedSearch.css'; // Adicione um arquivo CSS para estilos personalizados

const UnifiedSearch = ({ onLogout }) => {
  const [searchParams, setSearchParams] = useState({
    query: '',
    searchByCodPedc: true,
    searchByFornecedor: true,
    searchByObservacao: true,
    searchByDescricao: true,
    searchByItemId: true,
    searchByAtendido: true, // Adiciona o filtro por itens atendidos
    searchByNaoAtendido: true, // Adiciona o filtro por itens não atendidos
    searchPrecision: 'precisa', // Adiciona o parâmetro de precisão de busca
    score_cutoff: 100, // Valor padrão para precisão precisa
    selectedFuncName: 'todos' // Adiciona o filtro para o comprador selecionado
  });
  const [results, setResults] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [funcNames, setFuncNames] = useState([]); // Estado para armazenar os nomes dos compradores
  const [showAllItems, setShowAllItems] = useState({}); // Estado para controlar a exibição de todos os itens
  const [showFuncName, setShowFuncName] = useState({});

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
        console.error('Error fetching purchasers', error);
      }
    };

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
          score_cutoff: score_cutoff,
          searchByCodPedc: true,
          searchByFornecedor: true,
          searchByItemId: true
        });
      } else if (value === 'fuzzy') {
        score_cutoff = 70;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff,
          searchByCodPedc: false,
          searchByFornecedor: false,
          searchByItemId: false
        });
      } else if (value === 'tentar_a_sorte') {
        score_cutoff = 50;
        setSearchParams({
          ...searchParams,
          searchPrecision: value,
          score_cutoff: score_cutoff,
          searchByCodPedc: false,
          searchByFornecedor: false,
          searchByItemId: false
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

  const handleSearch = async () => {
    try {
      let purchaseResponse = [];
      let itemResponse = [];
      const uniqueResults = [];
      const seenIds = new Set();

      if (searchParams.searchPrecision === 'precisa') {
        if (searchParams.searchByCodPedc || searchParams.searchByFornecedor || searchParams.searchByObservacao || searchParams.searchByFuncName) {
          const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_purchases`, {
            params: {
              cod_pedc: searchParams.searchByCodPedc ? searchParams.query : '',
              fornecedor_descricao: searchParams.searchByFornecedor ? searchParams.query : '',
              observacao: searchParams.searchByObservacao ? searchParams.query : '',
              func_name: searchParams.searchByFuncName ? searchParams.selectedFuncName : ''
            },
            withCredentials: true
          });
          purchaseResponse = response.data;
        }

        if (searchParams.searchByDescricao || searchParams.searchByItemId) {
          const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_items`, {
            params: {
              descricao: searchParams.searchByDescricao ? searchParams.query : '',
              item_id: searchParams.searchByItemId ? searchParams.query : ''
            },
            withCredentials: true
          });
          itemResponse = response.data;
        }
      } else {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_fuzzy`, {
          params: {
            query: searchParams.query,
            precision: searchParams.searchPrecision,
            score_cutoff: searchParams.score_cutoff,
            cod_pedc: searchParams.searchByCodPedc ? searchParams.query : '',
            fornecedor_descricao: searchParams.searchByFornecedor ? searchParams.query : '',
            observacao: searchParams.searchByObservacao ? searchParams.query : '',
            descricao: searchParams.searchByDescricao ? searchParams.query : '',
            item_id: searchParams.searchByItemId ? searchParams.query : '',
            func_name: searchParams.searchByFuncName ? searchParams.selectedFuncName : ''
          },
          withCredentials: true
        });
        const fuzzyResponse = response.data;
        purchaseResponse = fuzzyResponse.purchases;
        itemResponse = fuzzyResponse.items;
      }

      const combinedResults = [...purchaseResponse, ...itemResponse];

      combinedResults.forEach(result => {
        const id = result.cod_pedc || result.id;
        if (!seenIds.has(id)) {
          seenIds.add(id);
          uniqueResults.push(result);
        }
      });

      uniqueResults.sort((a, b) => {
        const dateA = new Date(a.dt_emis || a.order.dt_emis);
        const dateB = new Date(b.dt_emis || b.order.dt_emis);

        if (dateB - dateA !== 0) {
          return dateB - dateA; // Ordenar por data de emissão (mais recente primeiro)
        }

        const codPedcA = parseInt(a.cod_pedc || a.order.cod_pedc, 10);
        const codPedcB = parseInt(b.cod_pedc || b.order.cod_pedc, 10);

        return codPedcB - codPedcA; // Ordenar por código do pedido (mais alto primeiro)
      });

      // Filtrar por itens atendidos e não atendidos


      setResults(uniqueResults);
    } catch (error) {
      console.error('Error fetching data', error);
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

  const toggleShowFuncName = (funcName) => {
    setShowFuncName(prevState => ({
      ...prevState,
      [funcName]: !prevState[funcName]
    }));
  };

  return (
    <div className="unified-search">
      <h2>Pedidos de compras Ruah</h2>
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
        <button onClick={handleSearch} className="search-button">
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
          <h3>Mostrar itens</h3>
          <label>
            <input
              type="radio"
              name="searchByAtendido"
              value="todos"
              checked={searchParams.searchByAtendido && searchParams.searchByNaoAtendido}
              onChange={() => setSearchParams({ ...searchParams, searchByAtendido: true, searchByNaoAtendido: true })}
            />
            Todos os itens
          </label>
          <label>
            <input
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
              name="searchByNaoAtendido"
              value="itens-pendentes"
              checked={!searchParams.searchByAtendido && searchParams.searchByNaoAtendido}
              onChange={() => setSearchParams({ ...searchParams, searchByAtendido: false, searchByNaoAtendido: true })}
            />
            Somente itens pendentes
          </label>
        </div>
      </div>
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
          {results.filter(item => showAllItems[item.cod_pedc] || (searchParams.searchByAtendido && item.quantidade === item.qtde_atendida) || (searchParams.searchByNaoAtendido && item.quantidade !== item.qtde_atendida))
            .filter(result => showFuncName[result.func_nome] || searchParams.selectedFuncName === 'todos' || result.func_nome === searchParams.selectedFuncName)
            .map((result) => (
              <React.Fragment key={result.cod_pedc}>
                <tr>
                  <td colSpan="10" className="order-header">
                    Pedido de Compra: {result.cod_pedc} ~ {result.order ? result.order.fornecedor_id : result.fornecedor_id} {getFirstWords(result.order ? result.order.fornecedor_descricao : result.fornecedor_descricao, 3)} - {formatCurrency(result.order ? result.order.total_bruto : result.total_bruto)} ~ Comprador: {result.order ? result.order.func_nome : result.func_nome}
                    <button className={`botao-mostrar ${(searchParams.searchByAtendido !== searchParams.searchByNaoAtendido) ? 'visible' : ''}`} onClick={() => toggleShowAllItems(result.cod_pedc)}>
                      {showAllItems[result.cod_pedc] ? 'Ocultar' : 'Mostrar todos'}
                    </button>
                  </td>
                </tr>
                {result.items ? (
                  result.items
                    .filter(item => showAllItems[result.cod_pedc] || (searchParams.searchByAtendido && item.quantidade === item.qtde_atendida) || (searchParams.searchByNaoAtendido && item.quantidade !== item.qtde_atendida))
                    .map((item) => (
                      <tr key={item.id} className={`item-row ${item.quantidade === item.qtde_atendida ? 'atendida' : 'nao-atendida'}`}>
                        <td>{formatDate(result.dt_emis)}</td>
                        <td>{result.cod_pedc}</td>
                        <td className="clickable" onClick={() => handleItemClick(item.id)}>{item.item_id}</td>
                        <td>{item.descricao}</td>
                        <td>{formatNumber(item.quantidade)} {item.unidade_medida}</td>
                        <td>R$ {formatNumber(item.preco_unitario)}</td>
                        <td>R$ {formatNumber(item.total)}</td>
                        <td>{result.observacao}</td>
                        <td>{formatNumber(item.qtde_atendida)} {item.unidade_medida}</td>
                        <td>{item.nfes.map(nf => nf.num_nf).join(', ')}</td>
                      </tr>
                    ))
                ) : (
                  <tr key={result.id} className={`item-row ${result.quantidade === result.qtde_atendida ? 'atendida' : 'nao-atendida'}`}>
                    <td>{formatDate(result.order ? result.order.dt_emis : '')}</td>
                    <td>{result.cod_pedc}</td>
                    <td className="clickable" onClick={() => handleItemClick(result.id)}>{result.item_id}</td>
                    <td>{result.descricao}</td>
                    <td>{formatNumber(result.quantidade)} {result.unidade_medida}</td>
                    <td>R$ {formatNumber(result.preco_unitario)}</td>
                    <td>R$ {formatNumber(result.total)}</td>
                    <td>{result.order ? result.order.observacao : ''}</td>
                    <td>{formatNumber(result.qtde_atendida)} {result.unidade_medida}</td>
                    <td>{result.nfes.map(nf => nf.num_nf).join(', ')}</td>
                  </tr>
                )}
              </React.Fragment>
            ))}
        </tbody>
      </table>
      {selectedItemId && <ItemScreen itemId={selectedItemId} onClose={handleCloseItemScreen} />}
    </div>
  );
};

export default UnifiedSearch;