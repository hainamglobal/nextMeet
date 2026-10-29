const MEETING_ID_PATTERN = /^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$/;

export interface ParsedMeetingInput {
	meetingId: string;
	hash: string;
}

export function parseMeetingInput(
	value: string,
	baseUrl = "https://meet.nextgrp.vn/meet/",
): ParsedMeetingInput | null {
	const input = value.trim();
	if (MEETING_ID_PATTERN.test(input)) {
		return { meetingId: input, hash: "" };
	}
	if (!input) return null;

	let url: URL;
	try {
		if (/^https?:\/\//i.test(input)) {
			url = new URL(input);
		} else if (input.startsWith("//")) {
			url = new URL(`https:${input}`);
		} else if (input.startsWith("/")) {
			url = new URL(input, baseUrl);
		} else if (/^[\w.-]+(?::\d+)?\/meet\//i.test(input)) {
			url = new URL(`https://${input}`);
		} else {
			return null;
		}
	} catch {
		return null;
	}

	const segments = url.pathname.split("/").filter(Boolean);
	const meetingRouteIndex = segments.lastIndexOf("meet");
	const meetingId = meetingRouteIndex >= 0 ? segments[meetingRouteIndex + 1] : "";
	if (!MEETING_ID_PATTERN.test(meetingId || "")) return null;

	return { meetingId, hash: url.hash };
}
