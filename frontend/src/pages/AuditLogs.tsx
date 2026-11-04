import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState, addNotification, setDateRange } from '../store/uiSlice';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  Divider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Tooltip,
  Badge,
  InputAdornment,
  IconButton,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  FilterList as FilterListIcon,
  Download as DownloadIcon,
  Visibility as VisibilityIcon,
  Delete as DeleteIcon,
  CalendarToday as CalendarTodayIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  ShoppingCart as ShoppingCartIcon,
  AccountBalance as AccountBalanceIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
  Science as ScienceIcon,
  Settings as SettingsIcon,
  Person as PersonIcon,
  Cloud as CloudIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { format, parseISO, startOfDay, endOfDay, subDays } from 'date-fns';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

const AuditLogs: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const [activeTab, setActiveTab] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [filters, setFilters] = useState({
    action: '',
    entityType: '',
    entityId: '',
    startDate: format(subDays(new Date(), 7), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd'),
    userId: '',
  });
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<any>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Mock data
  const [logs, setLogs] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    loadLogs();
  }, [page, rowsPerPage, filters]);

  const loadLogs = async () => {
    dispatch(setLoadingState({ key: 'audit', loading: true }));
    try {
      await new Promise(resolve => setTimeout(resolve, 300));
      const mockLogs = generateMockLogs();
      setLogs(mockLogs.slice(page * rowsPerPage, (page + 1) * rowsPerPage));
      setTotalCount(mockLogs.length);
    } catch (error) {
      console.error('Failed to load audit logs:', error);
    } finally {
      dispatch(setLoadingState({ key: 'audit', loading: false }));
    }
  };

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(0);
  };

  const handleDateChange = (key: string, date: Date | null) => {
    if (date) {
      handleFilterChange(key, format(date, 'yyyy-MM-dd'));
    }
  };

  const handleRowClick = (log: any) => {
    setSelectedLog(log);
    setDetailOpen(true);
  };

  const handleExpand = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const getActionColor = (action: string) => {
    const colors: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
      'order_placed': 'info',
      'order_filled': 'success',
      'order_cancelled': 'warning',
      'order_rejected': 'error',
      'position_opened': 'success',
      'position_closed': 'info',
      'stop_loss_hit': 'error',
      'target_hit': 'success',
      'kill_switch_activated': 'error',
      'kill_switch_deactivated': 'success',
      'risk_limit_breached': 'error',
      'signal_generated': 'info',
      'signal_approved': 'success',
      'signal_rejected': 'warning',
      'model_registered': 'info',
      'model_promoted': 'success',
      'config_changed': 'warning',
      'user_login': 'info',
      'user_logout': 'default',
      'broker_connected': 'success',
      'broker_disconnected': 'error',
      'data_feed_lost': 'error',
      'data_feed_restored': 'success',
    };
    return colors[action] || 'default';
  };

  const getActionIcon = (action: string) => {
    if (action.includes('order')) return <ShoppingCartIcon fontSize="small" />;
    if (action.includes('position')) return <AccountBalanceIcon fontSize="small" />;
    if (action.includes('signal')) return <NotificationsIcon fontSize="small" />;
    if (action.includes('risk') || action.includes('kill')) return <SecurityIcon fontSize="small" />;
    if (action.includes('model')) return <ScienceIcon fontSize="small" />;
    if (action.includes('config')) return <SettingsIcon fontSize="small" />;
    if (action.includes('user') || action.includes('login') || action.includes('logout')) return <PersonIcon fontSize="small" />;
    if (action.includes('broker') || action.includes('data_feed')) return <CloudIcon fontSize="small" />;
    return <InfoIcon fontSize="small" />;
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{ maxWidth: '100%' }}>
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 600 }}>Audit Logs</Typography>
            <Typography variant="body2" color="text.secondary">System activity and trading audit trail</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadLogs}>Refresh</Button>
            <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => {}}>Export CSV</Button>
          </Box>
        </Box>

        {/* Filters */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Grid container spacing={3} alignItems="flex-end">
              <Grid item xs={12} sm={4}>
                <FormControl fullWidth size="small">
                  <InputLabel>Action</InputLabel>
                  <Select value={filters.action} label="Action" onChange={(e) => handleFilterChange('action', e.target.value)}>
                    <MenuItem value="">All Actions</MenuItem>
                    <MenuItem value="order_placed">Order Placed</MenuItem>
                    <MenuItem value="order_filled">Order Filled</MenuItem>
                    <MenuItem value="order_cancelled">Order Cancelled</MenuItem>
                    <MenuItem value="order_rejected">Order Rejected</MenuItem>
                    <MenuItem value="position_opened">Position Opened</MenuItem>
                    <MenuItem value="position_closed">Position Closed</MenuItem>
                    <MenuItem value="stop_loss_hit">Stop Loss Hit</MenuItem>
                    <MenuItem value="target_hit">Target Hit</MenuItem>
                    <MenuItem value="kill_switch_activated">Kill Switch Activated</MenuItem>
                    <MenuItem value="signal_generated">Signal Generated</MenuItem>
                    <MenuItem value="signal_approved">Signal Approved</MenuItem>
                    <MenuItem value="signal_rejected">Signal Rejected</MenuItem>
                    <MenuItem value="model_registered">Model Registered</MenuItem>
                    <MenuItem value="config_changed">Config Changed</MenuItem>
                    <MenuItem value="user_login">User Login</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Entity Type</InputLabel>
                  <Select value={filters.entityType} label="Entity Type" onChange={(e) => handleFilterChange('entityType', e.target.value)}>
                    <MenuItem value="">All Types</MenuItem>
                    <MenuItem value="order">Order</MenuItem>
                    <MenuItem value="position">Position</MenuItem>
                    <MenuItem value="signal">Signal</MenuItem>
                    <MenuItem value="trade">Trade</MenuItem>
                    <MenuItem value="model">Model</MenuItem>
                    <MenuItem value="user">User</MenuItem>
                    <MenuItem value="system">System</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="Entity ID"
                  value={filters.entityId}
                  onChange={(e) => handleFilterChange('entityId', e.target.value)}
                  placeholder="Filter by ID"
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="User ID"
                  value={filters.userId}
                  onChange={(e) => handleFilterChange('userId', e.target.value)}
                  placeholder="Filter by User"
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="Start Date"
                  type="date"
                  value={filters.startDate}
                  onChange={(e) => handleFilterChange('startDate', e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="End Date"
                  type="date"
                  value={filters.endDate}
                  onChange={(e) => handleFilterChange('endDate', e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button variant="outlined" onClick={() => setFilters({ action: '', entityType: '', entityId: '', startDate: format(subDays(new Date(), 7), 'yyyy-MM-dd'), endDate: format(new Date(), 'yyyy-MM-dd'), userId: '' })}>Clear Filters</Button>
                  <Chip label={`${logs.length} results`} size="small" color="info" variant="outlined" />
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Logs Table */}
        <Card>
          <CardContent>
            <TableContainer sx={{ maxHeight: 600 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell style={{ width: 40 }} />
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Entity</TableCell>
                    <TableCell>Entity ID</TableCell>
                    <TableCell>User</TableCell>
                    <TableCell>IP Address</TableCell>
                    <TableCell>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {logs.map((log) => (
                    <>
                    <TableRow key={log.id} hover onClick={() => handleRowClick(log)}>
                      <TableCell>
                        <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleExpand(log.id); }}>
                          {expandedRow === log.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                        {format(new Date(log.createdAt), 'MMM dd, HH:mm:ss')}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={log.action.replace('_', ' ').toUpperCase()}
                          size="small"
                          color={getActionColor(log.action)}
                          variant="outlined"
                          icon={getActionIcon(log.action)}
                        />
                      </TableCell>
                      <TableCell>{log.entityType}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{log.entityId}</TableCell>
                      <TableCell>{log.userId || 'System'}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{log.ipAddress || '-'}</TableCell>
                      <TableCell>
                        <Tooltip title={JSON.stringify(log.newValues || {}, null, 2)}>
                          <span>{log.oldValues || log.newValues ? 'View Changes' : '-'}</span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                    {expandedRow === log.id && (
                      <TableRow>
                        <TableCell colSpan={8} sx={{ padding: 0 }}>
                          <Box sx={{ p: 2, bgcolor: 'background.default', borderTop: '1px solid', borderColor: 'divider' }}>
                            <Typography variant="caption" color="text.secondary" gutterBottom>Old Values</Typography>
                            <Box sx={{ fontSize: '0.7rem', fontFamily: 'monospace', bgcolor: '#0d1117', p: 2, borderRadius: 1, overflow: 'auto', maxHeight: 200 }}>
                              {JSON.stringify(log.oldValues || {}, null, 2)}
                            </Box>
                            <Typography variant="caption" color="text.secondary" gutterBottom sx={{ mt: 2 }}>New Values</Typography>
                            <Box sx={{ fontSize: '0.7rem', fontFamily: 'monospace', bgcolor: '#0d1117', p: 2, borderRadius: 1, overflow: 'auto', maxHeight: 200 }}>
                              {JSON.stringify(log.newValues || {}, null, 2)}
                            </Box>
                          </Box>
                        </TableCell>
                      </TableRow>
                    )}
                    </>
                  ))}
                  {logs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                        No audit logs found matching filters
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              rowsPerPageOptions={[10, 25, 50, 100]}
              component="div"
              count={totalCount}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
            />
          </CardContent>
        </Card>

        {/* Detail Dialog */}
        <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="lg" fullWidth>
          <DialogTitle>{selectedLog?.action?.replace('_', ' ').toUpperCase()} - Details</DialogTitle>
          <DialogContent dividers>
            {selectedLog && (
              <Box sx={{ minWidth: 600, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <DetailField label="Timestamp" value={format(new Date(selectedLog.createdAt), 'yyyy-MM-dd HH:mm:ss')} />
                  </Grid>
                  <Grid item xs={6}>
                    <DetailField label="Action" value={selectedLog.action.replace('_', ' ').toUpperCase()} />
                  </Grid>
                  <Grid item xs={6}>
                    <DetailField label="Entity Type" value={selectedLog.entityType} />
                  </Grid>
                  <Grid item xs={6}>
                    <DetailField label="Entity ID" value={selectedLog.entityId} />
                  </Grid>
                  <Grid item xs={6}>
                    <DetailField label="User ID" value={selectedLog.userId || 'System'} />
                  </Grid>
                  <Grid item xs={6}>
                    <DetailField label="IP Address" value={selectedLog.ipAddress || 'N/A'} />
                  </Grid>
                  <Grid item xs={6}>
                    <DetailField label="User Agent" value={selectedLog.userAgent ? 'Available' : 'N/A'} />
                  </Grid>
                </Grid>

                {selectedLog.oldValues && Object.keys(selectedLog.oldValues).length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>Old Values</Typography>
                    <Box sx={{ fontSize: '0.75rem', fontFamily: 'monospace', bgcolor: '#0d1117', p: 2, borderRadius: 1, overflow: 'auto', maxHeight: 300 }}>
                      {JSON.stringify(selectedLog.oldValues, null, 2)}
                    </Box>
                  </Box>
                )}

                {selectedLog.newValues && Object.keys(selectedLog.newValues).length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>New Values</Typography>
                    <Box sx={{ fontSize: '0.75rem', fontFamily: 'monospace', bgcolor: '#0d1117', p: 2, borderRadius: 1, overflow: 'auto', maxHeight: 300 }}>
                      {JSON.stringify(selectedLog.newValues, null, 2)}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDetailOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};

const DetailField: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Box sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{value}</Typography>
  </Box>
);

const generateMockLogs = () => {
  const actions = [
    'order_placed', 'order_filled', 'order_cancelled', 'order_rejected',
    'position_opened', 'position_closed', 'stop_loss_hit', 'target_hit',
    'signal_generated', 'signal_approved', 'signal_rejected',
    'kill_switch_activated', 'risk_limit_breached', 'config_changed',
    'user_login', 'broker_connected', 'data_feed_lost'
  ];
  const entities = ['order', 'position', 'signal', 'trade', 'model', 'user', 'system'];
  const users = ['admin', 'trader1', 'system', 'risk_mgr'];

  return Array.from({ length: 500 }, (_, i) => ({
    id: `log_${i}`,
    createdAt: new Date(Date.now() - i * 60000 * Math.random() * 10),
    action: actions[Math.floor(Math.random() * actions.length)],
    entityType: entities[Math.floor(Math.random() * entities.length)],
    entityId: `ENT_${Math.floor(Math.random() * 10000)}`,
    userId: users[Math.floor(Math.random() * users.length)],
    ipAddress: `192.168.1.${Math.floor(Math.random() * 255)}`,
    userAgent: 'Mozilla/5.0...',
    oldValues: Math.random() > 0.5 ? { status: 'pending', quantity: 75 } : {},
    newValues: Math.random() > 0.5 ? { status: 'filled', quantity: 75, price: 19850.25 } : {},
  }));
};

export default AuditLogs;
