const NETWORK_ERROR_MESSAGE = "Mất kết nối mạng. Vui lòng thử lại.";

export function isNetworkError(error: unknown): boolean {
	const message =
		typeof error === "string"
			? error
			: error instanceof Error
				? error.message
				: "";
	const normalizedMessage = message.toLowerCase();

	return [
		"failed to fetch",
		"networkerror",
		"network request failed",
		"err_internet_disconnected",
		"err_network_changed",
		"load failed",
	].some((indicator) => normalizedMessage.includes(indicator));
}

export function getErrorMessage(error: unknown): string {
	if (isNetworkError(error)) {
		return NETWORK_ERROR_MESSAGE;
	}

	if (!(error instanceof Error)) {
		return String(error);
	}

	if (
		"messages" in error &&
		Array.isArray(error.messages) &&
		error.messages.length > 0
	) {
		return error.messages[error.messages.length - 1];
	}

	return error.message || "An unknown error occurred";
}
