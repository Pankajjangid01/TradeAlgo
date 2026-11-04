import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState, addNotification, setTheme } from '../store/uiSlice';
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
  Switch,
  Divider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Tooltip,
  Slider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  IconButton,
  InputAdornment,
} from '@mui/material';
import {
  Person as PersonIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  Cloud as CloudIcon,
  Storage as StorageIcon,
  MonitorHeart as MonitorHeartIcon,
  Save as SaveIcon,
  Edit as EditIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';

const Settings: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const theme = useSelector((state: RootState) => state.ui.theme);
  const tradingMode = useSelector((state: RootState) => state.trading.tradingMode);
  const selectedBroker = useSelector((state: RootState) => state.trading.selectedBroker);
  const isTradingEnabled = useSelector((state: RootState) => state.trading.isTradingEnabled);
  const [activeTab, setActiveTab] = useState(0);
  const [editing, setEditing] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Mock user data
  const [user, setUser] = useState({
    name: 'TradeIQ User',
    email: 'trader@tradeiq.com',
    role: 'Trader',
    twoFA: false,
    lastLogin: new Date(),
  });

  interface AngelOneConfig {
    apiKey: string;
    clientCode: string;
    password: string;
    totpSecret: string;
    connected: boolean;
  }

  interface FlattradeConfig {
    apiKey: string;
    apiSecret: string;
    clientId: string;
    redirectUrl: string;
    connected: boolean;
  }

  type BrokerConfig = AngelOneConfig | FlattradeConfig;

  const [brokerConfigs, setBrokerConfigs] = useState<Record<string, any>>({
    angelone: { apiKey: '', clientCode: '', password: '', totpSecret: '', connected: false },
    flattrade: { apiKey: '', apiSecret: '', clientId: '', redirectUrl: '', connected: false },
  });

  const [notifications, setNotifications] = useState({
    emailEnabled: true,
    pushEnabled: true,
    signalAlerts: true,
    orderAlerts: true,
    riskAlerts: true,
    dailySummary: true,
    errorAlerts: true,
  });

  const [system, setSystem] = useState({
    dataRetentionDays: 30,
    logLevel: 'INFO',
    autoRefreshInterval: 5000,
    maxConcurrentRequests: 10,
    enableDebugMode: false,
  });

  const handleSave = () => {
    dispatch(setTheme(theme));
    addNotification({ type: 'success', message: 'Settings saved successfully' });
    setEditing(false);
  };

  return (
    <Box sx={{ maxWidth: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>Settings</Typography>
          <Typography variant="body2" color="text.secondary">Configure your trading platform preferences</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => {}}>Reset to Defaults</Button>
          <Button variant={editing ? 'contained' : 'outlined'} onClick={() => setEditing(!editing)} startIcon={editing ? <SaveIcon /> : <EditIcon />}>
            {editing ? 'Save Changes' : 'Edit Settings'}
          </Button>
        </Box>
      </Box>

      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v as number)} sx={{ mb: 3 }} variant="scrollable">
        <Tab label="Profile" icon={<PersonIcon />} />
        <Tab label="Brokers" icon={<CloudIcon />} />
        <Tab label="Trading" icon={<SettingsIcon />} />
        <Tab label="Notifications" icon={<MonitorHeartIcon />} />
        <Tab label="System" icon={<StorageIcon />} />
        <Tab label="Security" icon={<SecurityIcon />} />
      </Tabs>

      {/* Profile Tab */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', mb: 3 }}>
                  <Avatar sx={{ width: 100, height: 100, bgcolor: 'primary.main', mb: 2 }}>
                    <PersonIcon fontSize="large" />
                  </Avatar>
                  <Typography variant="h5" sx={{ fontWeight: 600 }}>{user.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{user.email}</Typography>
                  <Chip label={user.role} size="small" color="primary" variant="outlined" />
                </Box>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Last Login</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>{format(user.lastLogin, 'MMM dd, yyyy HH:mm')}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">Two-Factor Auth</Typography>
                      <Typography variant="caption" color="text.secondary">Add an extra layer of security</Typography>
                    </Box>
                    <Switch checked={user.twoFA} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUser({...user, twoFA: e.target.checked})} disabled={!editing} />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Profile Information</Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Full Name" value={user.name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUser({...user, name: e.target.value})} disabled={!editing} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Email" value={user.email} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUser({...user, email: e.target.value})} disabled={!editing} type="email" />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Current Password" type={showPassword ? 'text' : 'password'} InputProps={{ endAdornment: <InputAdornment position="end"><IconButton onClick={() => setShowPassword(!showPassword)}><VisibilityIcon /></IconButton></InputAdornment> }} disabled={!editing} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="New Password" type={showPassword ? 'text' : 'password'} disabled={!editing} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Confirm New Password" type={showPassword ? 'text' : 'password'} disabled={!editing} />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Brokers Tab */}
      {activeTab === 1 && (
        <Grid container spacing={3}>
          {Object.entries(brokerConfigs).map(([key, config]) => (
            <Grid item xs={12} lg={6} key={key}>
              <Card sx={{ borderLeft: `4px solid ${config.connected ? '#3fb950' : '#8b949e'}` }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, textTransform: 'capitalize' }}>{key}</Typography>
                    <Chip label={config.connected ? 'CONNECTED' : 'DISCONNECTED'} size="small" color={config.connected ? 'success' : 'default'} variant="filled" />
                  </Box>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6}>
                      <TextField fullWidth size="small" label="API Key" type="password" value={config.apiKey} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBrokerConfigs({...brokerConfigs, [key]: {...config, apiKey: e.target.value}})} disabled={!editing} />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      {key === 'angelone' ? (
                        <TextField fullWidth size="small" label="Client Code" value={config.clientCode} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBrokerConfigs({...brokerConfigs, [key]: {...config, clientCode: e.target.value}})} disabled={!editing} />
                      ) : (
                        <TextField fullWidth size="small" label="API Secret" type="password" value={config.apiSecret} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBrokerConfigs({...brokerConfigs, [key]: {...config, apiSecret: e.target.value}})} disabled={!editing} />
                      )}
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      {key === 'angelone' ? (
                        <TextField fullWidth size="small" label="Password" type="password" value={config.password} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBrokerConfigs({...brokerConfigs, [key]: {...config, password: e.target.value}})} disabled={!editing} />
                      ) : (
                        <TextField fullWidth size="small" label="Client ID" value={config.clientId} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBrokerConfigs({...brokerConfigs, [key]: {...config, clientId: e.target.value}})} disabled={!editing} />
                      )}
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      {key === 'angelone' ? (
                        <TextField fullWidth size="small" label="TOTP Secret" type="password" value={config.totpSecret} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBrokerConfigs({...brokerConfigs, [key]: {...config, totpSecret: e.target.value}})} disabled={!editing} />
                      ) : (
                        <TextField fullWidth size="small" label="Redirect URL" value={config.redirectUrl} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setBrokerConfigs({...brokerConfigs, [key]: {...config, redirectUrl: e.target.value}})} disabled={!editing} />
                      )}
                    </Grid>
                  </Grid>
                  <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                    <Button variant={config.connected ? 'outlined' : 'contained'} color={config.connected ? 'warning' : 'primary'} onClick={() => {}} startIcon={config.connected ? <VisibilityOffIcon /> : <VisibilityIcon />}>
                      {config.connected ? 'Disconnect' : 'Connect'}
                    </Button>
                    <Button variant="outlined" color="primary" onClick={() => {}}>Test Connection</Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Trading Tab */}
      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Trading Configuration</Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small" disabled={!editing}>
                      <InputLabel>Trading Mode</InputLabel>
                      <Select value={tradingMode} label="Trading Mode" onChange={(e, value) => dispatch({ type: 'trading/setTradingMode', payload: value as string })}>
                        <MenuItem value="paper">Paper Trading</MenuItem>
                        <MenuItem value="live">Live Trading</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small" disabled={!editing}>
                      <InputLabel>Default Broker</InputLabel>
                      <Select value={selectedBroker} label="Default Broker" onChange={(e, value) => dispatch({ type: 'trading/setSelectedBroker', payload: value as string })}>
                        <MenuItem value="angelone">Angel One</MenuItem>
                        <MenuItem value="flattrade">Flattrade</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Switch checked={isTradingEnabled} onChange={(e: React.ChangeEvent<HTMLInputElement>) => dispatch({ type: 'trading/setTradingEnabled', payload: e.target.checked })} disabled={!editing} size="small" color="success" />
                    <Typography variant="body2" sx={{ ml: 1, color: 'text.secondary' }}>Trading Enabled</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Default Order Settings</Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Default Quantity" type="number" value={75} inputProps={{ min: 1, step: 75 }} disabled={!editing} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small" disabled={!editing}>
                      <InputLabel>Default Product Type</InputLabel>
                      <Select label="Product Type">
                        <MenuItem value="MIS">MIS (Intraday)</MenuItem>
                        <MenuItem value="NRML">NRML (Overnight)</MenuItem>
                        <MenuItem value="CNC">CNC (Delivery)</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small" disabled={!editing}>
                      <InputLabel>Default Validity</InputLabel>
                      <Select label="Validity">
                        <MenuItem value="DAY">DAY</MenuItem>
                        <MenuItem value="IOC">IOC</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Default Price (LIMIT)" type="number" value={0} inputProps={{ step: 0.05, min: 0 }} disabled={!editing} />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Notifications Tab */}
      {activeTab === 3 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Notification Preferences</Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <Switch checked={notifications.emailEnabled} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotifications({...notifications, emailEnabled: e.target.checked})} disabled={!editing} color="primary" />
                <Typography variant="body2" sx={{ ml: 1 }}>Email Notifications</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Switch checked={notifications.pushEnabled} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotifications({...notifications, pushEnabled: e.target.checked})} disabled={!editing} color="primary" />
                <Typography variant="body2" sx={{ ml: 1 }}>Push Notifications</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Switch checked={notifications.signalAlerts} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotifications({...notifications, signalAlerts: e.target.checked})} disabled={!editing} color="info" />
                <Typography variant="body2" sx={{ ml: 1 }}>Signal Alerts</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Switch checked={notifications.orderAlerts} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotifications({...notifications, orderAlerts: e.target.checked})} disabled={!editing} color="info" />
                <Typography variant="body2" sx={{ ml: 1 }}>Order Alerts</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Switch checked={notifications.riskAlerts} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotifications({...notifications, riskAlerts: e.target.checked})} disabled={!editing} color="warning" />
                <Typography variant="body2" sx={{ ml: 1 }}>Risk Alerts</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Switch checked={notifications.dailySummary} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotifications({...notifications, dailySummary: e.target.checked})} disabled={!editing} color="success" />
                <Typography variant="body2" sx={{ ml: 1 }}>Daily Summary</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Switch checked={notifications.errorAlerts} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNotifications({...notifications, errorAlerts: e.target.checked})} disabled={!editing} color="error" />
                <Typography variant="body2" sx={{ ml: 1 }}>Error Alerts</Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* System Tab */}
      {activeTab === 4 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>System Configuration</Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Data Retention (Days)" type="number" value={system.dataRetentionDays} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSystem({...system, dataRetentionDays: parseInt(e.target.value)})} inputProps={{ min: 1, max: 365 }} disabled={!editing} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth size="small" disabled={!editing}>
                      <InputLabel>Log Level</InputLabel>
                      <Select value={system.logLevel} label="Log Level" onChange={(e, value) => setSystem({...system, logLevel: value as string})}>
                        <MenuItem value="DEBUG">DEBUG</MenuItem>
                        <MenuItem value="INFO">INFO</MenuItem>
                        <MenuItem value="WARNING">WARNING</MenuItem>
                        <MenuItem value="ERROR">ERROR</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Auto Refresh Interval (ms)" type="number" value={system.autoRefreshInterval} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSystem({...system, autoRefreshInterval: parseInt(e.target.value)})} inputProps={{ min: 1000, max: 60000, step: 1000 }} disabled={!editing} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField fullWidth size="small" label="Max Concurrent Requests" type="number" value={system.maxConcurrentRequests} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSystem({...system, maxConcurrentRequests: parseInt(e.target.value)})} inputProps={{ min: 1, max: 50 }} disabled={!editing} />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Switch checked={system.enableDebugMode} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSystem({...system, enableDebugMode: e.target.checked})} disabled={!editing} color="warning" />
                    <Typography variant="body2" sx={{ ml: 1 }}>Enable Debug Mode</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Data Management</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Export Configuration</Typography>
                      <Typography variant="caption" color="text.secondary">Download current settings as JSON</Typography>
                    </Box>
                    <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => {}}>Export</Button>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Import Configuration</Typography>
                      <Typography variant="caption" color="text.secondary">Upload settings from JSON file</Typography>
                    </Box>
                    <Button variant="outlined" startIcon={<UploadIcon />} onClick={() => {}}>Import</Button>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'error.main' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500, color: 'error.main' }}>Reset to Defaults</Typography>
                      <Typography variant="caption" color="text.secondary">Restore all settings to factory defaults</Typography>
                    </Box>
                    <Button variant="outlined" color="error" startIcon={<DeleteIcon />} onClick={() => {}}>Reset</Button>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Security Tab */}
      {activeTab === 5 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>API Security</Typography>
                <Alert severity="info">
                  API credentials are encrypted at rest. Never share your API keys or TOTP secrets.
                </Alert>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Credential Encryption</Typography>
                      <Typography variant="caption" color="text.secondary">AES-256 encryption for stored credentials</Typography>
                    </Box>
                    <Chip label="ENABLED" size="small" color="success" variant="filled" />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>HTTPS Enforcement</Typography>
                      <Typography variant="caption" color="text.secondary">All API communications over TLS 1.2+</Typography>
                    </Box>
                    <Chip label="ENABLED" size="small" color="success" variant="filled" />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Rate Limiting</Typography>
                      <Typography variant="caption" color="text.secondary">API rate limits enforced per endpoint</Typography>
                    </Box>
                    <Chip label="ENABLED" size="small" color="success" variant="filled" />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Session Management</Typography>
                      <Typography variant="caption" color="text.secondary">JWT tokens with automatic refresh</Typography>
                    </Box>
                    <Chip label="ENABLED" size="small" color="success" variant="filled" />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Audit & Compliance</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Audit Logging</Typography>
                      <Typography variant="caption" color="text.secondary">All critical actions logged immutably</Typography>
                    </Box>
                    <Chip label="ENABLED" size="small" color="success" variant="filled" />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Data Retention Policy</Typography>
                      <Typography variant="caption" color="text.secondary">{system.dataRetentionDays} days for audit logs</Typography>
                    </Box>
                    <Chip label="CONFIGURED" size="small" color="info" variant="filled" />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>Access Control</Typography>
                      <Typography variant="caption" color="text.secondary">Role-based permissions (Admin/Trader)</Typography>
                    </Box>
                    <Chip label="ENABLED" size="small" color="success" variant="filled" />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default Settings;
