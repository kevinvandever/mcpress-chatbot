const { createProxyMiddleware } = require('http-proxy-middleware');
const express = require('express');

const app = express();
const PORT = 9000;

// Proxy API requests to backend
app.use('/api', createProxyMiddleware({
  target: 'http://localhost:8000',
  changeOrigin: true,
  pathRewrite: {
    '^/api': '', // Remove /api prefix when forwarding
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    res.status(500).json({ error: 'Backend connection failed' });
  }
}));

// Proxy all other requests to frontend
app.use('/', createProxyMiddleware({
  target: 'http://localhost:3001',
  changeOrigin: true,
  ws: true, // Enable websocket proxying
  onError: (err, req, res) => {
    console.error('Frontend proxy error:', err);
    res.status(500).send('Frontend connection failed');
  }
}));

app.listen(PORT, () => {
  console.log(`🔄 Proxy server running on http://localhost:${PORT}`);
  console.log('📡 Routing /api/* -> Backend (port 8000)');
  console.log('📱 Routing /* -> Frontend (port 3001)');
});