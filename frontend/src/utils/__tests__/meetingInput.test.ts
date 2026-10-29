import { describe, expect, it } from "vitest";
import { parseMeetingInput } from "../meetingInput";

describe("parseMeetingInput", () => {
	it("accepts a meeting code", () => {
		expect(parseMeetingInput("abcd-efgh-ijkl")).toEqual({
			meetingId: "abcd-efgh-ijkl",
			hash: "",
		});
	});

	it("extracts a meeting code from a full Meet link and keeps its context", () => {
		expect(
			parseMeetingInput(
				"https://meet.nextgrp.vn/meet/abcd-efgh-ijkl#nextgrp_name=Member&nextgrp_entry=entry-1",
			),
		).toEqual({
			meetingId: "abcd-efgh-ijkl",
			hash: "#nextgrp_name=Member&nextgrp_entry=entry-1",
		});
	});

	it("accepts a pasted host and a relative Meet link", () => {
		expect(parseMeetingInput("meet.nextgrp.vn/meet/abcd-efgh-ijkl")?.meetingId).toBe(
			"abcd-efgh-ijkl",
		);
		expect(parseMeetingInput("/meet/abcd-efgh-ijkl")?.meetingId).toBe(
			"abcd-efgh-ijkl",
		);
	});

	it("rejects non-Meet links and malformed codes", () => {
		expect(parseMeetingInput("https://example.com/some/page")).toBeNull();
		expect(parseMeetingInput("https://meet.nextgrp.vn/meet/not-a-code")).toBeNull();
	});
});
