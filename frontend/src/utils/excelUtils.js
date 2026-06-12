import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';

/**
 * Generates and downloads an Excel file with quotation comparison data
 * @param {Object} extractedData - The extracted data containing items and supplier information
 */
export const generateQuotationExcel = (extractedData) => {
  try {
    const wb = XLSX.utils.book_new();
    
    // Create main comparison sheet with consolidated data
    addMainComparisonSheet(wb, extractedData);
    
    // Create individual supplier sheets
    addSupplierSheets(wb, extractedData);
    
    // Generate Excel file
    const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const data = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

    // Save file
    saveAs(data, `Comparacao_Cotacoes_${new Date().toISOString().slice(0, 10)}.xlsx`);
    
    return { success: true };
  } catch (err) {
    console.error('Error generating Excel:', err);
    return { 
      success: false, 
      error: err.message 
    };
  }
};

/**
 * Adds the main comparison sheet to the workbook
 * @param {Object} wb - The workbook
 * @param {Object} extractedData - The extracted data
 */
const addMainComparisonSheet = (wb, extractedData) => {
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

  // Create array from map and sort by description
  const sortedItems = Array.from(uniqueItems.values())
    .sort((a, b) => a.description.localeCompare(b.description));

  // Format data for the main comparison sheet
  const comparisonData = sortedItems.map(item => {
    // Find the best price (lowest non-zero price)
    const validPrices = item.supplier_prices
      .filter(sp => sp && sp.price > 0)
      .map(sp => sp.price);
    const bestPrice = validPrices.length > 0 ? Math.min(...validPrices) : null;
    
    // Get best price supplier index
    const bestPriceSupplierIndex = bestPrice ? 
      item.supplier_prices.findIndex(sp => sp && sp.price === bestPrice && sp.price > 0) : -1;
    
    // Create base row with item info
    const row = {
      'COD_ITEM': item.item_id || '—',
      'DESCRICAO': item.description,
      'QUANTIDADE': item.quantity || '—',
    };
    
    // Add a column for each supplier's price
    extractedData.extractedData.forEach((supplier, index) => {
      const supplierPrice = item.supplier_prices[index];
      row[`${supplier.supplier}`] = supplierPrice ? supplierPrice.price : '—';
    });
    
    // Calculate variation if we have last purchase and best price
    let variation = '—';
    if (bestPrice && item.last_purchase && item.last_purchase.price) {
      const lastPrice = item.last_purchase.price;
      variation = ((bestPrice - lastPrice) / lastPrice) * 100;
      variation = variation.toFixed(2) + '%';
    }
    
    // Get confidence of best match
    let confidence = '—';
    if (bestPriceSupplierIndex !== -1) {
      confidence = item.supplier_prices[bestPriceSupplierIndex].confidence || '—';
    }
    
    // Add additional columns
    row['MELHOR_PRECO'] = bestPrice || '—';
    row['VARIACAO'] = variation;
    row['CONFIANCA'] = confidence;
    
    return row;
  });

  // Create worksheet
  const ws = XLSX.utils.json_to_sheet(comparisonData);
  
  // Set column widths
  const wscols = [
    { wch: 12 }, // COD_ITEM
    { wch: 40 }, // DESCRICAO
    { wch: 12 }, // QUANTIDADE
    // Dynamic columns for suppliers - default width
    ...Array(extractedData.extractedData.length).fill({ wch: 15 }),
    { wch: 15 }, // MELHOR_PRECO
    { wch: 12 }, // VARIACAO
    { wch: 12 }, // CONFIANCA
  ];
  ws['!cols'] = wscols;

  // Add to workbook
  XLSX.utils.book_append_sheet(wb, ws, 'Comparativo');
};

/**
 * Adds individual supplier sheets to the workbook
 * @param {Object} wb - The workbook
 * @param {Object} extractedData - The extracted data
 */
const addSupplierSheets = (wb, extractedData) => {
  extractedData.extractedData.forEach(supplierData => {
    const supplierName = supplierData.supplier.substring(0, 30); // Truncate name if too long
    const supplierItems = supplierData.items.map(item => ({
      'Código': item.code || '—',
      'Descrição Original': item.description,
      'Quantidade': item.quantity || '—',
      'Unidade': item.unit || '—',
      'Preço Unitário': item.unitPrice || '—',
      'Preço Total': item.totalPrice || '—',
      'Fabricante': item.manufacturer || '—',
      'Item Correspondente': item.matchedItemDescription || '—',
      'Confiança da Correspondência': item.matchConfidence || '—',
      'Código do Item Correspondente': item.matchedItemCode || '—',
      'Variação de Preço (%)': item.priceDifferencePercent || '—',
      'Última Compra - Fornecedor': item.lastPurchase?.fornecedor || '—',
      'Última Compra - Preço': item.lastPurchase?.price || '—',
      'Última Compra - Data': item.lastPurchase?.date ? 
        new Date(item.lastPurchase.date).toLocaleDateString('pt-BR') : '—'
    }));

    // Create supplier-specific worksheet
    const supplierWs = XLSX.utils.json_to_sheet(supplierItems);
    
    // Set column widths
    const supplierWscols = [
      { wch: 12 }, // Código
      { wch: 40 }, // Descrição Original
      { wch: 12 }, // Quantidade
      { wch: 10 }, // Unidade
      { wch: 15 }, // Preço Unitário
      { wch: 15 }, // Preço Total
      { wch: 20 }, // Fabricante
      { wch: 40 }, // Item Correspondente
      { wch: 15 }, // Confiança da Correspondência
      { wch: 15 }, // Código do Item Correspondente
      { wch: 15 }, // Variação de Preço (%)
      { wch: 25 }, // Última Compra - Fornecedor
      { wch: 15 }, // Última Compra - Preço
      { wch: 15 }, // Última Compra - Data
    ];
    supplierWs['!cols'] = supplierWscols;
    
    // Add to workbook
    XLSX.utils.book_append_sheet(wb, supplierWs, supplierName);
  });
};

/**
 * Format currency for display
 * @param {number} value - The value to format
 * @returns {string} - Formatted currency string
 */
const formatCurrency = (value) => {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
};

/**
 * Generates and downloads an Excel file with the purchase report summary and monthly sheets
 * @param {Object} reportData - The purchase report data returned from the API
 */
export const generatePurchaseReportExcel = (reportData) => {
  try {
    const wb = XLSX.utils.book_new();

    const MONTH_NAMES = [
      "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
      "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
    ];

    const {
      category_names,
      data,
      category_totals,
      category_averages,
      month_totals,
      grand_total,
      user_name,
      year: rYear,
    } = reportData;

    // First tab: Summary & Chart Data
    const wsData = [];
    wsData.push([`RELATÓRIO DE COMPRAS ${rYear}`]);
    wsData.push([`Comprador: ${user_name}`]);
    wsData.push([]);
    wsData.push(["GÊNERO", ...MONTH_NAMES, "TOTAL", "MÉDIA MÊS"]);

    category_names.forEach((cat) => {
      wsData.push([
        cat,
        ...data[cat],
        category_totals[cat],
        category_averages[cat]
      ]);
    });

    wsData.push(["TOTAL", ...month_totals, grand_total, ""]);
    wsData.push([]);
    wsData.push(["GRÁFICO RELATÓRIO DE COMPRAS"]);
    wsData.push(["(Valores consolidados mensais)"]);
    wsData.push(["Mês", "Total de Compras"]);
    MONTH_NAMES.forEach((m, idx) => {
      wsData.push([m, month_totals[idx]]);
    });

    const ws = XLSX.utils.aoa_to_sheet(wsData);

    // Set column widths
    const wscols = [
      { wch: 22 }, // GÊNERO / Mês
      ...Array(12).fill({ wch: 14 }), // 12 months
      { wch: 16 }, // TOTAL
      { wch: 16 }  // MÉDIA MÊS
    ];
    ws['!cols'] = wscols;

    XLSX.utils.book_append_sheet(wb, ws, "Relatório");

    // Monthly tabs
    MONTH_NAMES.forEach((monthName, monthIdx) => {
      const monthOrders = (reportData.all_orders || []).filter(
        (o) => o.month_idx === monthIdx
      );

      // Format row values: COD_EMP1, PEDIDO, FORNECEDOR, DT. PED., VALOR, NF, DT. FAT., GENERO
      const sheetRows = monthOrders.map(o => ({
        "COD_EMP1": o.cod_emp1 || "",
        "PEDIDO": o.cod_pedc || "",
        "FORNECEDOR": o.fornecedor_descricao || "",
        "DT. PED.": o.dt_emis_br || "",
        "VALOR": o.total !== undefined ? o.total : "",
        "NF": o.nf || "",
        "DT. FAT.": o.dt_fat || "",
        "GENERO": o.matched_cat || ""
      }));

      const mWs = XLSX.utils.json_to_sheet(sheetRows);

      // Set column widths for month sheet
      mWs['!cols'] = [
        { wch: 12 }, // COD_EMP1
        { wch: 12 }, // PEDIDO
        { wch: 40 }, // FORNECEDOR
        { wch: 14 }, // DT. PED.
        { wch: 16 }, // VALOR
        { wch: 16 }, // NF
        { wch: 14 }, // DT. FAT.
        { wch: 22 }  // GENERO
      ];

      // Sheet name length limit in Excel is 31 chars
      const sheetName = monthName.substring(0, 30);
      XLSX.utils.book_append_sheet(wb, mWs, sheetName);
    });

    // Write workbook
    const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const fileBlob = new Blob([excelBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });

    saveAs(fileBlob, `relatorio_compras_${rYear}_${user_name}.xlsx`);
    return { success: true };
  } catch (err) {
    console.error("Error generating Purchase Report Excel:", err);
    return { success: false, error: err.message };
  }
};