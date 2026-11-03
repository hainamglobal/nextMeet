<template>
	<SettingsLayoutBase :description="'Thiết lập âm thanh và micrô'">
		<template #title>
			Audio
		</template>
		<template #content>
			<div class="space-y-6">
				<Switch
					class="w-full !px-0"
					label="Khử tiếng ồn"
					description="Giảm tiếng ồn xung quanh thu vào micrô"
					v-model="noiseCancellationEnabledLocal"
				/>
				<Switch
					class="w-full !px-0"
					label="Nhấn để nói"
					description="Giữ phím cách để bật tiếng micrô"
					v-model="pushToTalkEnabledLocal"
				/>
			</div>
		</template>
	</SettingsLayoutBase>
</template>

<script setup lang="ts">
import { Switch } from "frappe-ui";
import { type Ref, ref, watch } from "vue";
import {
	noiseCancellationEnabled,
	pushToTalkEnabled,
	setNoiseCancellationEnabled,
	setPushToTalkEnabled,
} from "../../data/mediaPreferences";
import SettingsLayoutBase from "./SettingsLayoutBase.vue";

const noiseCancellationEnabledLocal: Ref<boolean> = ref(
	noiseCancellationEnabled.value,
);

watch(noiseCancellationEnabledLocal, (newValue) => {
	setNoiseCancellationEnabled(newValue);
});

watch(noiseCancellationEnabled, (newValue) => {
	noiseCancellationEnabledLocal.value = newValue;
});

const pushToTalkEnabledLocal: Ref<boolean> = ref(pushToTalkEnabled.value);

watch(pushToTalkEnabledLocal, (newValue) => {
	setPushToTalkEnabled(newValue);
});

watch(pushToTalkEnabled, (newValue) => {
	pushToTalkEnabledLocal.value = newValue;
});
</script>
