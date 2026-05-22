import React from "react";
import { Box, Typography, Paper, Container } from "@mui/material";
import {
  Assessment as AssessmentIcon,
} from "@mui/icons-material";

const PurchaseReport = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          component="h1"
          sx={{
            fontWeight: 700,
            color: "#1a1f2e",
            mb: 1,
          }}
        >
          Relatório de Pedidos de Compra
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: "rgba(26, 31, 46, 0.6)",
          }}
        >
          Análise e visualização de pedidos de compra
        </Typography>
      </Box>

      <Paper
        sx={{
          p: 4,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 400,
          bgcolor: "#f5f7fa",
          border: "2px dashed rgba(26, 31, 46, 0.1)",
          borderRadius: 2,
        }}
      >
        <AssessmentIcon
          sx={{
            fontSize: 64,
            color: "rgba(26, 31, 46, 0.2)",
            mb: 2,
          }}
        />
        <Typography
          variant="h6"
          sx={{
            color: "rgba(26, 31, 46, 0.6)",
            textAlign: "center",
            mb: 1,
          }}
        >
          Relatório em desenvolvimento
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: "rgba(26, 31, 46, 0.5)",
            textAlign: "center",
          }}
        >
          Este relatório está sendo desenvolvido. Em breve, você poderá visualizar e analisar dados de pedidos de compra aqui.
        </Typography>
      </Paper>
    </Container>
  );
};

export default PurchaseReport;
