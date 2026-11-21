<template>
	<SettingsLayoutBase
		title="Quyền truy cập cuộc họp"
		description="Quản lý cách người tham gia vào và tương tác trong cuộc họp."
	>
		<template #content>
			<div class="space-y-6">
				<!-- Meeting Type Selector -->
				<div>
					<FormControl
						v-model="meetingType"
						type="select"
						label="Kiểm soát người có thể tham gia cuộc họp này"
						:options="[
							{
								label: 'Mở - Mọi người có thể tham gia ngay',
								value: 'open',
							},
							{
								label: 'Hạn chế - Cần chủ phòng phê duyệt',
								value: 'restricted',
							},
						]"
						:disabled="savingSettings || meetingDoc.get.loading"
					/>
				</div>

				<div class="space-y-3">
                    <Switch
                        class="w-full !px-0"
                        label="Chỉ chủ phòng được trò chuyện"
                        description="Chỉ chủ phòng và đồng chủ phòng mới có thể gửi tin nhắn"
                        v-model="hostOnlyChat"
						:disabled="savingSettings || meetingDoc.get.loading"
                    />
                </div>

			</div>
		</template>
	</SettingsLayoutBase>
</template>

<script setup lang="ts">
import { debounce, FormControl, frappeRequest, Switch } from "frappe-ui";
import { onMounted, ref, watch } from "vue";
import { useChatStore } from "@/composables/useChatStore";
import { useConnectionState } from "@/composables/useConnectionState";
import { useMeetingDoc } from "../../composables/useMeetingDoc";
import SettingsLayoutBase from "./SettingsLayoutBase.vue";

const props = defineProps({
	meetingId: {
		type: String,
		required: true,
	},
});

const {
	getMeetingDoc,
	meetingType: globalMeetingType,
} = useMeetingDoc();

const chatStore = useChatStore();
const connectionState = useConnectionState();

const meetingType = ref<string>("");
const hostOnlyChat = ref<boolean>(chatStore.hostOnlyChat);
const settingsReady = ref(false);
const savingSettings = ref(false);

const meetingDoc = getMeetingDoc(props.meetingId);

onMounted(async () => {
	try {
		// The document resource loads asynchronously. Do not initialize to the
		// default "open" value and save it before the server value is available.
		if (!meetingDoc.doc?.meeting_type) {
			await meetingDoc.get.submit();
		}
		meetingType.value = meetingDoc.doc?.meeting_type || globalMeetingType.value || "open";
		if (meetingDoc.doc?.host_only_chat !== undefined) {
			hostOnlyChat.value = !!meetingDoc.doc.host_only_chat;
		}
	} catch (error) {
		console.error("Failed to load meeting settings");
		meetingType.value = globalMeetingType.value || "open";
	} finally {
		settingsReady.value = true;
	}
});

const saveSettings = debounce(async () => {
	if (savingSettings.value) return;

	try {
		savingSettings.value = true;
		const guestId =
			connectionState.guestId || sessionStorage.getItem("guest_id") || undefined;
		const result = await frappeRequest({
			url: "meet.api.meeting.update_meeting_settings",
			params: {
				meeting_id: props.meetingId,
				guest_id: guestId,
				meeting_type: meetingType.value,
				host_only_chat: hostOnlyChat.value,
			},
		});

		if (meetingDoc.doc && result) {
			meetingDoc.doc.meeting_type = result.meeting_type;
			meetingDoc.doc.host_only_chat = !!result.host_only_chat;
		}
	} catch (error) {
		console.error("Failed to update meeting settings:", error);

		if (meetingDoc.doc?.host_only_chat !== undefined) {
			hostOnlyChat.value = !!meetingDoc.doc.host_only_chat;
		}
	} finally {
		savingSettings.value = false;
	}
}, 300);

watch(hostOnlyChat, (newValue) => {
	chatStore.hostOnlyChat = newValue;
});
watch([meetingType, hostOnlyChat], () => {
	if (settingsReady.value && meetingDoc.doc && !meetingDoc.get.loading) {
		saveSettings();
	}
});
</script>
