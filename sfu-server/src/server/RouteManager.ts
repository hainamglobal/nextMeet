import fs from 'node:fs';
import path from 'node:path';
import type { Application, Request, Response } from 'express';
import * as jwt from 'jsonwebtoken';
import type { MediasoupManager } from '../mediasoup/MediasoupManager';
import type { HealthStats } from '../types';

export class RouteManager {
	private app: Application;
	private mediasoup: MediasoupManager;
	private jwtSecret: string;

	private static version: string = RouteManager.readVersion();

	private static readVersion(): string {
		try {
			const pkgPath = path.join(__dirname, '..', '..', 'package.json');
			const raw = fs.readFileSync(pkgPath, 'utf8');
			const json = JSON.parse(raw) as { version?: string };
			return json.version ?? 'unknown';
		} catch (_err) {
			return 'unknown';
		}
	}

	constructor(
		app: Application,
		mediasoup: MediasoupManager,
		jwtSecret: string,
	) {
		this.app = app;
		this.mediasoup = mediasoup;
		this.jwtSecret = jwtSecret;
	}

	setupRoutes(): void {
		this.app.get('/', (_req: Request, res: Response) => {
			res.json({
				message: 'Frappe Meet SFU Server is running',
				version: RouteManager.version,
				timestamp: new Date().toISOString(),
			});
		});

		this.app.get('/health', (_req: Request, res: Response) => {
			const stats: HealthStats = {
				status: 'healthy',
				uptime: process.uptime(),
				rooms: this.mediasoup.rooms.getRoomCount(),
				peers: this.mediasoup.peers.getPeerCount(),
			};
			res.json(stats);
		});

		this.app.post('/internal/presence', (req: Request, res: Response) => {
			const authorization = req.header('Authorization') || '';
			const token = authorization.startsWith('Bearer ')
				? authorization.slice(7)
				: '';
			if (!token) {
				res.sendStatus(401);
				return;
			}

			let claims: jwt.JwtPayload;
			try {
				claims = jwt.verify(token, this.jwtSecret) as jwt.JwtPayload;
			} catch (_error) {
				res.sendStatus(401);
				return;
			}

			if (
				claims.scope !== 'presence-list' ||
				typeof claims.site !== 'string' ||
				!claims.site
			) {
				res.sendStatus(403);
				return;
			}

			const meetingIds = req.body?.meeting_ids;
			if (
				!Array.isArray(meetingIds) ||
				meetingIds.length > 100 ||
				meetingIds.some(
					(id) =>
						typeof id !== 'string' ||
						!id ||
						id.length > 140 ||
						id.includes('::') ||
						!Array.isArray(claims.meeting_ids) ||
						!claims.meeting_ids.includes(id),
				)
			) {
				res.status(400).json({ error: 'Invalid meeting_ids' });
				return;
			}

			const counts: Record<string, number> = {};
			for (const meetingId of meetingIds) {
				const roomId = `${claims.site}::${meetingId}`;
				counts[meetingId] = this.mediasoup.getRoomParticipants(roomId).length;
			}
			res.json({ counts });
		});
	}
}
