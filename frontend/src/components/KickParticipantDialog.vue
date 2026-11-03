<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Remove Participant',
			size: 'sm',
			actions: [
				{
					label: 'Hủy',
					variant: 'subtle',
					onClick: () => { showDialog = false; }
				},
				{
					label: 'Xóa',
					variant: 'solid',
					theme: 'red',
					onClick: handleKickConfirm
				}
			]
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-base text-ink-gray-7">
					Bạn có chắc muốn xóa <strong>{{ participantName }}</strong> khỏi cuộc họp không?
				</p>
				<FormControl
					label="Chặn người này khỏi cuộc họp?"
					type="checkbox"
					v-model="banFromMeeting"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, FormControl } from "frappe-ui";
import { computed, ref } from "vue";

interface Props {
	participantName: string;
	modelValue?: boolean;
}

interface Emits {
	(e: "update:modelValue", value: boolean): void;
	(e: "confirm", ban: boolean): void;
}

const props = withDefaults(defineProps<Props>(), {
	modelValue: false,
});

const emit = defineEmits<Emits>();

const banFromMeeting = ref(false);

const showDialog = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit("update:modelValue", value),
});

const handleKickConfirm = () => {
	emit("confirm", banFromMeeting.value);
	banFromMeeting.value = false;
	showDialog.value = false;
};
</script>
