import { afterEach, describe, expect, it, vi } from 'vitest';
import { publishPresence } from '../PresenceWebhook';
import type { MediasoupManager } from '../../mediasoup/MediasoupManager';

describe('publishPresence', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('retries when Meet reports that relaying to NextGRP failed', async () => {
		process.env.JWT_SECRET = 'test-secret';
		const fetch = vi
			.fn()
			.mockResolvedValueOnce({ ok: false, status: 502 })
			.mockResolvedValueOnce({ ok: true, status: 200 });
		vi.stubGlobal('fetch', fetch);
		vi.spyOn(globalThis, 'setTimeout').mockImplementation((callback: TimerHandler) => {
			if (typeof callback === 'function') callback();
			return 0 as unknown as ReturnType<typeof setTimeout>;
		});
		const mediasoup = {
			getRoomParticipants: vi.fn().mockReturnValue([{ id: 'peer-1' }]),
		} as unknown as MediasoupManager;

		await publishPresence(
			mediasoup,
			'site::room-1',
			'room-1',
			'site',
			'mtp.example.com',
			'https://meet.example/api/method/meet.api.meeting.sfu_presence_event',
		);

		expect(fetch).toHaveBeenCalledTimes(2);
		expect(mediasoup.getRoomParticipants).toHaveBeenCalledWith('site::room-1');
		expect(fetch.mock.calls[0][1]?.headers).toHaveProperty(
			'X-SFU-Presence-Token',
		);
	});

	it('does not retry a permanent callback rejection', async () => {
		process.env.JWT_SECRET = 'test-secret';
		const fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });
		vi.stubGlobal('fetch', fetch);

		await publishPresence(
			{ getRoomParticipants: vi.fn().mockReturnValue([]) } as unknown as MediasoupManager,
			'site::room-1',
			'room-1',
			'site',
			'mtp.example.com',
			'https://meet.example/api/method/meet.api.meeting.sfu_presence_event',
		);

		expect(fetch).toHaveBeenCalledTimes(1);
	});
});
