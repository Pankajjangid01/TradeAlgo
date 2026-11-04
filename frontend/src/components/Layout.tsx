import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { toggleSidebar, setActiveTab } from '../store/uiSlice';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Badge,
  Divider,
  Tooltip,
  Avatar,
  Menu,
  MenuItem,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  ShowChart as ShowChartIcon,
  Notifications as NotificationsIcon,
  AccountBalance as AccountBalanceIcon,
  Settings as SettingsIcon,
  Analytics as AnalyticsIcon,
  Security as SecurityIcon,
  History as HistoryIcon,
  Person as PersonIcon,
  ExitToApp as ExitToAppIcon,
  ChevronLeft,
  ChevronRight,
  Circle,
  FiberManualRecord,
} from '@mui/icons-material';
import { useTheme as useMuiTheme } from '@mui/material/styles';
import clsx from 'clsx';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: <DashboardIcon /> },
  { name: 'Market Analysis', href: '/market-analysis', icon: <ShowChartIcon /> },
  { name: 'Signal Center', href: '/signals', icon: <NotificationsIcon /> },
  { name: 'Trading Terminal', href: '/trading', icon: <AccountBalanceIcon /> },
  { name: 'Backtesting', href: '/backtesting', icon: <HistoryIcon /> },
  { name: 'ML Monitoring', href: '/ml-monitoring', icon: <AnalyticsIcon /> },
  { name: 'Risk Console', href: '/risk', icon: <SecurityIcon /> },
  { name: 'Audit Logs', href: '/audit', icon: <HistoryIcon /> },
  { name: 'Settings', href: '/settings', icon: <SettingsIcon /> },
];

const Layout: React.FC = () => {
  const theme = useMuiTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const dispatch = useDispatch<AppDispatch>();
  const location = useLocation();
  const { sidebarOpen } = useSelector((state: RootState) => state.ui);
  const isConnected = useSelector((state: RootState) => state.market.isConnected);
  const tradingMode = useSelector((state: RootState) => state.trading.tradingMode);
  const isTradingEnabled = useSelector((state: RootState) => state.trading.isTradingEnabled);
  const activeTab = useSelector((state: RootState) => state.ui.activeTab);
  
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleDrawerToggle = () => {
    if (isMobile) {
      setMobileOpen(!mobileOpen);
    } else {
      dispatch(toggleSidebar());
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
  };

  const drawerWidth = 260;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Mobile App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: 'background.paper',
          borderBottom: 1,
          borderColor: 'divider',
          zIndex: 1200,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, color: 'text.primary' }}>
            TradeIQ
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tooltip title={isConnected ? 'Connected' : 'Disconnected'}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  bgcolor: isConnected ? 'success.main' : 'error.main',
                  animation: isConnected ? 'pulse 2s infinite' : 'none',
                }}
              />
            </Tooltip>
            <Badge badgeContent={tradingMode === 'live' ? 'LIVE' : 'PAPER'} color={tradingMode === 'live' ? 'error' : 'success'} variant="dot">
              <Typography variant="caption" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
                {tradingMode}
              </Typography>
            </Badge>
            <IconButton onClick={handleMenuOpen}>
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                <PersonIcon fontSize="small" />
              </Avatar>
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Desktop Sidebar */}
      <Drawer
        variant="permanent"
        open={!isMobile && sidebarOpen}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
            borderRight: 1,
            borderColor: 'divider',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="h6" sx={{ color: 'text.primary', mb: 2 }}>
            TradeIQ
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <List>
            {navigation.map((item) => (
              <ListItem
                key={item.name}
                button
                component={NavLink}
                to={item.href}
                selected={location.pathname === item.href}
                sx={{
                  borderRadius: 1,
                  mb: 0.5,
                  color: 'text.secondary',
                  '&.Mui-selected': {
                    bgcolor: 'action.selected',
                    color: 'primary.main',
                    '&:hover': { bgcolor: 'action.hover' },
                    '& .MuiListItemIcon-root': { color: 'primary.main' },
                  },
                  '&:hover': { bgcolor: 'action.hover' },
                }}
                onClick={() => dispatch(setActiveTab(item.href))}
              >
                <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.name} />
              </ListItem>
            ))}
          </List>
          <Divider sx={{ my: 2 }} />
          <Box sx={{ px: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', mb: 1 }}>
              Status
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Circle sx={{ fontSize: 8, color: isConnected ? 'success.main' : 'error.main' }} />
              <Typography variant="caption" color="text.primary">
                {isConnected ? 'Data Feed Connected' : 'Data Feed Disconnected'}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FiberManualRecord sx={{ fontSize: 8, color: isTradingEnabled ? 'success.main' : 'warning.main' }} />
              <Typography variant="caption" color="text.primary">
                {isTradingEnabled ? 'Trading Enabled' : 'Trading Disabled'}
              </Typography>
            </Box>
          </Box>
        </Box>
      </Drawer>

      {/* Mobile Drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
          },
        }}
      >
        <Toolbar />
        <List>
          {navigation.map((item) => (
            <ListItem
              key={item.name}
              button
              component={NavLink}
              to={item.href}
              selected={location.pathname === item.href}
              sx={{
                borderRadius: 1,
                mb: 0.5,
                color: 'text.secondary',
                '&.Mui-selected': {
                  bgcolor: 'action.selected',
                  color: 'primary.main',
                  '& .MuiListItemIcon-root': { color: 'primary.main' },
                },
              }}
              onClick={() => {
                dispatch(setActiveTab(item.href));
                setMobileOpen(false);
              }}
            >
              <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.name} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* User Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem onClick={handleMenuClose}>
          <AccountBalanceIcon sx={{ mr: 1 }} fontSize="small" />
          Account
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <SettingsIcon sx={{ mr: 1 }} fontSize="small" />
          Settings
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ExitToAppIcon sx={{ mr: 1 }} fontSize="small" />
          Logout
        </MenuItem>
      </Menu>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          mt: '64px',
          bgcolor: 'background.default',
          minHeight: 'calc(100vh - 64px)',
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;