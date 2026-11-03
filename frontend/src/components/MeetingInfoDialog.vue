<template>
	<Dialog v-model="show" :options="{ title: 'Thông tin cuộc họp' }">
		<template #body-content>
			<div class="space-y-4">
				<div class="space-y-2">
					<label class="text-sm font-medium text-gray-700">Mã cuộc họp</label>
					<ClickToCopyField :textContent="meetingId" :breakLines="false" />
				</div>

				<div class="space-y-2">
					<label class="text-sm font-medium text-gray-700">Liên kết cuộc họp</label>
					<ClickToCopyField :textContent="meetingUrl" :breakLines="false" />
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui";
import { computed } from "vue";
import ClickToCopyField from "./ClickToCopyField.vue";

const props = defineProps<{
	modelValue?: boolean;
	meetingId: string;
	meetingTitle?: string;
}>();

const emit = defineEmits<{
	"update:modelValue": [value: boolean];
}>();

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const meetingUrl = computed(() => window.location.href);
</script>
