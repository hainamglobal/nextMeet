<template>
	<SettingsLayoutBase
		:description="'Tùy chỉnh âm báo cho các sự kiện trong cuộc họp'"
	>
		<template #title>
			Thông báo
		</template>
		<template #content>
			<div class="space-y-6">
				<Switch
					class="w-full"
					label="Bật âm thanh thông báo"
					description="Phát âm thanh cho mọi sự kiện trong cuộc họp"
					v-model="notificationChimesEnabledLocal"
				/>
			</div>
		</template>
	</SettingsLayoutBase>
</template>

<script setup lang="ts">
import { Switch } from "frappe-ui";
import { type Ref, ref, watch } from "vue";
import {
	notificationChimesEnabled,
	setNotificationChimesEnabled,
} from "../../data/notificationPreferences";
import SettingsLayoutBase from "./SettingsLayoutBase.vue";

const notificationChimesEnabledLocal: Ref<boolean> = ref(
	notificationChimesEnabled.value,
);

watch(notificationChimesEnabledLocal, (newValue) => {
	setNotificationChimesEnabled(newValue);
});
</script>
