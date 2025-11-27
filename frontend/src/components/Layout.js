import React, { useState } from "react";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Divider,
  Avatar,
  Tooltip,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  Dashboard as DashboardIcon,
  Search as SearchIcon,
  Compare as CompareIcon,
  Upload as UploadIcon,
  Logout as LogoutIcon,
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
  Settings as SettingsIcon,
  Key as KeyIcon,
} from "@mui/icons-material";

const DRAWER_WIDTH = 260;
const DRAWER_WIDTH_COLLAPSED = 72;

const Layout = ({ onLogout }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [mobileOpen, setMobileOpen] = useState(false);

  const drawerWidth = sidebarOpen ? DRAWER_WIDTH : DRAWER_WIDTH_COLLAPSED;

  const menuItems = [
    {
      text: "Dashboard",
      icon: <DashboardIcon />,
      path: "/dashboard",
      description: "Visão geral e métricas",
    },
    {
      text: "Pedidos",
      icon: <SearchIcon />,
      path: "/search",
      description: "Buscar pedidos de compra",
    },
    {
      text: "Cotações",
      icon: <CompareIcon />,
      path: "/quotation-analyzer",
      description: "Analisar cotações",
    },
    {
      text: "Importar",
      icon: <UploadIcon />,
      path: "/import",
      description: "Importar arquivos XML",
    },
  ];

  const bottomMenuItems = [
    {
      text: "Tokens",
      icon: <KeyIcon />,
      path: "/token-manager",
      description: "Gerenciar tokens de API",
    },
  ];

  const handleNavigate = (path) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const handleLogout = () => {
    onLogout?.();
    navigate("/login");
  };

  const isActive = (path) => location.pathname === path;

  const getPageTitle = () => {
    const allItems = [...menuItems, ...bottomMenuItems];
    const current = allItems.find((item) => item.path === location.pathname);
    return current?.text || "Sistema de Compras";
  };

  const drawerContent = (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        bgcolor: "#1a1f2e",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: sidebarOpen ? "space-between" : "center",
          p: 2,
          minHeight: 64,
        }}
      >
        {sidebarOpen && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Avatar
              sx={{
                bgcolor: "primary.main",
                width: 36,
                height: 36,
                fontSize: "1rem",
                fontWeight: 700,
              }}
            >
              SC
            </Avatar>
            <Box>
              <Typography
                variant="subtitle1"
                sx={{ color: "#fff", fontWeight: 600, lineHeight: 1.2 }}
              >
                Compras
              </Typography>
              <Typography
                variant="caption"
                sx={{ color: "rgba(255,255,255,0.5)", fontSize: "0.7rem" }}
              >
                Sistema de Gestão
              </Typography>
            </Box>
          </Box>
        )}
        <IconButton
          onClick={() => setSidebarOpen(!sidebarOpen)}
          sx={{
            color: "rgba(255,255,255,0.7)",
            "&:hover": { color: "#fff", bgcolor: "rgba(255,255,255,0.08)" },
          }}
        >
          {sidebarOpen ? <ChevronLeftIcon /> : <MenuIcon />}
        </IconButton>
      </Box>

      <Divider sx={{ borderColor: "rgba(255,255,255,0.08)" }} />

      {/* Main Navigation */}
      <List sx={{ px: 1.5, py: 2, flexGrow: 1 }}>
        {menuItems.map((item) => (
          <Tooltip
            key={item.path}
            title={!sidebarOpen ? item.text : ""}
            placement="right"
            arrow
          >
            <ListItemButton
              onClick={() => handleNavigate(item.path)}
              selected={isActive(item.path)}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                minHeight: 48,
                px: sidebarOpen ? 2 : 1.5,
                justifyContent: sidebarOpen ? "flex-start" : "center",
                color: "rgba(255,255,255,0.7)",
                "&:hover": {
                  bgcolor: "rgba(255,255,255,0.08)",
                  color: "#fff",
                },
                "&.Mui-selected": {
                  bgcolor: "primary.main",
                  color: "#fff",
                  "&:hover": {
                    bgcolor: "primary.dark",
                  },
                  "& .MuiListItemIcon-root": {
                    color: "#fff",
                  },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: sidebarOpen ? 2 : 0,
                  justifyContent: "center",
                  color: "inherit",
                }}
              >
                {item.icon}
              </ListItemIcon>
              {sidebarOpen && (
                <ListItemText
                  primary={item.text}
                  secondary={item.description}
                  primaryTypographyProps={{
                    fontSize: "0.9rem",
                    fontWeight: 500,
                  }}
                  secondaryTypographyProps={{
                    fontSize: "0.7rem",
                    color: "rgba(255,255,255,0.4)",
                    sx: { mt: 0.25 },
                  }}
                />
              )}
            </ListItemButton>
          </Tooltip>
        ))}
      </List>

      {/* Bottom Section */}
      <Box sx={{ px: 1.5, pb: 2 }}>
        <Divider sx={{ borderColor: "rgba(255,255,255,0.08)", mb: 2 }} />

        {bottomMenuItems.map((item) => (
          <Tooltip
            key={item.path}
            title={!sidebarOpen ? item.text : ""}
            placement="right"
            arrow
          >
            <ListItemButton
              onClick={() => handleNavigate(item.path)}
              selected={isActive(item.path)}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                minHeight: 44,
                px: sidebarOpen ? 2 : 1.5,
                justifyContent: sidebarOpen ? "flex-start" : "center",
                color: "rgba(255,255,255,0.7)",
                "&:hover": {
                  bgcolor: "rgba(255,255,255,0.08)",
                  color: "#fff",
                },
                "&.Mui-selected": {
                  bgcolor: "primary.main",
                  color: "#fff",
                  "&:hover": { bgcolor: "primary.dark" },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: sidebarOpen ? 2 : 0,
                  justifyContent: "center",
                  color: "inherit",
                }}
              >
                {item.icon}
              </ListItemIcon>
              {sidebarOpen && (
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{ fontSize: "0.875rem" }}
                />
              )}
            </ListItemButton>
          </Tooltip>
        ))}

        {/* Logout Button */}
        <Tooltip title={!sidebarOpen ? "Sair" : ""} placement="right" arrow>
          <ListItemButton
            onClick={handleLogout}
            sx={{
              borderRadius: 2,
              minHeight: 44,
              px: sidebarOpen ? 2 : 1.5,
              justifyContent: sidebarOpen ? "flex-start" : "center",
              color: "rgba(255,255,255,0.7)",
              "&:hover": {
                bgcolor: "rgba(244,67,54,0.15)",
                color: "#f44336",
                "& .MuiListItemIcon-root": {
                  color: "#f44336",
                },
              },
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 0,
                mr: sidebarOpen ? 2 : 0,
                justifyContent: "center",
                color: "inherit",
              }}
            >
              <LogoutIcon />
            </ListItemIcon>
            {sidebarOpen && (
              <ListItemText
                primary="Sair"
                primaryTypographyProps={{ fontSize: "0.875rem" }}
              />
            )}
          </ListItemButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "#f5f7fa" }}>
      {/* Mobile AppBar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          display: { md: "none" },
          bgcolor: "#fff",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Toolbar>
          <IconButton
            edge="start"
            onClick={() => setMobileOpen(true)}
            sx={{ mr: 2, color: "text.primary" }}
          >
            <MenuIcon />
          </IconButton>
          <Typography
            variant="h6"
            sx={{ color: "text.primary", fontWeight: 600 }}
          >
            {getPageTitle()}
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Mobile Drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
            border: "none",
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Desktop Drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          width: drawerWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: drawerWidth,
            boxSizing: "border-box",
            border: "none",
            transition: theme.transitions.create("width", {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.short,
            }),
          },
        }}
        open
      >
        {drawerContent}
      </Drawer>

      {/* Main Content */}
      <Box
        component="main"
        onClick={() => {
          if (sidebarOpen) {
            setSidebarOpen(false);
          }
        }}
        sx={{
          flexGrow: 1,
          minHeight: "100vh",
          transition: theme.transitions.create(["width", "margin"], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.short,
          }),
        }}
      >
        {/* Mobile spacer */}
        <Toolbar sx={{ display: { md: "none" } }} />

        {/* Page Content */}
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;
