// filepath: /home/talison/dev/flask-rest-api/frontend/src/components/ItemScreen.js
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Chart, LineController, LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip } from 'chart.js';
import './ItemScreen.css';

Chart.register(LineController, LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip);

const ItemScreen = ({ itemId, onClose }) => {
  const [itemDetails, setItemDetails] = useState(null);
  const [priceHistory, setPriceHistory] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [showQuotations, setShowQuotations] = useState(false);
  const [searchType, setSearchType] = useState('item_id');
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);


  useEffect(() => {
    fetchItemDetails();
  }, [itemId, searchType]);

  const fetchItemDetails = async () => {
    try {
      let response;
      if (searchType === 'item_id') {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/item_details/${itemId}`, { withCredentials: true });
      } else if (searchType === 'fuzzy_95') {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_item_fuzzy`, {
          params: { descricao: itemDetails.descricao, score_cutoff: 95 },
          withCredentials: true
        });
      } else if (searchType === 'fuzzy_70') {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/search_item_fuzzy`, {
          params: { descricao: itemDetails.descricao, score_cutoff: 70 },
          withCredentials: true
        });
      }
      setItemDetails(response.data.item);
      setPriceHistory(response.data.priceHistory);
      setShowQuotations(false);

    } catch (error) {
      console.error('Error fetching item details', error);
    }
  };

  const fetchQuotations = async () => {
    try {
      let response;
      if (searchType === 'item_id') {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/quotations`, {
          params: { item_id: itemDetails.item_id },
          withCredentials: true
        });
      } else {
        response = await axios.get(`${process.env.REACT_APP_API_URL}/api/quotations_fuzzy`, {
          params: { descricao: itemDetails.descricao, score_cutoff: searchType === 'fuzzy_95' ? 95 : 70 },
          withCredentials: true
        });
      }
      const uniqueQuotations = {};
      response.data.forEach(quotation => {
        if (!uniqueQuotations[quotation.fornecedor_descricao]) {
          uniqueQuotations[quotation.fornecedor_descricao] = quotation;
        }
      });

      const sortedQuotations = Object.values(uniqueQuotations).sort((a, b) => a.fornecedor_descricao.localeCompare(b.fornecedor_descricao));
      setQuotations(sortedQuotations);
      setShowQuotations(true);
    } catch (error) {
      console.error('Error fetching quotations', error);
    }
  };

  useEffect(() => {
    if (priceHistory.length > 0 && chartRef.current) {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
      const ctx = chartRef.current.getContext('2d');
      chartInstanceRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels: priceHistory.map(entry => entry.date),
          datasets: [
            {
              label: 'Preço',
              data: priceHistory.map(entry => entry.price),
              fill: false,
              borderColor: 'blue',
              tension: 0.1
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            tooltip: {
              callbacks: {
                label: function (context) {
                  const entry = priceHistory[context.dataIndex];
                  return `Data: ${entry.date}, Preço: R$ ${entry.price}, Cod. Pedido: ${entry.cod_pedc}, Fornecedor: ${entry.fornecedor_descricao}`;
                }
              }
            }
          },
          scales: {
            x: {
              type: 'category',
              title: {
                display: true,
                text: 'Data'
              }
            },
            y: {
              title: {
                display: true,
                text: 'Preço'
              }
            }
          }
        }
      });
    }
  }, [priceHistory]);

  return (
    <div className="item-screen">
      <button className="close-button" onClick={onClose}>Fechar</button>
      <div>
        <label>
          <input
            type="radio"
            value="item_id"
            checked={searchType === 'item_id'}
            onChange={() => setSearchType('item_id')}
          />
          ID do Item
        </label>
        <label>
          <input
            type="radio"
            value="fuzzy_95"
            checked={searchType === 'fuzzy_95'}
            onChange={() => setSearchType('fuzzy_95')}
          />
          Nome do Item (95% similaridade)
        </label>
        <label>
          <input
            type="radio"
            value="fuzzy_70"
            checked={searchType === 'fuzzy_70'}
            onChange={() => setSearchType('fuzzy_70')}
          />
          Nome do Item (70% similaridade)
        </label>
      </div>
      {itemDetails && (
        <div>
          <h2>Detalhes do Item</h2>
          <p><strong>ID do Item:</strong> {itemDetails.item_id}</p>
          <p><strong>Descrição:</strong> {itemDetails.descricao}</p>
          <p><strong>Fornecedor:</strong> {itemDetails.fornecedor_descricao}</p>
          <p><strong>Quantidade:</strong> {itemDetails.quantidade}</p>
          <p><strong>Preço Unitário:</strong> R$ {itemDetails.preco_unitario}</p>
          <p><strong>Total:</strong> R$ {itemDetails.total}</p>

          <h3>Histórico de Preços</h3>
          <canvas ref={chartRef}></canvas>
          <button onClick={fetchQuotations}>Show Older Quotations</button>
        </div>
      )}
      {showQuotations && (
        <div>
          <h2>Older Quotations</h2>
          {quotations.length > 0 ? (
            <ul>
              {quotations.map((quotation) => (
                <li key={quotation.fornecedor_descricao}>
                  <p>{quotation.fornecedor_id.toString().padStart(6, ' ')} - {quotation.fornecedor_descricao}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p>No quotations found for this item.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ItemScreen;