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
	if (!site || !hostName || !callbackUrl) return;
	const jwtSecret = process.env.JWT_SECRET;
	if (!jwtSecret) return;

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
		{ expiresIn: 10 },
	);
	try {
		const response = await fetch(callbackUrl, {
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json',
			},
			body: '{}',
			signal: AbortSignal.timeout(2000),
		});
		if (!response.ok)
			throw new Error(`Meet presence callback returned ${response.status}`);
	} catch (error) {
		loggers.socketHandler.warn(
			'Could not relay presence for room %s: %s',
			roomId,
			(error as Error).message,
		);
	}
}
