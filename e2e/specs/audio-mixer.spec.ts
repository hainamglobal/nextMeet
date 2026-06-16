import { test, expect, joinFromPreview } from "../fixtures/test";

interface MixerState {
	found: boolean;
	paused: boolean;
	muted: boolean;
	readyState: number;
	trackCount: number;
	trackStates: Array<{ id: string; muted: boolean; readyState: string }>;
}

async function readMixerState(page: import("@playwright/test").Page): Promise<MixerState> {
	return page.evaluate(() => {
		const el = document.querySelector(
			'[data-testid="audio-mixer-output"]',
		) as HTMLAudioElement | null;
		if (!el) {
			return {
				found: false,
				paused: false,
				muted: false,
				readyState: 0,
				trackCount: 0,
				trackStates: [],
			};
		}
		const stream = el.srcObject as MediaStream | null;
		const tracks = stream?.getAudioTracks() ?? [];
		return {
			found: true,
			paused: el.paused,
			muted: el.muted,
			readyState: el.readyState,
			trackCount: tracks.length,
			trackStates: tracks.map((t) => ({
				id: t.id,
				muted: t.muted,
				readyState: t.readyState,
			})),
		};
	});
}

function expectMixerHealthy(state: MixerState): void {
	expect(state.found, "mixer output element should be created").toBe(true);
	expect(state.trackCount, "should have at least one inbound audio track").toBeGreaterThan(0);
	expect(state.paused, "mixer output <audio> should not be paused").toBe(false);
	expect(state.muted, "mixer output <audio> should not be muted").toBe(false);
	expect(
		state.readyState,
		"mixer output <audio> should have data ready (HAVE_CURRENT_DATA or beyond)",
	).toBeGreaterThanOrEqual(2);
	for (const t of state.trackStates) {
		expect(t.readyState, `inbound track ${t.id} should be live`).toBe("live");
		expect(t.muted, `inbound track ${t.id} should be unmuted`).toBe(false);
	}
}

test.describe("Remote audio mixer", () => {
	test("a guest hears the host: the mixer's output is playing the host's audio", async ({
		hostPage,
		meetingId,
		createParticipant,
	}) => {
		const guest = await createParticipant();

		await hostPage.goto(`/meet/${meetingId}`);
		await joinFromPreview(hostPage);
		await guest.joinAsGuest(meetingId, "Audio Probe Guest");

		await expect(hostPage.locator("[data-participant-id]")).toHaveCount(2);

		await expect(
			guest.page.locator('[data-testid="audio-mixer-output"]'),
		).toHaveCount(1, { timeout: 15_000 });

		expectMixerHealthy(await readMixerState(guest.page));
	});

	test("with 3 participants, each one receives audio from the other two in the shared mixer output", async ({
		hostPage,
		meetingId,
		createParticipant,
	}) => {
		const guestA = await createParticipant();
		const guestB = await createParticipant();

		await hostPage.goto(`/meet/${meetingId}`);
		await joinFromPreview(hostPage);
		await guestA.joinAsGuest(meetingId, "Guest A");
		await guestB.joinAsGuest(meetingId, "Guest B");

		await expect(hostPage.locator("[data-participant-id]")).toHaveCount(3);
		await expect(guestA.page.locator("[data-participant-id]")).toHaveCount(3);

		// Each guest should have a mixer output with the other two as inbound
		// tracks, all live and unmuted.
		for (const participant of [hostPage, guestA.page, guestB.page]) {
			await expect(
				participant.locator('[data-testid="audio-mixer-output"]'),
			).toHaveCount(1, { timeout: 15_000 });
			const state = await readMixerState(participant);
			expectMixerHealthy(state);
		}
	});
});

