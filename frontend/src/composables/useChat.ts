import { frappeRequest, toast } from "frappe-ui";
import audioNotificationManager from "../utils/audioNotifications";
import type { SFUClient } from "../utils/SFUClient";
import type { ChatMessage, ChatStore } from "./useChatStore";
import type { CurrentUser } from "./useCurrentUser";

interface ChatAPI {
	setupChatEvents: (notificationQueue: unknown) => void;
	loadHistory: () => Promise<void>;
	onSendChat: (text: string) => Promise<void>;
	toggleRestriction: (enabled: boolean) => void;
}

export function useChat(deps: {
	chatStore: ChatStore;
	currentUser: CurrentUser;
	sfuClient: SFUClient;
	meetingId: string;
}): ChatAPI {
	const { chatStore, currentUser, sfuClient, meetingId } = deps;

	const loadHistory = async () => {
		const guestId = currentUser.currentUser.value?.user_id?.startsWith("guest_")
			? sessionStorage.getItem("guest_id") || undefined
			: undefined;
		const rows = (await frappeRequest({
			url: "meet.api.chat.get_history",
			params: { meeting_id: meetingId, guest_id: guestId, limit: 200 },
		})) as Array<Record<string, unknown>>;

		chatStore.setMessages(
			(rows || []).map((row) => ({
				id: String(row.id),
				user_id: String(row.user_id || ""),
				user_name: String(row.user_name || row.user_id || ""),
				message: String(row.message || ""),
				timestamp: String(row.timestamp || ""),
			})),
		);
	};

	const setupChatEvents = (notificationQueue: unknown) => {
		sfuClient.on("chat:message", (data: Record<string, unknown>) => {
			if (data.fromUser === currentUser.currentUser.value?.user_id) {
				return;
			}

			const message: ChatMessage = {
				id: Date.now() + Math.random(),
				user_id: data.fromUser as string,
				user_name: (data.fromName || data.fromUser) as string,
				message: data.message as string,
				timestamp: new Date().toISOString(),
			};

			chatStore.addMessage(message);

			if (
				!chatStore.isChatOpen &&
				data.fromUser !== currentUser.currentUser.value?.user_id
			) {
				chatStore.hasUnreadMessages = true;

				(
					notificationQueue as { addNotification?: (n: unknown) => void }
				)?.addNotification?.({
					message: data.message,
					fromUser: data.fromUser,
					fromName: data.fromName || data.fromUser,
					timestamp: message.timestamp,
				});
				audioNotificationManager.playChatNotification();
			}
		});
		sfuClient.on(
			"chat:restriction_updated",
			(data: Record<string, unknown>) => {
				chatStore.hostOnlyChat = Boolean(data.enabled);
			},
		);

		sfuClient.on("sfu_error", (data: Record<string, unknown>) => {
			if (data?.code === "HOST_ONLY_CHAT") {
				toast.error("The host has restricted chat to hosts and co-hosts only.");
				chatStore.hostOnlyChat = true;
			}
		});
	};

	const toggleRestriction = (enabled: boolean) => {
		if (sfuClient.isConnected()) {
			sfuClient.sendEvent("chat:toggle_restriction", { enabled });
		}
	};

	const onSendChat = async (text: string) => {
		const messageText = text.trim();
		if (!messageText) return;

		const current = currentUser.currentUser.value;
		const guestId = current?.user_id?.startsWith("guest_")
			? sessionStorage.getItem("guest_id") || undefined
			: undefined;
		const clientId =
			globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;

		try {
			const saved = (await frappeRequest({
				url: "meet.api.chat.send_message",
				params: {
					meeting_id: meetingId,
					message: messageText,
					guest_id: guestId,
					client_id: clientId,
				},
			})) as Record<string, unknown>;

			chatStore.addMessage({
				id: String(saved.id),
				user_id: String(saved.user_id || current?.user_id || ""),
				user_name: String(
					saved.user_name || current?.full_name || current?.name || "",
				),
				message: String(saved.message || messageText),
				timestamp: String(saved.timestamp || new Date().toISOString()),
			});

			if (sfuClient.isConnected()) {
				sfuClient.sendChatMessage(messageText, { clientId });
			}
		} catch (error) {
			console.error("Failed to save chat message:", error);
			toast.error("Could not save this message");
		}
	};

	return {
		setupChatEvents,
		loadHistory,
		toggleRestriction,
		onSendChat,
	};
}
