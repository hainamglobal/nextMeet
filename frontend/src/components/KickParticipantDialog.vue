<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Xóa người tham gia',
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
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui";
import { computed } from "vue";

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

const showDialog = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit("update:modelValue", value),
});

const handleKickConfirm = () => {
	emit("confirm", false);
	showDialog.value = false;
};
</script>
