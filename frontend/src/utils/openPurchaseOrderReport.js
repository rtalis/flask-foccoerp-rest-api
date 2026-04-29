export const openPurchaseOrderReport = ({ codPedc, codEmp1, apiUrl }) => {
  if (!codPedc) {
    throw new Error("codPedc is required");
  }

  const finalApiUrl = (apiUrl || "").replace(/\/$/, "");
  const params = new URLSearchParams({ cod_pedc: String(codPedc) });
  if (codEmp1) {
    params.set("cod_emp1", String(codEmp1));
  }
  if (finalApiUrl) {
    params.set("apiUrl", finalApiUrl);
  }

  const reportUrl = `/modelo_ped.htm?${params.toString()}`;
  const reportWindow = window.open(reportUrl, "_blank");

  if (!reportWindow) {
    throw new Error(
      "Pop-up bloqueado pelo navegador. Permita pop-ups para abrir o relatorio.",
    );
  }

  return reportWindow;
};
