import { describe, expect, it } from "vitest";
import { getErrorMessage, isNetworkError } from "../error";

describe("error helpers", () => {
	it.each([
		"Failed to fetch",
		"TypeError: NetworkError when attempting to fetch resource",
		"net::ERR_INTERNET_DISCONNECTED",
		"Load failed",
	])("recognizes %s as a network error", (message) => {
		expect(isNetworkError(new Error(message))).toBe(true);
		expect(getErrorMessage(new Error(message))).toBe(
			"Mất kết nối mạng. Vui lòng thử lại.",
		);
	});

	it("preserves non-network error messages", () => {
		expect(getErrorMessage(new Error("Phòng họp không tồn tại"))).toBe(
			"Phòng họp không tồn tại",
		);
	});
});
