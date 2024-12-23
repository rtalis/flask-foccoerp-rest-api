import React, { useState } from 'react';
import axios from 'axios';

const UnifiedSearch = () => {
  const [searchParams, setSearchParams] = useState({
    query: '',
    searchByCodPedc: false,
    searchByFornecedor: false,
    searchByObservacao: false,
    searchByDescricao: false,
    searchByItemId: false
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
      let response;
      if (searchParams.searchByCodPedc || searchParams.searchByFornecedor || searchParams.searchByObservacao) {
        response = await axios.get('http://localhost:5000/api/search_purchases', {
          params: {
            cod_pedc: searchParams.searchByCodPedc ? searchParams.query : '',
            fornecedor_descricao: searchParams.searchByFornecedor ? searchParams.query : '',
            observacao: searchParams.searchByObservacao ? searchParams.query : ''
          }
        });
      } else if (searchParams.searchByDescricao || searchParams.searchByItemId) {
        response = await axios.get('http://localhost:5000/api/search_items', {
          params: {
            descricao: searchParams.searchByDescricao ? searchParams.query : '',
            item_id: searchParams.searchByItemId ? searchParams.query : ''
          }
        });
      }
      const data = response.data;
      const detailedResults = await Promise.all(
        data.map(async (item) => {
          if (item.purchase_order_id) {
            const orderResponse = await axios.get('http://localhost:5000/api/get_purchase', {
              params: { cod_pedc: item.cod_pedc }
            });
            return { ...item, order: orderResponse.data[0] };
          } else if (item.items) {
            return item;
          }
          return item;
        })
      );
      setResults(detailedResults);
    } catch (error) {
      console.error('Error fetching data', error);
    }
  };

  return (
    <div>
      <h2>Unified Search</h2>
      <input
        type="text"
        name="query"
        placeholder="Search..."
        value={searchParams.query}
        onChange={handleChange}
      />
      <div>
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
      <button onClick={handleSearch}>Search</button>
      <table>
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
            result.items ? (
              result.items.map((item) => (
                <tr key={item.item_id}>
                  <td>{result.cod_pedc}</td>
                  <td>{item.descricao}</td>
                  <td>{item.quantidade}</td>
                  <td>{item.preco_unitario}</td>
                  <td>{item.total}</td>
                  <td>{item.unidade_medida}</td>
                  <td>{result.dt_emis}</td>
                  <td>{result.fornecedor_id}</td>
                  <td>{result.fornecedor_descricao}</td>
                  <td>{result.observacao}</td>
                </tr>
              ))
            ) : (
              <tr key={result.item_id}>
                <td>{result.cod_pedc}</td>
                <td>{result.descricao}</td>
                <td>{result.quantidade}</td>
                <td>{result.preco_unitario}</td>
                <td>{result.total}</td>
                <td>{result.unidade_medida}</td>
                <td>{result.order ? result.order.dt_emis : ''}</td>
                <td>{result.order ? result.order.fornecedor_id : ''}</td>
                <td>{result.order ? result.order.fornecedor_descricao : ''}</td>
                <td>{result.order ? result.order.observacao : ''}</td>
              </tr>
            )
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default UnifiedSearch;