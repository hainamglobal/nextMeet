import 'dotenv/config';
import fs from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import cors from 'cors';
import express, { type Application } from 'express';
import { Server } from 'socket.io';
import { MediasoupManager } from './mediasoup/MediasoupManager';
import { AuthManager } from './server/AuthManager';
import { RouteManager } from './server/RouteManager';
import { SocketHandlerManager } from './server/SocketHandlerManager';
import type { ServerConfig } from './types';
import { loggers } from './utils/logger';

export class SFUServer {
	private app: Application;
	private server: http.Server;
	private io: Server;
	private mediasoup: MediasoupManager;
	private authManager: AuthManager;
	private routeManager: RouteManager;
	private socketHandlerManager: SocketHandlerManager;
	private config: ServerConfig;
	private readonly portConfigPath = path.resolve(process.cwd(), '.runtime-port.json');

	constructor() {
		const jwtSecret = process.env.JWT_SECRET;
		if (!jwtSecret) {
			throw new Error('JWT_SECRET environment variable is required');
		}
		this.config = {
			port: Number.parseInt(process.env.PORT || '4001', 10),
			host: process.env.HOST || '0.0.0.0',
			jwtSecret,
		};

		loggers.server.info(
			'SFU Server will run on http://%s:%d',
			this.config.host,
			this.config.port,
		);

		this.app = express();
		this.server = http.createServer(this.app);
		this.io = new Server(this.server, {
			cors: {
				origin: '*',
				methods: ['GET', 'POST'],
				allowedHeaders: ['*'],
				credentials: false,
			},
			transports: ['websocket', 'polling'],
			pingTimeout: 60000,
			pingInterval: 25000,
			allowEIO3: true,
		});

		this.mediasoup = new MediasoupManager();
		this.authManager = new AuthManager(this.config.jwtSecret);
		this.routeManager = new RouteManager(this.app, this.mediasoup);
		this.socketHandlerManager = new SocketHandlerManager(
			this.io,
			this.mediasoup,
			this.authManager,
		);

		this.setupMiddleware();
		this.routeManager.setupRoutes();
		this.socketHandlerManager.setupSocketHandlers();
	}

	private setupMiddleware(): void {
		this.app.use(cors());
		this.app.use(express.json());
	}

	private async findAvailablePort(startPort: number, host: string): Promise<number> {
		const tryPort = (port: number) =>
			new Promise<void>((resolve, reject) => {
				const tester = net.createServer();
				tester.unref();
				tester.on('error', reject);
				tester.listen(port, host, () => {
					tester.close(() => resolve());
				});
			});

		for (let port = startPort; port <= startPort + 50; port += 1) {
			try {
				await tryPort(port);
				return port;
			} catch {
				continue;
			}
		}

		throw new Error(`No available port found starting from ${startPort}`);
	}

	private persistRuntimePort(port: number): void {
		try {
			fs.writeFileSync(
				this.portConfigPath,
				JSON.stringify(
					{ port, host: this.config.host, updatedAt: new Date().toISOString() },
					null,
					2,
				),
				'utf8',
			);
		} catch (error) {
			loggers.server.warn(
				'Could not persist runtime port to %s: %s',
				this.portConfigPath,
				(error as Error).message,
			);
		}
	}

	async start(): Promise<void> {
		try {
			loggers.server.info('Starting SFU Server');

			await this.mediasoup.init();

			this.config.port = await this.findAvailablePort(
				this.config.port,
				this.config.host,
			);
			this.persistRuntimePort(this.config.port);

			await new Promise<void>((resolve, reject) => {
				this.server.once('error', reject);
				this.server.listen(this.config.port, this.config.host, () => {
					this.server.off('error', reject);
					loggers.server.info(
						'SFU Server running on http://%s:%d',
						this.config.host,
						this.config.port,
					);
					resolve();
				});
			});
		} catch (error) {
			loggers.server.error(
				'Failed to start SFU server: %s',
				(error as Error).message,
			);
			process.exit(1);
		}
	}

	async stop(): Promise<void> {
		loggers.server.info('Stopping SFU Server');

		try {
			await this.mediasoup.cleanup();

			this.server.close(() => {
				loggers.server.info('SFU Server stopped');
			});
		} catch (error) {
			loggers.server.error(
				'Error during server shutdown: %s',
				(error as Error).message,
			);
			this.server.close(() => {
				loggers.server.info('SFU Server force stopped');
			});
		}
	}
}

const sfuServer = new SFUServer();

process.on('SIGINT', async () => {
	loggers.server.info('Received SIGINT, shutting down gracefully');
	await sfuServer.stop();
	process.exit(0);
});

process.on('SIGTERM', async () => {
	loggers.server.info('Received SIGTERM, shutting down gracefully');
	await sfuServer.stop();
	process.exit(0);
});

process.on('uncaughtException', (error) => {
	loggers.server.error(
		'Uncaught exception (server kept alive): %s\n%s',
		error.message,
		error.stack,
	);
});

process.on('unhandledRejection', (reason) => {
	loggers.server.error(
		'Unhandled rejection (server kept alive): %s',
		reason instanceof Error ? reason.message : String(reason),
	);
});

sfuServer.start().catch((error) => {
	loggers.server.error(
		'Failed to start SFU server: %s',
		(error as Error).message,
	);
	process.exit(1);
});
