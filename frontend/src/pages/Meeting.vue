<template>
	<div class="h-[100dvh] bg-gray-900 flex flex-col" data-meeting-component>
		<!-- Checking meeting validity state -->
		<div v-if="isCheckingMeeting" class="flex-1 flex items-center justify-center bg-gray-50">
			<div class="flex items-center justify-center text-gray-800 space-x-4">
				<Spinner class="h-10 text-blue-600" />
				<p class="text-base font-medium">Đang kiểm tra cuộc họp...</p>
			</div>
		</div>

		<!-- Meeting Not Found / Invalid state -->
		<div v-else-if="meetingNotFound" class="flex-1 flex flex-col bg-gray-50">
			<div class="bg-gray-50 px-6 pt-4 flex-shrink-0">
				<div class="flex items-center gap-2 cursor-pointer" @click="$router.push('/')">
					<FrappeMeetingLogo class="h-8" />
					<h4 class="text-gray-900 text-base font-semibold">NextMeet</h4>
				</div>
			</div>
			<div class="flex-1 flex items-center justify-center p-6">
				<div class="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center space-y-4 border border-gray-100">
					<div class="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-2 bg-red-100">
						<lucide-alert-circle class="w-8 h-8 text-red-600" />
					</div>
					<h2 class="text-2xl font-semibold text-gray-900">
						Cuộc họp không tồn tại
					</h2>
					<p class="text-gray-600 text-sm">
						{{ meetingErrorMessage || "Đường dẫn cuộc họp không đúng hoặc phòng họp đã bị xóa / kết thúc." }}
					</p>
					<div class="pt-2">
						<Button
							variant="solid"
							size="lg"
							class="w-full"
							@click="$router.push('/')"
						>
							Quay lại trang chủ
						</Button>
					</div>
				</div>
			</div>
		</div>

		<!-- Loading state -->
		<div v-else-if="isConnecting" class="flex-1 flex items-center justify-center">
			<div class="flex items-center justify-center text-white space-x-4">
				<Spinner class="h-12" />
				<p class="text-lg">Joining meeting...</p>
			</div>
		</div>

		<!-- Error state -->
		<div v-else-if="hasConnectionError" class="flex-1 flex items-center justify-center">
			<div class="text-center text-white">
				<div class="text-red-500 mb-4">
					<lucide-alert-circle class="w-12 h-12 mx-auto" />
				</div>
				<p class="text-lg mb-4">{{ connectionState.connectionError }}</p>
				<Button @click="resetToPreview" variant="outline" theme="red">Try Again</Button>
			</div>
		</div>

		<!-- Meeting ended state -->
		<div v-else-if="callEnded" class="relative flex-1 overflow-hidden bg-slate-50">
			<header class="absolute inset-x-0 top-0 flex h-16 items-center justify-between border-b border-gray-200 bg-white px-5 sm:px-8">
				<div class="flex items-center gap-3">
					<FrappeMeetingLogo class="h-8 w-8" />
					<span class="text-base font-semibold text-gray-900">nextMeet</span>
				</div>
				<span class="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">Đã kết thúc</span>
			</header>
			<main class="flex min-h-full items-center justify-center px-5 pb-8 pt-24">
				<section class="w-full max-w-xl text-center">
					<div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700">
						<lucide-check class="h-8 w-8" />
					</div>
					<p class="mb-2 text-sm font-semibold text-emerald-700">Cuộc họp đã kết thúc</p>
					<h1 class="text-3xl font-semibold text-gray-900">Bạn đã rời khỏi cuộc họp</h1>
					<p class="mx-auto mt-3 max-w-md text-sm leading-6 text-gray-600">
						Kết nối và các thiết bị trong cuộc họp đã được ngắt. Bạn có thể tham gia lại nếu cuộc họp vẫn còn mở.
					</p>
					<div class="mt-8 flex justify-center">
						<Button variant="solid" size="lg" class="min-w-40" @click="rejoinMeeting">Tham gia lại</Button>
					</div>
					<p class="mt-8 text-xs text-gray-500">Mã cuộc họp <span class="ml-1 font-medium text-gray-700">{{ meetingId }}</span></p>
				</section>
			</main>
		</div>

		<!-- Preview mode -->
		<MeetingPreview
			v-else-if="showPreview"
			:meetingId="meetingId"
			:isCameraOn="mediaState.isCameraOn"
			:isMicOn="mediaState.isMicOn"
			:cameraPermissionGranted="mediaState.cameraPermissionGranted"
			:microphonePermissionGranted="mediaState.microphonePermissionGranted"
			:isConnecting="connectionState.isConnecting"
			:userInitials="currentUser.userInitials.value"
			:userAvatar="currentUser.userAvatar.value"
			:currentUserName="
				currentUser.currentUser.value?.full_name ||
				currentUser.currentUser.value?.name ||
				'You'
			"
			:guestAuthToken="connectionState.guestAuthToken"
			:isWaitingForApproval="lobbyStore.isWaitingForApproval"
			:setLocalVideoRef="mediaControls.setLocalVideoRef"
			@toggle-microphone="mediaControls.toggleMicrophone()"
			@toggle-camera="mediaControls.toggleCamera()"
			@join-from-preview="joinMeetingFromPreview"
			@guest-join-complete="handleGuestJoinComplete"
			@leave-waiting-room="leaveWaitingRoom"
			@try-join-again="tryJoinAgain"
			@device-changed="handleDeviceChanged"
		/>

		<!-- Main meeting interface -->
		<template v-else>
			<div class="relative flex flex-1 min-h-0 overflow-hidden">
				<div
					class="grid flex-1 min-h-0 transition-[grid-template-columns] duration-300 ease-out relative"
					:style="{
						'--panel-width': panelWidth,
						gridTemplateColumns: 'minmax(0, 1fr) var(--panel-width)',
					}"
				>
					<!-- Video column — padding-bottom mirrors the toolbar height so tiles
                 reclaim the space when the toolbar hides, without affecting panels -->
					<div
						class="flex flex-col min-h-0 transition-[padding-bottom] duration-500 ease-in-out"
						:style="{ paddingBottom: isToolbarVisible ? '6rem' : '0' }"
					>
						<!-- Video area -->
						<div class="p-4 flex flex-col flex-1 min-h-0 text-white">
							<MeetingLayout @open-people-panel="togglePeople" />
						</div>
					</div>

					<!-- Panel Container -->
					<Transition
						enter-active-class="transition-all duration-300 ease-out"
						enter-from-class="opacity-0 transform translate-x-full w-0"
						enter-to-class="opacity-100 transform translate-x-0"
						leave-active-class="transition-all duration-300 ease-in"
						leave-from-class="opacity-100 transform translate-x-0"
						leave-to-class="opacity-0 transform translate-x-full"
					>
						<div
							v-if="activePanel"
							class="h-full overflow-hidden z-50 md:z-auto bg-black/30 backdrop-blur-sm md:bg-transparent"
							:class="{
								'absolute inset-0 w-full': isMobile,
								relative: !isMobile,
								'md:relative': true,
							}"
							:style="{ width: isMobile ? '100%' : '24rem' }"
						>
							<!-- Chat Panel -->
							<ChatPanel
								v-if="activePanel === 'chat'"
								:open="true"
								:messages="chatStore.chatMessages"
								:user-id="(currentUser.currentUser.value?.user_id as string) || ''"
								:user-name="
									(currentUser.currentUser.value?.full_name as string) ||
									(currentUser.currentUser.value?.name as string) ||
									'You'
								"
								:isHost="isCurrentUserHost"
								:isCohost="isCurrentUserCohost"
                                :hostOnlyChat="chatStore.hostOnlyChat"
								@close="toggleChat"
								@send="chat.onSendChat"
							/>

							<!-- People Panel -->
							<PeoplePanel
								v-if="activePanel === 'people'"
								:open="true"
								:currentUser="currentUser.currentUser.value"
								:participants="participantsForPeoplePanel"
								:isMicOn="mediaState.isMicOn"
								:isCameraOn="mediaState.isCameraOn"
								:creatorUserId="meetingOwner"
								:coHosts="meetingCoHosts"
								:lobbyUsers="lobbyStore.lobbyUsers"
								:isHost="isCurrentUserHost"
								@close="togglePeople"
								@muteParticipant="handleMuteParticipant"
								@kickParticipant="handleKickParticipant"
								@lowerHand="handleLowerHand"
								@promoteToCohost="handlePromoteToCohost"
								@approveLobbyUser="handleApproveLobbyUser"
								@approveAllLobbyUsers="handleApproveAllLobbyUsers"
								@rejectLobbyUser="handleRejectLobbyUser"
							/>
						</div>
					</Transition>
				</div>

				<!-- Meeting controls are anchored to the meeting viewport so side panels do not shift them -->
				<div class="pointer-events-none absolute inset-x-0 bottom-0">
					<!-- Meeting controls -->
					<MeetingToolbar
						:isChatOpen="chatStore.isChatOpen"
						:isPeopleOpen="isPeopleOpen"
						:hasUnread="chatStore.hasUnreadMessages"
						:lobbyUserCount="lobbyStore.lobbyUsers?.length || 0"
						:isMicOn="mediaState.isMicOn"
						:isCameraOn="mediaState.isCameraOn"
						:isScreenSharing="mediaState.isScreenSharing"
						:isFullscreen="isFullscreen"
						:isHandRaised="isHandRaised"
						:isReactionPickerOpen="isReactionPickerOpen"
						@update:isReactionPickerOpen="isReactionPickerOpen = $event"
						:meetingId="meetingId"
						:meetingTitle="meetingTitle"
						:currentUser="currentUser.currentUser.value"
						:cameraPermissionGranted="mediaState.cameraPermissionGranted"
						:microphonePermissionGranted="mediaState.microphonePermissionGranted"
						@toggle-chat="toggleChat"
						@toggle-people="togglePeople"
						@toggle-reactions="toggleReactions($event)"
						@toggle-microphone="mediaControls.toggleMicrophone()"
						@toggle-camera="mediaControls.toggleCamera()"
						@toggle-screen-share="mediaControls.toggleScreenShare()"
						@toggle-fullscreen="toggleFullscreen"
						@toggle-raise-hand="raiseHand.toggleRaiseHand()"
						@report-problem="handleReportProblem"
						@end-call="sfuConnection.endCall()"
						@device-changed="handleDeviceChanged"
						@visibility-change="isToolbarVisible = $event"
					/>
				</div>
			</div>

			<LobbyOverlay
				v-if="(isInLobby || isWaitingForApproval) && !isRejected"
				@leave="leaveLobby"
			/>

			<RejectionOverlay v-if="isRejected && isGuestSession" @leave="goHome" />
		</template>

		<!-- Chat notifications -->
		<ChatNotificationQueue
			ref="chatNotificationQueue"
			:auto-dismiss-delay="5000"
			@notification-click="handleNotificationClick"
		/>

		<!-- Join request notifications -->
		<JoinRequestNotifications
			:waitingUsers="lobbyUsersForNotifications"
			@approve-user="lobby.approveUser"
			@reject-user="lobby.rejectUser"
		/>
	</div>
</template>

<script setup lang="ts">
import { Button, frappeRequest, toast } from "frappe-ui";
import { computed, onMounted, onUnmounted, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import ChatNotificationQueue from "../components/ChatNotificationQueue.vue";
import FrappeMeetingLogo from "../icons/FrappeMeetingLogo.vue";
import ChatPanel from "../components/ChatPanel.vue";
import JoinRequestNotifications from "../components/JoinRequestNotifications.vue";
import LobbyOverlay from "../components/LobbyOverlay.vue";
import MeetingLayout from "../components/MeetingLayout.vue";
import MeetingPreview from "../components/MeetingPreview.vue";
import MeetingToolbar from "../components/MeetingToolbar.vue";
import PeoplePanel from "../components/PeoplePanel.vue";
import RejectionOverlay from "../components/RejectionOverlay.vue";
import Spinner from "../components/Spinner.vue";
import { useBackgroundEffects } from "../composables/useBackgroundEffects";
import { useChat } from "../composables/useChat";
import { useChatStore } from "../composables/useChatStore";
import { useConnectionState } from "../composables/useConnectionState";
import { useCurrentUser } from "../composables/useCurrentUser";
import { useGridLayout } from "../composables/useGridLayout";
import { useKeyboardShortcuts } from "../composables/useKeyboardShortcuts";
import { useLobby } from "../composables/useLobby";
import { useLobbyStore } from "../composables/useLobbyStore";
import { useMediaControls } from "../composables/useMediaControls";
import { useMediaState } from "../composables/useMediaState";
import { provideMeetingContext } from "../composables/useMeetingContext";
import { useMeetingDoc } from "../composables/useMeetingDoc";
import {
	type MeetingDocLike,
	useMeetingHandlers,
} from "../composables/useMeetingHandlers";
import { useNoiseCancellation } from "../composables/useNoiseCancellation";
import { useParticipantStore } from "../composables/useParticipantStore";
import { useRaiseHand } from "../composables/useRaiseHand";
import { useRaiseHandStore } from "../composables/useRaiseHandStore";
import { useReactionStore } from "../composables/useReactionStore";
import { useReactions } from "../composables/useReactions";
import { useResponsiveGrid } from "../composables/useResponsiveGrid";
import {
	type SFUScreenShareData,
	useSFUConnection,
} from "../composables/useSFUConnection";
import {
	selectedCameraId,
	selectedMicId,
	selectedSpeakerId,
} from "../data/mediaPreferences";
import { session } from "../data/session";
import { useSocket } from "../socket";
import { deviceManager } from "../utils/media/DeviceManager";
import type { Participant } from "../utils/media/ParticipantManager";

// Router
const route = useRoute();
const router = useRouter();
const meetingId = computed(() => route.params.meetingId as string);

// --- Stores (singletons) ---
const connectionState = useConnectionState();
const currentUser = useCurrentUser();
const mediaState = useMediaState();
const participantStore = useParticipantStore();
const chatStore = useChatStore();
const lobbyStore = useLobbyStore();
const reactionStore = useReactionStore();
const raiseHandStore = useRaiseHandStore();
const gridLayout = useGridLayout(mediaState);

// --- Lobby notification tracking ---
const notifiedLobbyUsers = ref(new Set<string>());

// --- Meeting doc ---
const {
	getMeetingDoc,
	meetingTitle,
	meetingOwner,
	isCurrentUserHost,
	isCurrentUserCohost,
	meetingCoHosts,
} = useMeetingDoc();
const meetingDoc = getMeetingDoc(meetingId.value);
const callEnded = ref(false);

// --- Background effects & noise cancellation ---
const backgroundEffects = useBackgroundEffects();
const noiseCancellation = useNoiseCancellation();

// --- Lobby notification conversion ---
const lobbyUsersForNotifications = computed(() => {
	return lobbyStore.lobbyUsers
		.filter((user) => !notifiedLobbyUsers.value.has(user.userId))
		.map((user) => ({
			user_id: user.userId,
			user_name: user.name,
			user_image: user.avatar,
		}));
});

// --- Guest session ---
const isGuestSession = computed(
	() => !!connectionState.guestAuthToken || lobbyStore.isWaitingForApproval,
);

// --- SFU Connection ---
const sfuConnection = useSFUConnection({
	connectionState,
	currentUser,
	mediaState,
	participantStore,
	lobbyStore,
	gridLayout,
	meetingId: meetingId.value,
	onCallEnded: () => {
		showCallEndedScreen();
	},
	notifiedLobbyUsers,
	onHostMutedYou: () => {
		if (mediaState.isMicOn) {
			mediaControls.toggleMicrophone();
		}
	},
	onHostKickedYou: () => sfuConnection.endCall(),
	onScreenShareStarted: (data: SFUScreenShareData) => {
		const pid = data.participantId;
		if (!pid) return;
		const prev = mediaState.activeScreenShareConsumers || [];
		const filtered = prev.filter((s) => s.participantId !== pid);
		mediaState.activeScreenShareConsumers = [
			...filtered,
			{
				participantId: pid,
				consumerId: data.consumer?.id || "remote-screen",
				startedAt: data.startedAt || Date.now(),
			},
		];
		if (data.stream instanceof MediaStream) {
			try {
				const store = mediaState.screenShareStreams || {};
				store[pid] = data.stream;
				mediaState.screenShareStreams = store;
			} catch (err) {
				console.warn("Failed to store screen share stream:", err);
			}
		}
	},
	onScreenShareStopped: (data: SFUScreenShareData) => {
		const pid = data.participantId;
		const list = mediaState.activeScreenShareConsumers || [];
		mediaState.activeScreenShareConsumers = list.filter(
			(share) => share.participantId !== pid,
		);
		const store = mediaState.screenShareStreams || {};
		if (pid && store[pid]) {
			const stream = store[pid];
			const tracks = stream.getTracks();
			if (tracks) {
				for (const t of tracks) {
					t.stop();
				}
			}
			delete store[pid];
			mediaState.screenShareStreams = store;
		}
	},
	onActiveSpeakerChanged: (participantIds: string[]) => {
		participantStore.activeSpeakerIds = participantIds;
	},
});

// --- Media Controls ---
const mediaControls = useMediaControls({
	mediaState,
	connectionState,
	raiseHandStore,
	currentUser,
	sfuClient: sfuConnection.sfuClient,
	sfuManager: sfuConnection.sfuManager,
	deviceManager,
	backgroundEffects,
	noiseCancellation,
	toast,
	mediaPreferences: {
		micEnabled: ref(false),
		cameraEnabled: ref(false),
		selectedCameraId,
		selectedMicId,
		selectedSpeakerId,
		pushToTalkEnabled: ref(false),
		noiseCancellationEnabled: ref(false),
		setMicEnabled: (_v: boolean) => {
			/* handled via mediaState */
		},
		setCameraEnabled: (_v: boolean) => {
			/* handled via mediaState */
		},
		setSelectedCameraId: () => {},
		setSelectedMicId: () => {},
		setSelectedSpeakerId: () => {},
	},
});

// --- Chat ---
const chat = useChat({
	chatStore,
	currentUser,
	sfuClient: sfuConnection.sfuClient,
	meetingId: meetingId.value,
});

watch(
	() => connectionState.isSetupComplete,
	(isReady) => {
		if (isReady) {
			void chat.loadHistory().catch((error) => {
				console.error("Failed to load meeting chat history:", error);
			});
		}
	},
);

// --- Reactions ---
const reactions = useReactions({
	reactionStore,
	currentUser,
	sfuClient: sfuConnection.sfuClient,
});

// --- Raise Hand ---
const raiseHand = useRaiseHand({
	raiseHandStore,
	currentUser,
	sfuClient: sfuConnection.sfuClient,
});

// --- Lobby ---
const lobby = useLobby({
	lobbyStore,
	meetingId: meetingId.value as string,
});

type AccessData = { allow_guest?: boolean; host_only_chat?: boolean };

// --- Keyboard Shortcuts ---
const keyboardShortcuts = useKeyboardShortcuts({
	mediaControls: {
		toggleMicrophone: () => mediaControls.toggleMicrophone(),
		toggleCamera: () => mediaControls.toggleCamera(),
	},
	mediaState,
});

// --- Provide meeting context for child components ---
provideMeetingContext({
	mediaState,
	participantStore,
	currentUser,
	chatStore,
	gridLayout,
	raiseHandStore,
	reactionStore,
	lobbyStore,
	sfuManager: sfuConnection.sfuManager.value,
	processedStream: mediaState.processedStream,
	isInMeeting: computed(() => true),
	onBackgroundEffectsChanged: mediaControls.applyBackgroundEffectsToLocalStream,
});

// Provide legacy injects for components not yet migrated to useMeetingContext
provide("setLocalVideoRef", mediaControls.setLocalVideoRef);
provide("setRemoteVideoRef", mediaControls.setRemoteVideoRef);
provide("setScreenShareVideoRef", mediaControls.setScreenShareVideoRef);
provide("getParticipantName", participantStore.getParticipantName);
provide("meetingId", meetingId.value);
provide("sfuManager", sfuConnection.sfuManager);
provide("socket", useSocket());
provide("isCurrentUserHost", isCurrentUserHost);
provide("hostControls", {
	muteParticipant: (...args: unknown[]) =>
		handleMuteParticipant(args[0] as string),
	kickParticipant: (...args: unknown[]) =>
		handleKickParticipant(args[0] as string, args[1] as boolean),
});
provide(
	"meetingTitle",
	computed(() => {
		if (!session.isLoggedIn) {
			return meetingId.value;
		}
		return meetingTitle.value;
	}),
);

// --- Computed properties ---
const isConnecting = computed(() => connectionState.isConnecting);
const hasConnectionError = computed(() => !!connectionState.connectionError);
const isInLobby = computed(() => lobbyStore.isInLobby || false);
const isWaitingForApproval = computed(
	() => lobbyStore.isWaitingForApproval || false,
);
const isCheckingMeeting = ref(true);
const meetingNotFound = ref(false);
const meetingErrorMessage = ref("");

async function validateMeeting() {
	isCheckingMeeting.value = true;
	meetingNotFound.value = false;
	meetingErrorMessage.value = "";

	const id = meetingId.value;
	const codeRegex = /^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$/;
	if (!id || !codeRegex.test(id)) {
		isCheckingMeeting.value = false;
		meetingNotFound.value = true;
		meetingErrorMessage.value = "Mã cuộc họp không hợp lệ hoặc đường dẫn sai định dạng.";
		return false;
	}

	try {
		const accessData = await frappeRequest({
			url: "meet.api.meeting.check_meeting_access",
			params: {
				meeting_id: id,
			},
		});

		if (!accessData || !(accessData as any).exists) {
			meetingNotFound.value = true;
			meetingErrorMessage.value = "Cuộc họp không tồn tại hoặc đã kết thúc.";
			return false;
		}

		if ((accessData as any).host_only_chat !== undefined) {
			chatStore.hostOnlyChat = !!(accessData as any).host_only_chat;
		}

		if (!session.isLoggedIn && !(accessData as { allow_guest?: boolean }).allow_guest) {
			const loginUrl = `/login?redirect-to=${encodeURIComponent(`/meet/${id}`)}`;
			window.location.href = loginUrl;
			return false;
		}

		return true;
	} catch (error) {
		console.error("Failed to check meeting access:", error);
		meetingNotFound.value = true;
		meetingErrorMessage.value = "Cuộc họp không tồn tại hoặc đã kết thúc.";
		return false;
	} finally {
		isCheckingMeeting.value = false;
	}
}

const showPreview = computed(() => {
	if (isCheckingMeeting.value || meetingNotFound.value) {
		return false;
	}
	const isUnauthenticatedGuest = !session.isLoggedIn && !isGuestSession.value;
	if (isUnauthenticatedGuest) {
		return true;
	}

	if (isGuestSession.value) {
		return false;
	}
	if (lobbyStore.isInLobby) {
		return false;
	}
	if (lobbyStore.isWaitingForApproval) {
		return false;
	}
	const inPreview = connectionState.isInPreview;
	const joinRequestRejected = lobbyStore.isJoinRequestRejected;
	return inPreview || joinRequestRejected;
});

const isPeopleOpen = ref(false);

const activePanel = computed(() => {
	if (chatStore.isChatOpen) return "chat";
	if (isPeopleOpen.value) return "people";
	return null;
});

const participantsForPeoplePanel = computed<Record<string, Participant>>(
	() => participantStore.participants as Record<string, Participant>,
);

const { isMobile } = useResponsiveGrid();

const panelWidth = computed(() => {
	if (!activePanel.value) return "0rem";
	if (isMobile.value) return "0rem";
	return "24rem";
});

const isHandRaised = computed(() => {
	const currentUserId = currentUser.currentUser.value?.user_id as string;
	return currentUserId ? !!raiseHandStore.raisedHands?.[currentUserId] : false;
});

// --- Refs ---
const chatNotificationQueue = ref<InstanceType<
	typeof ChatNotificationQueue
> | null>(null);
const isReactionPickerOpen = ref(false);
const isFullscreen = ref(false);
const isToolbarVisible = ref(true);

function showCallEndedScreen() {
	callEnded.value = true;
}

async function rejoinMeeting() {
	callEnded.value = false;
	connectionState.$reset();
	if (session.isLoggedIn) {
		await sfuConnection.joinMeetingRoom();
		return;
	}
	connectionState.isInPreview = true;
}

// --- Extracted handlers ---
const handlers = useMeetingHandlers({
	connectionState,
	mediaState,
	participantStore,
	chatStore,
	lobbyStore,
	reactionStore,
	raiseHandStore,
	gridLayout,
	currentUser,
	sfuConnection,
	mediaControls,
	lobby,
	meetingDoc: meetingDoc as unknown as MeetingDocLike,
	meetingId: meetingId.value,
	isCurrentUserHost,
	isPeopleOpen,
	notifiedLobbyUsers,
	router,
});

const {
	resetToPreview,
	joinMeetingFromPreview,
	handleGuestJoinComplete,
	leaveWaitingRoom,
	leaveLobby,
	goHome,
	tryJoinAgain,
	toggleChat,
	handleMuteParticipant,
	handleKickParticipant,
	handleLowerHand,
	handlePromoteToCohost,
	handleApproveLobbyUser,
	handleApproveAllLobbyUsers,
	handleRejectLobbyUser,
	handleNotificationClick,
	toggleFullscreen,
	handleReportProblem,
	handleDeviceChanged,
} = handlers;

// --- Local UI state ---
const togglePeople = () => {
	isPeopleOpen.value = !isPeopleOpen.value;
	if (isPeopleOpen.value) {
		chatStore.isChatOpen = false;
	}
};

const toggleReactions = (payload: string) => {
	reactions.onSendReaction(payload);
	isReactionPickerOpen.value = false;
};

const syncFullscreenState = () => {
	isFullscreen.value = !!document.fullscreenElement;
};

const setSinkIdOnVideoElements = async (sinkId: string) => {
	const videoElements = document.querySelectorAll("video");
	const promises = [];
	for (const videoEl of videoElements) {
		promises.push(
			(videoEl as HTMLVideoElement).setSinkId(sinkId).catch(() => {}),
		);
	}

	if (sfuConnection.sfuManager.value?.videoManager) {
		for (const [, audioElement] of sfuConnection.sfuManager.value.videoManager
			.audioElements) {
			promises.push(audioElement.setSinkId(sinkId).catch(() => {}));
		}
	}

	await Promise.all(promises);
};

// --- Lifecycle ---
onMounted(async () => {
	// get wasJustCreated before resetting stores else it'll be reset to false
	const wasJustCreated = connectionState.justCreated;

	// Reset all stores
	connectionState.$reset();
	mediaState.$reset();
	participantStore.$reset();
	chatStore.$reset();
	lobbyStore.$reset();
	reactionStore.$reset();
	raiseHandStore.$reset();
	gridLayout.resetGridLayout();
	currentUser.setCurrentUser({
		user_id: "",
		name: "",
		full_name: "",
		avatar: "",
	});

	window.addEventListener("keydown", keyboardShortcuts.handleKeyDown);
	window.addEventListener("keyup", keyboardShortcuts.handleKeyUp);
	document.addEventListener("fullscreenchange", syncFullscreenState);
	const isValid = await validateMeeting();
	if (!isValid) return;

	// Setup event handlers
	chat.setupChatEvents(chatNotificationQueue.value);
	reactions.setupReactionEvents();
	raiseHand.setupRaiseHandEvents();

	// Setup notification context watchers

	if (!session.isLoggedIn) {
		await mediaControls.initializeCamera();
		if (selectedSpeakerId.value) {
			await mediaControls.applySpeakerDevice();
		}
		connectionState.isInPreview = true;
		return;
	}

	// Setup current user
	currentUser.setCurrentUser({
		user_id: session.user?.sessionUser || "",
		name: session.user?.full_name || session.user?.sessionUser || "",
		full_name: session.user?.full_name || "",
		avatar: session.user?.avatar || "",
	});

	// Initialize camera
	await mediaControls.initializeCamera();

	if (selectedSpeakerId.value) {
		await mediaControls.applySpeakerDevice();
	}

	// Auto-join if just created
	if (wasJustCreated) {
		connectionState.justCreated = false;
		await joinMeetingFromPreview();
	}
});

onUnmounted(() => {
	window.removeEventListener("keydown", keyboardShortcuts.handleKeyDown);
	window.removeEventListener("keyup", keyboardShortcuts.handleKeyUp);
	document.removeEventListener("fullscreenchange", syncFullscreenState);
});

// Watch for localVideo element and localStream connection
watch(
	[
		() => mediaState.localVideo,
		() => mediaState.localStream,
		() => mediaState.processedStream,
	],
	async ([videoElement, stream, _processedStream]) => {
		if (videoElement && stream) {
			try {
				// Prefer processed stream (with background effects) over raw local stream
				const streamToUse = mediaState.processedStream || stream;
				const currentStreamId = streamToUse.id;
				const trackedStreamId = (videoElement as HTMLElement).dataset
					?.sourceStreamId;

				if (trackedStreamId !== currentStreamId) {
					const videoTracks = streamToUse.getVideoTracks();
					if (videoTracks.length > 0) {
						(videoElement as HTMLVideoElement).srcObject = new MediaStream(
							videoTracks,
						);
					} else {
						(videoElement as HTMLVideoElement).srcObject = streamToUse;
					}
					(videoElement as HTMLElement).dataset.sourceStreamId =
						currentStreamId;
					(videoElement as HTMLVideoElement).muted = true;
					await (videoElement as HTMLVideoElement).play();
				}

				if (
					selectedSpeakerId.value &&
					typeof (videoElement as HTMLVideoElement).setSinkId === "function"
				) {
					try {
						await (videoElement as HTMLVideoElement).setSinkId(
							selectedSpeakerId.value,
						);
					} catch (error) {
						console.warn("Could not set speaker for local video:", error);
					}
				}
			} catch (error) {
				console.warn("Could not play local video:", error);
			}
		}
	},
	{ immediate: true },
);

watch(selectedSpeakerId, async (newSpeakerId) => {
	if (
		newSpeakerId &&
		deviceManager.isDeviceAvailable(newSpeakerId, "speaker")
	) {
		await setSinkIdOnVideoElements(newSpeakerId);
	}
});

// Watch lobby users for notification tracking
watch(
	() => lobbyStore.lobbyUsers,
	(newUsers, oldUsers) => {
		if (isCurrentUserHost.value) {
			const newUserIds = new Set((newUsers || []).map((u) => u.userId));
			const oldUserIds = new Set((oldUsers || []).map((u) => u.userId));
			for (const userId of oldUserIds) {
				if (!newUserIds.has(userId)) {
					notifiedLobbyUsers.value.add(userId);
				}
			}
		}
	},
	{ immediate: true },
);

watch(
	() => chatStore.hostOnlyChat,
	(isRestricted, oldValue) => {
		if (
			isRestricted !== oldValue &&
			(isCurrentUserHost.value || isCurrentUserCohost.value) &&
			sfuConnection.sfuClient?.isConnected()
		) {
			chat.toggleRestriction(isRestricted);
		}
	},
);

watch(meetingId, async () => {
	await validateMeeting();
});
</script>
