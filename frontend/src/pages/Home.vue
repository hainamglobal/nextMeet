<template>
	<div class="min-h-screen bg-gray-50 flex items-center justify-center" data-testid="home-page">
		<div class="max-w-lg mx-auto text-center p-8">
			<div class="mb-20">
				<div class="flex justify-center items-center gap-4 mb-6">
					<FrappeMeetingLogo class="h-16 w-16" />
				</div>
				<h1 class="text-2xl font-bold text-gray-900 mb-4">NextMeet</h1>
			</div>

			<div class="space-y-6">
				<div class="space-y-3">
					<form @submit.prevent="joinMeeting" class="space-y-3" data-testid="join-meeting-form">
						<label class="block text-sm font-medium text-gray-700 text-left">
							Tham gia bằng mã hoặc liên kết cuộc họp
						</label>
						<div class="flex gap-3 items-center">
							<div class="flex-1">
								<FormControl
									v-model="meetingCode"
								placeholder="abcd-efgh-ijkl hoặc dán liên kết cuộc họp"
									size="lg"
									:error="meetingCodeError"
									class="text-center sm:text-left"
									data-testid="meeting-code-input"
								/>
							</div>
							<Button
								size="lg"
								type="submit"
								class="whitespace-nowrap px-6 py-3"
								:disabled="!isMeetingInputValid(meetingCode)"
								data-testid="join-meeting-button"
							>
								Tham gia
							</Button>
						</div>
					</form>
				</div>

				<div v-if="session.isLoggedIn" class="flex items-center">
					<div class="flex-grow h-px bg-gray-300"></div>
					<span class="px-4 text-sm text-gray-500">hoặc</span>
					<div class="flex-grow h-px bg-gray-300"></div>
				</div>

				<div v-if="session.isLoggedIn" class="relative inline-block">
					<div class="flex items-center justify-center">
						<Button
							variant="solid"
							size="lg"
							:loading="createMeeting.loading"
							class="whitespace-nowrap px-6 py-3 rounded-r-none"
							@click="() => startNewMeeting('open')"
							data-testid="create-open-meeting-button"
						>
							<template #prefix>
								<lucide-plus class="h-4 w-4" />
							</template>
							Bắt đầu cuộc họp mới
						</Button>

						<Dropdown
							size="lg"
							variant="solid"
							class="rounded-l-none"
							icon="chevron-down"
							:disabled="createMeeting.loading"
							data-testid="create-meeting-options"
							:options="[
								{
									icon: 'lock',
									label: 'Tạo cuộc họp giới hạn',
									onClick: () => startNewMeeting('restricted'),
								},
							]"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import {
	Button,
	createResource,
	Dropdown,
	FormControl,
	toast,
} from "frappe-ui";
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useConnectionState } from "../composables/useConnectionState";
import { session } from "../data/session";
import FrappeMeetingLogo from "../icons/FrappeMeetingLogo.vue";
import { parseMeetingInput } from "../utils/meetingInput";

const router = useRouter();
const connectionState = useConnectionState();
const meetingCode = ref("");
const meetingCodeError = ref("");

const createMeeting = createResource({
	url: "meet.api.meeting.create",
	method: "POST",
	onSuccess: (meeting_code) => {
		router.push({
			name: "Meeting",
			params: { meetingId: meeting_code },
		});
		connectionState.justCreated = true;
	},
	onError: (error) => {
		console.error("Error creating meeting:", error);
		toast.error("Failed to create meeting. Please try again.");
	},
});

const startNewMeeting = (meetingType) => {
	toast.promise(createMeeting.submit({ meeting_type: meetingType }), {
		loading: "Creating meeting...",
		success: "Meeting created successfully!",
		error: "Failed to create meeting. Please try again.",
	});
};

const joinMeeting = () => {
	meetingCodeError.value = "";
	const parsedInput = parseMeetingInput(meetingCode.value, window.location.origin);
	if (!parsedInput) {
		meetingCodeError.value = "Vui lòng nhập mã phòng hợp lệ hoặc dán liên kết cuộc họp.";
		return;
	}

	router.push({
		name: "Meeting",
		params: { meetingId: parsedInput.meetingId },
		hash: parsedInput.hash,
	});
};

const isMeetingInputValid = value => Boolean(parseMeetingInput(value, window.location.origin));
</script>
