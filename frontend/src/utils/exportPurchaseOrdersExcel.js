import * as XLSX from "xlsx";
import { saveAs } from "file-saver";

/**
 * Generates and downloads an Excel file from purchase order search results
 * @param {Array} results - The purchase order search results
 */
export const exportPurchaseOrdersToExcel = (results) => {
  try {
    const wb = XLSX.utils.book_new();

    const orders = Array.isArray(results) ? results : [results];
    const flatRows = orders
      .map((order) => {
        return (order.items || []).map((item) => ({
          "Código Pedido": order.order.cod_pedc,
          "Data Emissão": order.order.dt_emis,
          Fornecedor: order.order.fornecedor_descricao,
          "Total Bruto": order.order.total_bruto,
          "Total Líquido": order.order.total_liquido,
          "Total Líquido IPI": order.order.total_liquido_ipi.replace(".", ","),
          Posição: order.order.posicao,
          Observação: order.order.observacao,
          Contato: order.order.contato,
          Funcionário: order.order.func_nome,
          "CF Pgto": order.order.cf_pgto,
          "Item ID": item.item_id,
          "Descrição Item": item.descricao,
          Quantidade: item.quantidade,
          "Preço Unitário": item.preco_unitario,
          "Total Item": item.total,
          "Unidade Medida": item.unidade_medida,
          "Data Entrega": item.dt_entrega,
          "Perc. IPI": item.perc_ipi,
          "Tot. Líquido IPI": item.tot_liquido_ipi,
          "Tot. Descontos": item.tot_descontos,
          "Tot. Acréscimos": item.tot_acrescimos,
          "Qtde Cancelada": item.qtde_canc,
          "Qtde Cancelada Tol.": item.qtde_canc_toler,
          "Qtde Atendida": item.qtde_atendida,
          "Qtde Saldo": item.qtde_saldo,
          "Perc. Tolerância": item.perc_toler,
          NFEs: (item.nfes || []).map((nfe) => nfe.num_nf).join(", "),
        }));
      })
      .flat();

    const ws = XLSX.utils.json_to_sheet(flatRows);
    XLSX.utils.book_append_sheet(wb, ws, "Pedidos de Compra");
    const excelBuffer = XLSX.write(wb, { bookType: "xlsx", type: "array" });
    const data = new Blob([excelBuffer], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    saveAs(
      data,
      `Pedidos_de_Compra_${new Date().toISOString().slice(0, 10)}.xlsx`
    );
    return { success: true };
  } catch (err) {
    console.error("Error exporting purchase orders to Excel:", err);
    return { success: false, error: err.message };
  }
};
