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
    fuzzySearch: false
  });
  const [results, setResults] = useState([]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSearchParams({
      ...searchParams,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleSearch = async () => {
    try {
      let purchaseResponse = [];
      let itemResponse = [];

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

      const combinedResults = [...purchaseResponse, ...itemResponse];

      combinedResults.sort((a, b) => {
        const dateA = new Date(a.dt_emis || a.order.dt_emis);
        const dateB = new Date(b.dt_emis || b.order.dt_emis);
      
        if (dateB - dateA !== 0) {
          return dateB - dateA; // Ordenar por data de emissão (mais recente primeiro)
        }
      
        const codPedcA = parseInt(a.cod_pedc || a.order.cod_pedc, 10);
        const codPedcB = parseInt(b.cod_pedc || b.order.cod_pedc, 10);
      
        return codPedcB - codPedcA; // Ordenar por código do pedido (mais alto primeiro)
      });

      setResults(combinedResults);
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
    if (!text) return ''; 
    return text.split(' ').slice(0, numWords).join(' ');
  };

  return (
    <div className="unified-search">
      <h2>Unified Search</h2>
      <div className="search-container">
        <input
          type="text"
          name="query"
          placeholder="Search..."
          value={searchParams.query}
          onChange={handleChange}
          className="search-input"
        />
        <button onClick={handleSearch} className="search-button">
          <span className="icon">🔍</span>
          <span className="text">Buscar</span>
        </button>
      </div>
      <div className="checkbox-section">
        <div className="checkbox-group">
          <h3>Dados dos pedidos</h3>
          <label>
            <input
              type="checkbox"
              name="searchByCodPedc"
              checked={searchParams.searchByCodPedc}
              onChange={handleChange}
            />
            Cod. PEDC
          </label>
          <label>
            <input
              type="checkbox"
              name="searchByFornecedor"
              checked={searchParams.searchByFornecedor}
              onChange={handleChange}
            />
            Fornecedor Descrição
          </label>
          <label>
            <input
              type="checkbox"
              name="searchByObservacao"
              checked={searchParams.searchByObservacao}
              onChange={handleChange}
            />
            Observação
          </label>
        </div>
        <div className="checkbox-group">
          <h3>Dados do item</h3>
          <label>
            <input
              type="checkbox"
              name="searchByDescricao"
              checked={searchParams.searchByDescricao}
              onChange={handleChange}
            />
            Descrição do Item
          </label>
          <label>
            <input
              type="checkbox"
              name="searchByItemId"
              checked={searchParams.searchByItemId}
              onChange={handleChange}
            />
            Item ID
          </label>
        </div>
        <div className="checkbox-group">
          <h3>Pesquisa avançada</h3>
          <label>
            <input
              type="checkbox"
              name="fuzzySearch"
              checked={searchParams.fuzzySearch}
              onChange={handleChange}
            />
            Pesquisa com erro de digitação
          </label>
          PORCENTAGEM DO ERRO DE DIGIGAÇÂO
        </div>
      </div>
      <table className="results-table">
        <thead>
          <tr>
            <th>Cod. PEDC</th>
            <th>Descrição</th>
            <th>Quantidade</th>
            <th>Preço Unitário</th>
            <th>Total</th>
            <th>Unidade Medida</th>
            <th>Data Emissão</th>
            <th>Cod. Fornecedor</th>
            <th>Fornecedor</th>
            <th>Observação</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <React.Fragment key={result.cod_pedc}>
              <tr>
                <td colSpan="10" className="order-header" align="center">
                  Pedido de Compra: {result.cod_pedc} ~ {getFirstWords(result.order ? result.order.fornecedor_descricao : result.fornecedor_descricao, 3)} - {formatCurrency(result.order ? result.order.total_bruto : result.total_bruto)}
                </td>
              </tr>
              {result.items ? (
                result.items.map((item) => (
                  <tr key={item.item_id} className={`item-row ${item.quantidade === item.qtde_atendida ? 'atendida' : 'nao-atendida'}`}>
                    <td>{result.cod_pedc}</td>
                    <td>{item.descricao}</td>
                    <td>{formatNumber(item.quantidade)}</td>
                    <td>{formatNumber(item.preco_unitario)}</td>
                    <td>{formatNumber(item.total)}</td>
                    <td>{item.unidade_medida}</td>
                    <td>{formatDate(result.dt_emis)}</td>
                    <td>{result.fornecedor_id}</td>
                    <td>{result.fornecedor_descricao}</td>
                    <td>{result.observacao}</td>
                  </tr>
                ))
              ) : (
                <tr key={result.item_id} className={`item-row ${result.quantidade === result.qtde_atendida ? 'atendida' : 'nao-atendida'}`}>
                  <td>{result.cod_pedc}</td>
                  <td>{result.descricao}</td>
                  <td>{formatNumber(result.quantidade)}</td>
                  <td>{formatNumber(result.preco_unitario)}</td>
                  <td>{formatNumber(result.total)}</td>
                  <td>{result.unidade_medida}</td>
                  <td>{formatDate(result.order ? result.order.dt_emis : '')}</td>
                  <td>{result.order ? result.order.fornecedor_id : ''}</td>
                  <td>{result.order ? result.order.fornecedor_descricao : ''}</td>
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