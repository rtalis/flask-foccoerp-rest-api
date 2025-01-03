import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Chart, LineController, LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip } from 'chart.js';
import './ItemScreen.css';

Chart.register(LineController, LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip);

const ItemScreen = ({ itemId, onClose }) => {
  const [itemDetails, setItemDetails] = useState(null);
  const [priceHistory, setPriceHistory] = useState([]);
  const chartRef = useRef(null);

  useEffect(() => {
    const fetchItemDetails = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/item_details/${itemId}`, { withCredentials: true });
        setItemDetails(response.data.item);
        setPriceHistory(response.data.priceHistory);
      } catch (error) {
        console.error('Error fetching item details', error);
      }
    };

    fetchItemDetails();
  }, [itemId]);

  useEffect(() => {
    if (priceHistory.length > 0 && chartRef.current) {
      const ctx = chartRef.current.getContext('2d');
      new Chart(ctx, {
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
                label: function(context) {
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
        </div>
      )}
    </div>
  );
};

export default ItemScreen;