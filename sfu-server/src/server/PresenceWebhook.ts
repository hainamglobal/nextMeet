import * as jwt from 'jsonwebtoken';
import type { MediasoupManager } from '../mediasoup/MediasoupManager';
import { loggers } from '../utils/logger';

export async function publishPresence(
	mediasoup: MediasoupManager,
	roomId: string,
	meetingId: string,
	site: string | undefined,
	hostName: string | undefined,
	callbackUrl: string | undefined,
): Promise<void> {
	if (!site || !hostName || !callbackUrl) {
		loggers.socketHandler.warn(
			'Presence webhook skipped for meeting %s: token is missing site, host name, or callback URL',
			meetingId,
		);
		return;
	}
	const jwtSecret = process.env.JWT_SECRET;
	if (!jwtSecret) {
		loggers.socketHandler.error('Presence webhook skipped: JWT_SECRET is not configured');
		return;
	}

	const count = mediasoup.getRoomParticipants(roomId).length;
	const token = jwt.sign(
		{
			scope: 'sfu-presence-event',
			site,
			host_name: hostName,
			meeting_id: meetingId,
			count,
		},
		jwtSecret,
		{ expiresIn: 30 },
	);
	for (let attempt = 1; attempt <= 2; attempt += 1) {
		try {
			const response = await fetch(callbackUrl, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
				body: '{}',
				signal: AbortSignal.timeout(8000),
			});
			if (!response.ok) {
				const message = `Meet presence callback returned ${response.status}`;
				if (response.status < 500 && response.status !== 429) {
					loggers.socketHandler.warn(
						'Presence webhook rejected for room %s: %s',
						roomId,
						message,
					);
					return;
				}
				throw new Error(message);
			}
			loggers.socketHandler.info(
				'Presence webhook delivered for meeting %s with count %s',
				meetingId,
				count,
			);
			return;
		} catch (error) {
			loggers.socketHandler.warn(
				'Presence webhook attempt %s/2 failed for room %s: %s',
				attempt,
				roomId,
				(error as Error).message,
			);
			if (attempt === 2) return;
			await new Promise((resolve) => setTimeout(resolve, 250));
		}
	}
}
