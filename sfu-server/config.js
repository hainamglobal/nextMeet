const mediasoup = require('mediasoup');
const os = require('os');

// Helper function to get server's local IP address
function getServerIP() {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        console.log(`🔍 Auto-detected server IP: ${iface.address}`);
        return iface.address;
      }
    }
  }
  console.warn('⚠️ Could not auto-detect server IP, using localhost. This will only work for local testing!');
  return '127.0.0.1';
}

function buildListenIps() {
  const baseListenIp = process.env.WEBRTC_LISTEN_IP || '0.0.0.0';
  const announcedEnv = process.env.WEBRTC_ANNOUNCED_IP;
  if (announcedEnv) {
    const ips = Array.from(new Set(announcedEnv.split(',').map(s => s.trim()).filter(Boolean)));
    if (ips.length === 0) {
      console.warn('⚠️ WEBRTC_ANNOUNCED_IP provided but empty after parsing; falling back to auto-detect');
    } else {
      console.log(`🌐 Using announced IP list from env: ${ips.join(', ')}`);
      return ips.map(ip => ({ ip: baseListenIp, announcedIp: ip }));
    }
  }
  // Fallback single entry
  return [{ ip: baseListenIp, announcedIp: getServerIP() }];
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
];

const webRtcTransportOptions = {
  listenIps: buildListenIps(),
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
  logLevel: process.env.MEDIASOUP_WORKER_LOGLEVEL || 'warn',
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

function resolveNumWorkers() {
  const envVal = parseInt(process.env.MEDIASOUP_NUM_WORKERS);
  if (!isNaN(envVal) && envVal > 0) return envVal;
  const cpuCount = os.cpus()?.length || 2;
  return Math.max(1, cpuCount);
}

module.exports = {
  mediasoup: {
    numWorkers: resolveNumWorkers(),
    worker: workerSettings,
    router: { mediaCodecs },
    webRtcTransport: webRtcTransportOptions,
  },
};
