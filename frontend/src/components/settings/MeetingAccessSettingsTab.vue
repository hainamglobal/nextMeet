<template>
	<SettingsLayoutBase
		title="Quyền truy cập cuộc họp"
		description="Quản lý cách người tham gia vào và tương tác trong cuộc họp."
	>
		<template #content>
			<div class="space-y-6">
				<!-- Allow Guest Toggle -->
				<div class="space-y-3">
					<Switch
						class="w-full !px-0"
						label="Cho phép khách"
						description="Cho phép người chưa đăng ký tham gia cuộc họp này"
						v-model="allowGuest"
						:disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
					/>
				</div>

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
								label: 'Hạn chế - Cần chủ trì phê duyệt',
								value: 'restricted',
							},
						]"
						:disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
					/>
				</div>

				<div class="space-y-3">
                    <Switch
                        class="w-full !px-0"
                        label="Chỉ chủ trì được trò chuyện"
                        description="Chỉ chủ trì và đồng chủ trì mới có thể gửi tin nhắn"
                        v-model="hostOnlyChat"
                        :disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
                    />
                </div>

			</div>
		</template>
	</SettingsLayoutBase>
</template>

<script setup lang="ts">
import { debounce, FormControl, Switch, toast } from "frappe-ui";
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
	allowGuest: globalAllowGuest,
	meetingType: globalMeetingType,
} = useMeetingDoc();

const chatStore = useChatStore();

const allowGuest = ref<boolean>(globalAllowGuest.value);
const meetingType = ref<string>(globalMeetingType.value);
const hostOnlyChat = ref<boolean>(chatStore.hostOnlyChat);

const meetingDoc = getMeetingDoc(props.meetingId);

onMounted(async () => {
	try {
		allowGuest.value = globalAllowGuest.value;
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
			allow_guest: allowGuest.value,
			meeting_type: meetingType.value,
			host_only_chat: hostOnlyChat.value,
		});

		await meetingDoc.reload();
	} catch (error) {
		console.error("Failed to update meeting settings:", error);
		toast.error("Không thể cập nhật cài đặt cuộc họp");

		if (meetingDoc.doc?.host_only_chat !== undefined) {
			hostOnlyChat.value = !!meetingDoc.doc.host_only_chat;
		}
	}
}, 300);

watch(hostOnlyChat, (newValue) => {
	chatStore.hostOnlyChat = newValue;
});
watch([allowGuest, meetingType, hostOnlyChat], () => {
	if (!meetingDoc.get.loading) {
		saveSettings();
	}
});
</script>
