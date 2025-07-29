/**
 * Client-side SFU Connection Manager
 * Handles direct communication between client and SFU server
 */

class SFUClientManager {
	constructor() {
		this.socket = null;
		this.connected = false;
		this.meetingId = null;
		this.userId = null;
		this.authToken = null;
		this.eventHandlers = new Map();
		this.reconnectAttempts = 0;
		this.maxReconnectAttempts = 5;
	}

	/**
	 * Connect to SFU server with authentication
	 */
	async connect(sfuEndpoint, authToken, meetingId, userId) {
		try {
			this.authToken = authToken;
			this.meetingId = meetingId;
			this.userId = userId;

			console.log('Connecting to SFU:', sfuEndpoint);

			// Create socket connection
			this.socket = io(sfuEndpoint, {
				auth: {
					token: authToken,
					meetingId: meetingId,
					userId: userId
				},
				reconnection: true,
				reconnectionAttempts: this.maxReconnectAttempts,
				reconnectionDelay: 1000,
				reconnectionDelayMax: 5000,
			});

			// Setup event listeners
			this.setupEventListeners();

			// Wait for connection
			return new Promise((resolve, reject) => {
				this.socket.on('connect', () => {
					console.log('Connected to SFU');
					this.connected = true;
					this.reconnectAttempts = 0;
					resolve(true);
				});

				this.socket.on('connect_error', (error) => {
					console.error('SFU connection error:', error);
					reject(error);
				});

				setTimeout(() => {
					if (!this.connected) {
						reject(new Error('Connection timeout'));
					}
				}, 10000);
			});

		} catch (error) {
			console.error('Error connecting to SFU:', error);
			throw error;
		}
	}

	/**
	 * Setup socket event listeners
	 */
	setupEventListeners() {
		this.socket.on('disconnect', () => {
			console.log('Disconnected from SFU');
			this.connected = false;
		});

		this.socket.on('reconnect', () => {
			console.log('Reconnected to SFU');
			this.connected = true;
		});

		this.socket.on('error', (error) => {
			console.error('SFU error:', error);
			this.handleEvent('error', error);
		});

		// WebRTC events
		this.socket.on('router_rtp_capabilities', (data) => {
			this.handleEvent('router_rtp_capabilities', data);
		});

		this.socket.on('webrtc_transport_created', (data) => {
			this.handleEvent('webrtc_transport_created', data);
		});

		this.socket.on('producer_created', (data) => {
			this.handleEvent('producer_created', data);
		});

		this.socket.on('consumer_created', (data) => {
			this.handleEvent('consumer_created', data);
		});

		this.socket.on('new_producer', (data) => {
			this.handleEvent('new_producer', data);
		});

		this.socket.on('producer_closed', (data) => {
			this.handleEvent('producer_closed', data);
		});

		// Meeting events
		this.socket.on('participant_joined', (data) => {
			this.handleEvent('participant_joined', data);
		});

		this.socket.on('participant_left', (data) => {
			this.handleEvent('participant_left', data);
		});
	}

	/**
	 * Register event handler
	 */
	on(event, handler) {
		if (!this.eventHandlers.has(event)) {
			this.eventHandlers.set(event, []);
		}
		this.eventHandlers.get(event).push(handler);
	}

	/**
	 * Handle events and call registered handlers
	 */
	handleEvent(event, data) {
		const handlers = this.eventHandlers.get(event);
		if (handlers) {
			handlers.forEach(handler => {
				try {
					handler(data);
				} catch (error) {
					console.error(`Error in event handler for ${event}:`, error);
				}
			});
		}
	}

	/**
	 * Get router RTP capabilities
	 */
	async getRouterRtpCapabilities() {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error('Not connected to SFU'));
				return;
			}

			this.socket.emit('get_router_rtp_capabilities', {
				roomId: this.meetingId
			}, (response) => {
				if (response && response.success) {
					resolve(response.rtpCapabilities);
				} else {
					reject(new Error(response?.error || 'Failed to get router capabilities'));
				}
			});
		});
	}

	/**
	 * Create WebRTC transport
	 */
	async createWebRtcTransport(direction = 'send') {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error('Not connected to SFU'));
				return;
			}

			this.socket.emit('create_webrtc_transport', {
				roomId: this.meetingId,
				userId: this.userId,
				direction: direction
			}, (response) => {
				if (response && response.success) {
					resolve({
						id: response.id,
						iceParameters: response.iceParameters,
						iceCandidates: response.iceCandidates,
						dtlsParameters: response.dtlsParameters,
						sctpParameters: response.sctpParameters
					});
				} else {
					reject(new Error(response?.error || 'Failed to create transport'));
				}
			});
		});
	}

	/**
	 * Connect transport
	 */
	connectTransport(transportId, dtlsParameters) {
		if (!this.connected) {
			throw new Error('Not connected to SFU');
		}

		this.socket.emit('connect_transport', {
			roomId: this.meetingId,
			userId: this.userId,
			transportId: transportId,
			dtlsParameters: dtlsParameters
		});
	}

	/**
	 * Produce media
	 */
	async produce(transportId, kind, rtpParameters, paused = false, appData = {}) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error('Not connected to SFU'));
				return;
			}

			this.socket.emit('produce', {
				roomId: this.meetingId,
				userId: this.userId,
				transportId: transportId,
				kind: kind,
				rtpParameters: rtpParameters,
				paused: paused,
				appData: appData
			}, (response) => {
				if (response && response.success) {
					resolve(response.id);
				} else {
					reject(new Error(response?.error || 'Failed to produce'));
				}
			});
		});
	}

	/**
	 * Consume media
	 */
	async consume(producerId, rtpCapabilities) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error('Not connected to SFU'));
				return;
			}

			this.socket.emit('consume', {
				roomId: this.meetingId,
				userId: this.userId,
				producerId: producerId,
				rtpCapabilities: rtpCapabilities
			}, (response) => {
				if (response && response.success) {
					resolve({
						id: response.id,
						producerId: response.producerId,
						kind: response.kind,
						rtpParameters: response.rtpParameters,
						type: response.type,
						producerPaused: response.producerPaused
					});
				} else {
					reject(new Error(response?.error || 'Failed to consume'));
				}
			});
		});
	}

	/**
	 * Get existing producers
	 */
	async getExistingProducers() {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error('Not connected to SFU'));
				return;
			}

			this.socket.emit('get_existing_producers', {
				roomId: this.meetingId,
				userId: this.userId
			}, (response) => {
				if (response && response.success) {
					resolve(response.producers || []);
				} else {
					reject(new Error(response?.error || 'Failed to get existing producers'));
				}
			});
		});
	}

	/**
	 * Pause/Resume producer
	 */
	pauseResumeProducer(producerId, action) {
		if (!this.connected) {
			throw new Error('Not connected to SFU');
		}

		this.socket.emit(`${action}_producer`, {
			roomId: this.meetingId,
			userId: this.userId,
			producerId: producerId
		});
	}

	/**
	 * Pause/Resume consumer
	 */
	pauseResumeConsumer(consumerId, action) {
		if (!this.connected) {
			throw new Error('Not connected to SFU');
		}

		this.socket.emit(`${action}_consumer`, {
			roomId: this.meetingId,
			userId: this.userId,
			consumerId: consumerId
		});
	}

	/**
	 * Disconnect from SFU
	 */
	disconnect() {
		if (this.socket) {
			this.socket.disconnect();
			this.socket = null;
			this.connected = false;
		}
	}
}

// Export for use in other modules
window.SFUClientManager = SFUClientManager;
