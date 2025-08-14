const mediasoup = require('mediasoup');
const os = require('os');

// Helper function to get server's local IP address
function getServerIP() {
  const interfaces = os.networkInterfaces();
  
  // Look for the first non-internal IPv4 address
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      // Skip internal (loopback) and non-IPv4 addresses
      if (iface.family === 'IPv4' && !iface.internal) {
        console.log(`🔍 Auto-detected server IP: ${iface.address}`);
        return iface.address;
      }
    }
  }
  
  // Fallback to localhost if no external IP found (development)
  console.warn('⚠️ Could not auto-detect server IP, using localhost. This will only work for local testing!');
  return '127.0.0.1';
}

const mediaCodecs = [
  {
    kind: 'audio',
    mimeType: 'audio/opus',
    clockRate: 48000,
    channels: 2,
  },
  {
    kind: 'video',
    mimeType: 'video/VP8',
    clockRate: 90000,
    parameters: {
      'x-google-start-bitrate': 1000,
    },
  },
  {
    kind: 'video',
    mimeType: 'video/VP9',
    clockRate: 90000,
    parameters: {
      'profile-id': 2,
      'x-google-start-bitrate': 1000,
    },
  },
  {
    kind: 'video',
    mimeType: 'video/h264',
    clockRate: 90000,
    parameters: {
      'packetization-mode': 1,
      'profile-level-id': '4d0032',
      'level-asymmetry-allowed': 1,
      'x-google-start-bitrate': 1000,
    },
  },
  {
    kind: 'video',
    mimeType: 'video/h264',
    clockRate: 90000,
    parameters: {
      'packetization-mode': 1,
      'profile-level-id': '42e01f',
      'level-asymmetry-allowed': 1,
      'x-google-start-bitrate': 1000,
    },
  },
];

const webRtcTransportOptions = {
  listenIps: [
    {
      ip: process.env.WEBRTC_LISTEN_IP || '0.0.0.0',
      announcedIp: getServerIP(),
    },
  ],
  enableUdp: true,
  enableTcp: true,
  preferUdp: true,
  portRange: {
    min: parseInt(process.env.RTC_MIN_PORT) || 40000,
    max: parseInt(process.env.RTC_MAX_PORT) || 49999,
  },
  // Add additional WebRTC options for better connectivity
  maxIncomingBitrate: 1500000,
  maxOutgoingBitrate: 600000,
  initialAvailableOutgoingBitrate: 300000,
  // Add ICE server configurations for NAT traversal
  iceServers: [
    {
      urls: ['stun:stun.l.google.com:19302'],
    },
    {
      urls: ['stun:global.stun.twilio.com:3478'],
    }
  ],
  iceTransportPolicy: 'all'
};

const workerSettings = {
  logLevel: process.env.MEDIASOUP_WORKER_LOGLEVELS || 'warn',
  logTags: [
    'info',
    'ice',
    'dtls',
    'rtp',
    'srtp',
    'rtcp',
    'rtx',
    'bwe',
    'score',
    'simulcast',
    'svc',
    'sctp',
  ],
  rtcMinPort: parseInt(process.env.RTC_MIN_PORT) || 40000,
  rtcMaxPort: parseInt(process.env.RTC_MAX_PORT) || 49999,
};

module.exports = {
  mediasoup: {
    numWorkers: parseInt(process.env.MEDIASOUP_NUM_WORKERS) || 2,
    worker: workerSettings,
    router: {
      mediaCodecs,
    },
    webRtcTransport: webRtcTransportOptions,
  },
};
