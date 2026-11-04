import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState, addNotification } from '../store/uiSlice';
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
  Paper,
  Divider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Slider,
  Switch,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  CircularProgress,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Analytics as AnalyticsIcon,
  Settings as SettingsIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  CloudUpload as CloudUploadIcon,
  Science as ScienceIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

const MLMonitoring: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const [activeTab, setActiveTab] = useState(0);
  const [modelDialogOpen, setModelDialogOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // Mock data
  const models = [
    { id: 'knn_v1', name: 'KNN Classifier v1.2', type: 'knn', version: '1.2.0', status: 'active', accuracy: 0.68, precision: 0.72, recall: 0.65, f1: 0.68, lastTrained: '2026-11-01', trainingSamples: 15420, features: 17 },
    { id: 'rf_v1', name: 'Random Forest v1.0', type: 'random_forest', version: '1.0.0', status: 'candidate', accuracy: 0.71, precision: 0.74, recall: 0.69, f1: 0.71, lastTrained: '2026-11-03', trainingSamples: 15420, features: 17 },
    { id: 'regime_v1', name: 'Regime Classifier v1.1', type: 'regime_classifier', version: '1.1.0', status: 'active', accuracy: 0.78, precision: 0.81, recall: 0.75, f1: 0.78, lastTrained: '2026-10-28', trainingSamples: 12000, features: 12 },
  ];

  const predictions = Array.from({ length: 50 }, (_, i) => ({
    id: `pred_${i}`,
    timestamp: new Date(Date.now() - i * 300000),
    instrument: ['NIFTY', 'SENSEX'][Math.floor(Math.random() * 2)],
    predictedClass: [1, 2, 3][Math.floor(Math.random() * 3)],
    confidence: 0.5 + Math.random() * 0.5,
    probabilities: { 1: Math.random(), 2: Math.random(), 3: Math.random() },
    modelVersion: 'knn_v1',
  }));

  const classDistribution = { bullish: 42, bearish: 35, no_trade: 23 };

  return (
    <Box sx={{ maxWidth: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>ML Monitoring</Typography>
          <Typography variant="body2" color="text.secondary">Monitor model performance, predictions, and drift</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => {}}>Refresh</Button>
          <Button variant="outlined" startIcon={<CloudUploadIcon />} onClick={() => setModelDialogOpen(true)}>Register Model</Button>
          <Button variant="contained" startIcon={<ScienceIcon />} onClick={() => {}}>Retrain Active</Button>
        </Box>
      </Box>

      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v as number)} sx={{ mb: 3 }}>
        <Tab label="Models" icon={<ScienceIcon />} />
        <Tab label="Predictions" icon={<VisibilityIcon />} />
        <Tab label="Performance" icon={<AnalyticsIcon />} />
        <Tab label="Drift Monitor" icon={<SettingsIcon />} />
      </Tabs>

      {/* Models Tab */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          {models.map((model) => (
            <Grid item xs={12} lg={4} key={model.id}>
              <Card sx={{ borderLeft: `4px solid ${model.status === 'active' ? '#3fb950' : model.status === 'candidate' ? '#d29922' : '#8b949e'}` }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>{model.name}</Typography>
                      <Typography variant="caption" color="text.secondary">Type: {model.type.replace('_', ' ').toUpperCase()} • v{model.version}</Typography>
                    </Box>
                    <Chip
                      label={model.status.toUpperCase()}
                      size="small"
                      color={model.status === 'active' ? 'success' : model.status === 'candidate' ? 'warning' : 'default'}
                      variant="filled"
                    />
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5, mb: 2 }}>
                    <MetricBox label="Accuracy" value={`${(model.accuracy * 100).toFixed(1)}%`} />
                    <MetricBox label="Precision" value={`${(model.precision * 100).toFixed(1)}%`} />
                    <MetricBox label="Recall" value={`${(model.recall * 100).toFixed(1)}%`} />
                    <MetricBox label="F1 Score" value={`${(model.f1 * 100).toFixed(1)}%`} />
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2, fontSize: '0.75rem' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Last Trained</Typography>
                      <Typography>{format(new Date(model.lastTrained), 'MMM dd, yyyy')}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Training Samples</Typography>
                      <Typography>{model.trainingSamples.toLocaleString()}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography color="text.secondary">Features</Typography>
                      <Typography>{model.features}</Typography>
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <Button size="small" variant="outlined" onClick={() => { setSelectedModel(model); setDetailDialogOpen(true); }}>Details</Button>
                    {model.status !== 'active' && (
                      <Button size="small" variant="contained" color="primary" onClick={() => {}}>Promote to Active</Button>
                    )}
                    <Button size="small" variant="outlined" color="error" onClick={() => {}}>Archive</Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Predictions Tab */}
      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>Recent Predictions ({predictions.length})</Typography>
                  <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={() => {}}>Refresh</Button>
                </Box>
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Time</TableCell>
                        <TableCell>Instrument</TableCell>
                        <TableCell>Prediction</TableCell>
                        <TableCell>Confidence</TableCell>
                        <TableCell>Probabilities</TableCell>
                        <TableCell>Model</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {predictions.map((pred) => (
                        <TableRow key={pred.id}>
                          <TableCell>{format(pred.timestamp, 'HH:mm:ss')}</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>{pred.instrument}</TableCell>
                          <TableCell>
                            <Chip
                              label={pred.predictedClass === 1 ? 'BULLISH' : pred.predictedClass === 2 ? 'BEARISH' : 'NO TRADE'}
                              size="small"
                              color={pred.predictedClass === 1 ? 'success' : pred.predictedClass === 2 ? 'error' : 'default'}
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LinearProgress variant="determinate" value={pred.confidence * 100} sx={{ flex: 1, height: 6 }} />
                              <Typography variant="caption" sx={{ fontFamily: 'monospace', minWidth: 50 }}>{(pred.confidence * 100).toFixed(0)}%</Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 1, fontSize: '0.7rem' }}>
                              <Chip label={`B: ${(pred.probabilities[1]*100).toFixed(0)}%`} size="small" variant="outlined" color="success" />
                              <Chip label={`S: ${(pred.probabilities[2]*100).toFixed(0)}%`} size="small" variant="outlined" color="error" />
                              <Chip label={`N: ${(pred.probabilities[3]*100).toFixed(0)}%`} size="small" variant="outlined" color="default" />
                            </Box>
                          </TableCell>
                          <TableCell>{pred.modelVersion}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={4}>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Class Distribution (Last 100)</Typography>
                <Box sx={{ height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={Object.entries(classDistribution).map(([name, value]) => ({ name: name.replace('_', ' ').toUpperCase(), value }))}
                        cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                        paddingAngle={2} dataKey="value" nameKey="name"
                        label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {Object.entries(classDistribution).map((_, i) => (
                          <Cell key={`cell-${i}`} fill={i === 0 ? '#3fb950' : i === 1 ? '#f85149' : '#8b949e'} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Confidence Distribution</Typography>
                <Box sx={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={generateConfidenceDistribution()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                      <XAxis dataKey="range" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} />
                      <YAxis stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#00d4aa" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Performance Tab */}
      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Model Accuracy Over Time</Typography>
                <Box sx={{ height: 350 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={generateAccuracyHistory()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                      <XAxis dataKey="date" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} />
                      <YAxis stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} domain={[0.5, 1]} tickFormatter={val => `${(val*100).toFixed(0)}%`} />
                      <Tooltip />
                      <Line type="monotone" dataKey="knn" stroke="#00d4aa" strokeWidth={2} dot={false} name="KNN" />
                      <Line type="monotone" dataKey="rf" stroke="#d29922" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Random Forest" />
                      <Line type="monotone" dataKey="regime" stroke="#58a6ff" strokeWidth={2} dot={false} name="Regime Classifier" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Feature Importance (Random Forest)</Typography>
                <Box sx={{ height: 350 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={generateFeatureImportance()} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                      <XAxis type="number" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} />
                      <YAxis type="category" dataKey="feature" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} width={180} />
                      <Tooltip />
                      <Bar dataKey="importance" fill="#58a6ff" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Drift Monitor Tab */}
      {activeTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Data Drift Detection</Typography>
                <Alert severity="info" sx={{ mb: 2 }}>
                  No significant drift detected. All features within expected distributions.
                </Alert>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {['ema_9_20_distance', 'vwap_distance', 'rsi', 'macd_histogram', 'adx', 'relative_volume', 'atr_pct'].map((feature) => (
                    <DriftRow key={feature} feature={feature} />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Prediction Drift</Typography>
                <Box sx={{ height: 350 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={generateDriftHistory()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                      <XAxis dataKey="date" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} />
                      <YAxis stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} domain={[0, 1]} tickFormatter={val => `${(val*100).toFixed(0)}%`} />
                      <Tooltip />
                      <Line type="monotone" dataKey="psi" stroke="#f85149" strokeWidth={2} dot={false} name="PSI Score" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Model Dialog */}
      <Dialog open={modelDialogOpen} onClose={() => setModelDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Register New Model</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, p: 1 }}>
            <TextField fullWidth size="small" label="Model Name" placeholder="KNN Classifier v1.3" />
            <FormControl fullWidth size="small">
              <InputLabel>Model Type</InputLabel>
              <Select label="Model Type">
                <MenuItem value="knn">KNN Classifier</MenuItem>
                <MenuItem value="random_forest">Random Forest</MenuItem>
                <MenuItem value="regime_classifier">Regime Classifier</MenuItem>
              </Select>
            </FormControl>
            <TextField fullWidth size="small" label="Version" placeholder="1.3.0" />
            <TextField fullWidth size="small" label="Model File Path" placeholder="/models/knn_v1.3.joblib" />
            <TextField fullWidth size="small" label="Scaler File Path" placeholder="/models/scaler_v1.3.joblib" />
            <TextField fullWidth size="small" multiline rows={3} label="Config (JSON)" placeholder='{"n_neighbors": 15, "weights": "distance"}' />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModelDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="primary" onClick={() => setModelDialogOpen(false)}>Register</Button>
        </DialogActions>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{selectedModel?.name} - Details</DialogTitle>
        <DialogContent dividers>
          {selectedModel && (
            <Box sx={{ minWidth: 400, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                <DetailRow label="Type" value={selectedModel.type.replace('_', ' ').toUpperCase()} />
                <DetailRow label="Version" value={selectedModel.version} />
                <DetailRow label="Status" value={selectedModel.status.toUpperCase()} />
                <DetailRow label="Accuracy" value={`${(selectedModel.accuracy * 100).toFixed(1)}%`} />
                <DetailRow label="Precision" value={`${(selectedModel.precision * 100).toFixed(1)}%`} />
                <DetailRow label="Recall" value={`${(selectedModel.recall * 100).toFixed(1)}%`} />
                <DetailRow label="F1 Score" value={`${(selectedModel.f1 * 100).toFixed(1)}%`} />
                <DetailRow label="Last Trained" value={format(new Date(selectedModel.lastTrained), 'MMM dd, yyyy')} />
                <DetailRow label="Training Samples" value={selectedModel.trainingSamples.toLocaleString()} />
                <DetailRow label="Features" value={selectedModel.features} />
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

const MetricBox: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Box sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="h6" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>{value}</Typography>
  </Box>
);

const DetailRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Box sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 500 }}>{value}</Typography>
  </Box>
);

const DriftRow: React.FC<{ feature: string }> = ({ feature }) => {
  const psi = Math.random() * 0.15;
  const isAlert = psi > 0.1;
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{feature}</Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <LinearProgress variant="determinate" value={psi * 500} sx={{ width: 100, height: 6 }} color={isAlert ? 'error' : 'success'} />
        <Typography variant="caption" sx={{ fontFamily: 'monospace', minWidth: 50, color: isAlert ? 'error.main' : 'success.main' }}>{(psi * 100).toFixed(1)}%</Typography>
        {isAlert && <Chip label="ALERT" size="small" color="error" variant="outlined" />}
      </Box>
    </Box>
  );
};

const generateConfidenceDistribution = () => [
  { range: '0-10%', count: 2 },
  { range: '10-20%', count: 3 },
  { range: '20-30%', count: 5 },
  { range: '30-40%', count: 8 },
  { range: '40-50%', count: 12 },
  { range: '50-60%', count: 18 },
  { range: '60-70%', count: 22 },
  { range: '70-80%', count: 18 },
  { range: '80-90%', count: 10 },
  { range: '90-100%', count: 2 },
];

const generateAccuracyHistory = () => Array.from({ length: 30 }, (_, i) => ({
  date: format(new Date(Date.now() - (29-i)*24*60*60*1000), 'MM/dd'),
  knn: 0.62 + Math.random() * 0.1,
  rf: 0.65 + Math.random() * 0.1,
  regime: 0.72 + Math.random() * 0.08,
}));

const generateFeatureImportance = () => [
  { feature: 'vwap_distance', importance: 0.18 },
  { feature: 'ema_9_20_distance', importance: 0.15 },
  { feature: 'rsi', importance: 0.14 },
  { feature: 'macd_histogram', importance: 0.12 },
  { feature: 'adx', importance: 0.11 },
  { feature: 'relative_volume', importance: 0.10 },
  { feature: 'atr_pct', importance: 0.08 },
  { feature: 'ema_20_50_distance', importance: 0.07 },
  { feature: 'plus_di', importance: 0.05 },
];

const generateDriftHistory = () => Array.from({ length: 30 }, (_, i) => ({
  date: format(new Date(Date.now() - (29-i)*24*60*60*1000), 'MM/dd'),
  psi: Math.random() * 0.12,
}));

export default MLMonitoring;
