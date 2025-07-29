const winston = require('winston');

// Define log format
const logFormat = winston.format.combine(
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss'
  }),
  winston.format.errors({ stack: true }),
  winston.format.printf(({ level, message, timestamp, stack }) => {
    return `${timestamp} [${level.toUpperCase()}]: ${stack || message}`;
  })
);

// Create logger instance
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: logFormat,
  transports: [
    // Console transport with colors for development
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        logFormat
      )
    }),
    
    // File transport for errors
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    }),
    
    // File transport for all logs
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    })
  ],
  
  // Don't exit on handled exceptions
  exitOnError: false
});

// Handle uncaught exceptions and unhandled rejections
logger.exceptions.handle(
  new winston.transports.File({ filename: 'logs/exceptions.log' })
);

logger.rejections.handle(
  new winston.transports.File({ filename: 'logs/rejections.log' })
);

// Add custom methods for SFU-specific logging
logger.sfu = {
  // Connection events
  connection: (message, meta = {}) => {
    logger.info(`[CONNECTION] ${message}`, meta);
  },
  
  // Room events
  room: (message, meta = {}) => {
    logger.info(`[ROOM] ${message}`, meta);
  },
  
  // Transport events
  transport: (message, meta = {}) => {
    logger.info(`[TRANSPORT] ${message}`, meta);
  },
  
  // Producer/Consumer events
  media: (message, meta = {}) => {
    logger.info(`[MEDIA] ${message}`, meta);
  },
  
  // WebRTC events
  webrtc: (message, meta = {}) => {
    logger.info(`[WEBRTC] ${message}`, meta);
  },
  
  // Performance metrics
  metrics: (message, meta = {}) => {
    logger.debug(`[METRICS] ${message}`, meta);
  },
  
  // Security events
  security: (message, meta = {}) => {
    logger.warn(`[SECURITY] ${message}`, meta);
  }
};

module.exports = logger;
