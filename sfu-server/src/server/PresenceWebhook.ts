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
	const callbackTarget = (() => {
		try {
			const url = new URL(callbackUrl);
			return `${url.origin}${url.pathname}`;
		} catch {
			return 'invalid callback URL';
		}
	})();
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
					'X-SFU-Presence-Token': token,
					'Content-Type': 'application/json',
				},
				body: '{}',
				signal: AbortSignal.timeout(8000),
			});
			if (!response.ok) {
				const message = `Meet presence callback returned ${response.status}`;
				if (response.status < 500 && response.status !== 429) {
					let responseReason = '';
					try {
						const body = (await response.clone().json()) as {
							exception?: unknown;
							message?: unknown;
							_server_messages?: unknown;
						};
						let detail =
							typeof body.exception === 'string'
								? body.exception
								: typeof body.message === 'string'
									? body.message
									: '';
						if (typeof body._server_messages === 'string') {
							try {
								const messages = JSON.parse(body._server_messages) as unknown[];
								const first = messages[0];
								const parsed =
									typeof first === 'string'
										? (JSON.parse(first) as { message?: unknown })
										: (first as { message?: unknown });
								if (typeof parsed?.message === 'string') detail = parsed.message;
							} catch (_error) {
								// Keep the HTTP exception detail when Frappe's message is malformed.
							}
						}
						responseReason = detail.split(/\r?\n/, 1)[0].slice(0, 180);
					} catch (_error) {
						responseReason = '';
					}
					loggers.socketHandler.warn(
						'Presence webhook rejected for room %s: %s%s',
						roomId,
						message,
						responseReason ? ` (${responseReason})` : '',
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
			const cause = (error as Error & { cause?: unknown }).cause;
			const causeMessage =
				cause instanceof Error
					? `${cause.name}: ${cause.message}`
					: cause
						? String(cause)
						: 'none';
			loggers.socketHandler.warn(
				'Presence webhook attempt %s/2 failed for room %s to %s: %s (cause: %s)',
				attempt,
				roomId,
				callbackTarget,
				(error as Error).message,
				causeMessage,
			);
			if (attempt === 2) return;
			await new Promise((resolve) => setTimeout(resolve, 250));
		}
	}
}
