import { frappeRequest, toast } from "frappe-ui";
import { getErrorMessage } from "../utils/error";
import type { LobbyStore } from "./useLobbyStore";
import { useConnectionState } from "./useConnectionState";

interface LobbyAPI {
	approveUser: (userId: string) => Promise<void>;
	approveAllUsers: () => Promise<void>;
	rejectUser: (userId: string) => Promise<void>;
}

export function useLobby(deps: {
	lobbyStore: LobbyStore;
	meetingId: string;
}): LobbyAPI {
	const { lobbyStore, meetingId } = deps;
	const connectionState = useConnectionState();

	const getGuestId = () =>
		connectionState.guestId || sessionStorage.getItem("guest_id") || undefined;

	const approveUser = async (userId: string) => {
		try {
			const params: Record<string, unknown> = {
				meeting_id: meetingId,
				user_id: userId,
			};
			const guestId = getGuestId();
			if (guestId) params.guest_id = guestId;

			await frappeRequest({
				url: "meet.api.meeting.approve_join_request",
				params,
			});

			lobbyStore.removeLobbyUser(userId);
		} catch (error) {
			console.error("Failed to approve user:", error);
			toast.error(getErrorMessage(error));
		}
	};

	const approveAllUsers = async () => {
		try {
			const params: Record<string, unknown> = {
				meeting_id: meetingId,
			};
			const guestId = getGuestId();
			if (guestId) params.guest_id = guestId;

			await frappeRequest({
				url: "meet.api.meeting.approve_all_join_requests",
				params,
			});

			lobbyStore.setLobbyUsers([]);
		} catch (error) {
			console.error("Failed to approve all users:", error);
			toast.error(getErrorMessage(error));
		}
	};

	const rejectUser = async (userId: string) => {
		try {
			const params: Record<string, unknown> = {
				meeting_id: meetingId,
				user_id: userId,
			};
			const guestId = getGuestId();
			if (guestId) params.guest_id = guestId;

			await frappeRequest({
				url: "meet.api.meeting.reject_join_request",
				params,
			});

			lobbyStore.removeLobbyUser(userId);
		} catch (error) {
			console.error("Failed to reject user:", error);
			toast.error(getErrorMessage(error));
		}
	};

	return {
		approveUser,
		approveAllUsers,
		rejectUser,
	};
}