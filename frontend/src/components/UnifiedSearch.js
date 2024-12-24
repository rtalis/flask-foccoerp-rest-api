import React, { useState } from 'react';
import axios from 'axios';
import './UnifiedSearch.css'; // Adicione um arquivo CSS para estilos personalizados

const UnifiedSearch = () => {
  const [searchParams, setSearchParams] = useState({
    query: '',
    searchByCodPedc: true,
    searchByFornecedor: true,
    searchByObservacao: true,
    searchByDescricao: true,
    searchByItemId: true,
    searchPrecision: 'precisa', // Adiciona o parâmetro de precisão de busca
    score_cutoff: 100 // Valor padrão para precisão precisa
  });
  const [results, setResults] = useState([]);

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
        if (searchParams.searchByCodPedc || searchParams.searchByFornecedor || searchParams.searchByObservacao) {
          const response = await axios.get('http://localhost:5000/api/search_purchases', {
            params: {
              cod_pedc: searchParams.searchByCodPedc ? searchParams.query : '',
              fornecedor_descricao: searchParams.searchByFornecedor ? searchParams.query : '',
              observacao: searchParams.searchByObservacao ? searchParams.query : ''
            }
          });
          purchaseResponse = response.data;
        }

        if (searchParams.searchByDescricao || searchParams.searchByItemId) {
          const response = await axios.get('http://localhost:5000/api/search_items', {
            params: {
              descricao: searchParams.searchByDescricao ? searchParams.query : '',
              item_id: searchParams.searchByItemId ? searchParams.query : ''
            }
          });
          itemResponse = response.data;
        }
      } else {
        const response = await axios.get('http://localhost:5000/api/search_fuzzy', {
          params: {
            query: searchParams.query,
            precision: searchParams.searchPrecision,
            score_cutoff: searchParams.score_cutoff,
            cod_pedc: searchParams.searchByCodPedc ? searchParams.query : '',
            fornecedor_descricao: searchParams.searchByFornecedor ? searchParams.query : '',
            observacao: searchParams.searchByObservacao ? searchParams.query : '',
            descricao: searchParams.searchByDescricao ? searchParams.query : '',
            item_id: searchParams.searchByItemId ? searchParams.query : ''
          }
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

      setResults(uniqueResults);
    } catch (error) {
      console.error('Error fetching data', error);
    }
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

  return (
    <div className="unified-search">
      <h2>Pedidos de compras Ruah</h2>
      <div className="search-container">
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
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <React.Fragment key={result.cod_pedc}>
              <tr>
                <td colSpan="10" className="order-header">
                  Pedido de Compra: {result.cod_pedc} ~ {result.order ? result.order.fornecedor_id : result.fornecedor_id} {getFirstWords(result.order ? result.order.fornecedor_descricao : result.fornecedor_descricao, 3)} - {formatCurrency(result.order ? result.order.total_bruto : result.total_bruto)} ~ Comprador: {result.order ? result.order.func_nome : result.func_nome}
                </td>
              </tr>
              {result.items ? (
                result.items.map((item) => (
                  <tr key={item.id} className={`item-row ${item.quantidade === item.qtde_atendida ? 'atendida' : 'nao-atendida'}`}>
                    <td>{formatDate(result.dt_emis)}</td>
                    <td>{result.cod_pedc}</td>
                    <td>{item.item_id}</td>
                    <td>{item.descricao}</td>
                    <td>{formatNumber(item.quantidade)} {item.unidade_medida}</td>
                    <td>R$ {formatNumber(item.preco_unitario)}</td>
                    <td>R$ {formatNumber(item.total)}</td>
                    <td>{result.observacao}</td>
                  </tr>
                ))
              ) : (
                <tr key={result.id} className={`item-row ${result.quantidade === result.qtde_atendida ? 'atendida' : 'nao-atendida'}`}>
                  <td>{formatDate(result.order ? result.order.dt_emis : '')}</td>
                  <td>{result.cod_pedc}</td>
                  <td>{result.item_id}</td>
                  <td>{result.descricao}</td>
                  <td>{formatNumber(result.quantidade)} {result.unidade_medida}</td>
                  <td>R$ {formatNumber(result.preco_unitario)}</td>
                  <td>R$ {formatNumber(result.total)}</td>
                  <td>{result.order ? result.order.observacao : ''}</td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default UnifiedSearch;