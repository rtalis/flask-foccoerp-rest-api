import * as XLSX from "xlsx";
import { saveAs } from "file-saver";

/**
 * Generates and downloads an Excel file from purchase order search results
 * @param {Array} results - The purchase order search results
 * @param {Object} options - Options containing permissions (canViewFinancials, canViewNfes)
 */
export const exportPurchaseOrdersToExcel = (results, options = {}) => {
  const { canViewFinancials = true, canViewNfes = true } = options;
  try {
    const wb = XLSX.utils.book_new();

    const orders = Array.isArray(results) ? results : [results];
    const flatRows = orders
      .map((order) => {
        return (order.items || []).map((item) => {
          const row = {
            "Código Pedido": order.order.cod_pedc,
            "Data Emissão": order.order.dt_emis,
            Fornecedor: order.order.fornecedor_descricao,
          };
          if (canViewFinancials) {
            row["Total Bruto"] = order.order.total_bruto;
            row["Total Líquido"] = order.order.total_liquido;
            row["Total Líquido IPI"] = order.order.total_liquido_ipi;
          }
          row["Posição"] = order.order.posicao;
          row["Observação"] = order.order.observacao;
          row["Contato"] = order.order.contato;
          row["Funcionário"] = order.order.func_nome;
          
          if (canViewFinancials) {
            row["CF Pgto"] = order.order.cf_pgto;
          }

          row["Item ID"] = item.item_id;
          row["Descrição Item"] = item.descricao;
          row["Quantidade"] = item.quantidade;

          if (canViewFinancials) {
            row["Preço Unitário"] = item.preco_unitario;
            row["Total Item"] = item.total;
          }

          row["Unidade Medida"] = item.unidade_medida;
          row["Data Entrega"] = item.dt_entrega;

          if (canViewFinancials) {
            row["Perc. IPI"] = item.perc_ipi;
            row["Tot. Líquido IPI"] = item.tot_liquido_ipi;
            row["Tot. Descontos"] = item.tot_descontos;
            row["Tot. Acréscimos"] = item.tot_acrescimos;
          }

          row["Qtde Cancelada"] = item.qtde_canc;
          row["Qtde Cancelada Tol."] = item.qtde_canc_toler;
          row["Qtde Atendida"] = item.qtde_atendida;
          row["Qtde Saldo"] = item.qtde_saldo;
          row["Perc. Tolerância"] = item.perc_toler;

          if (canViewNfes) {
            row["NFEs"] = (item.nfes || []).map((nfe) => nfe.num_nf).join(", ");
          }

          return row;
        });
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
