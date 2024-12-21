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
      setResults(response.data);
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
            <th>Data</th>
            <th>Cod. Item</th>
            <th>Descrição do Item</th>
            <th>Cod. For</th>
            <th>Fornecedor</th>
            <th>Qnd.</th>
            <th>Preço Unitário</th>
            <th>Total Bruto</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            result.items ? (
              result.items.map((item) => (
                <tr key={item.item_id}>
                  <td>{result.dt_emis}</td>
                  <td>{item.item_id}</td>
                  <td>{item.descricao}</td>
                  <td>{result.fornecedor_id}</td>
                  <td>{result.fornecedor_descricao}</td>
                  <td>{item.quantidade}</td>
                  <td>{item.preco_unitario}</td>
                  <td>{item.total}</td>
                </tr>
              ))
            ) : (
              <tr key={result.item_id}>
                <td>{result.dt_entrega}</td>
                <td>{result.item_id}</td>
                <td>{result.descricao}</td>
                <td>{result.cod_pedc}</td>
                <td>{result.fornecedor_descricao}</td>
                <td>{result.quantidade}</td>
                <td>{result.preco_unitario}</td>
                <td>{result.total}</td>
              </tr>
            )
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default UnifiedSearch;