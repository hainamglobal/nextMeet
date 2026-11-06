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
						:disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
					/>
				</div>

				<div class="space-y-3">
                    <Switch
                        class="w-full !px-0"
                        label="Chỉ chủ phòng được trò chuyện"
                        description="Chỉ chủ phòng và đồng chủ phòng mới có thể gửi tin nhắn"
                        v-model="hostOnlyChat"
                        :disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
                    />
                </div>

			</div>
		</template>
	</SettingsLayoutBase>
</template>

<script setup lang="ts">
import { debounce, FormControl, Switch } from "frappe-ui";
import { onMounted, ref, watch } from "vue";
import { useChatStore } from "@/composables/useChatStore";
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

const meetingType = ref<string>(globalMeetingType.value);
const hostOnlyChat = ref<boolean>(chatStore.hostOnlyChat);

const meetingDoc = getMeetingDoc(props.meetingId);

onMounted(async () => {
	try {
		meetingType.value = globalMeetingType.value;
		if (meetingDoc.doc?.host_only_chat !== undefined) {
			hostOnlyChat.value = !!meetingDoc.doc.host_only_chat;
		}
	} catch (error) {
		console.error("Failed to load meeting settings");
	}
});

const saveSettings = debounce(async () => {
	if (meetingDoc.updateSettings.loading) return;

	try {
		await meetingDoc.updateSettings.submit({
			meeting_type: meetingType.value,
			host_only_chat: hostOnlyChat.value,
		});

		await meetingDoc.reload();
	} catch (error) {
		console.error("Failed to update meeting settings:", error);

		if (meetingDoc.doc?.host_only_chat !== undefined) {
			hostOnlyChat.value = !!meetingDoc.doc.host_only_chat;
		}
	}
}, 300);

watch(hostOnlyChat, (newValue) => {
	chatStore.hostOnlyChat = newValue;
});
watch([meetingType, hostOnlyChat], () => {
	if (!meetingDoc.get.loading) {
		saveSettings();
	}
});
</script>
