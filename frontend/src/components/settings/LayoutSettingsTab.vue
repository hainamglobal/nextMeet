<template>
	<SettingsLayoutBase
		:description="'Tùy chỉnh bố cục giao diện cuộc họp'"
	>
		<template #title>
			Bố cục
		</template>
		<template #content>
			<div class="space-y-6">
				<Switch
					class="w-full !px-0"
					label="Tự động ẩn thanh công cụ"
					description="Tự động ẩn thanh công cụ sau 10 giây không hoạt động"
					v-model="autoHideToolbarLocal"
				/>
			</div>
		</template>
	</SettingsLayoutBase>
</template>

<script setup lang="ts">
import { Switch } from "frappe-ui";
import { type Ref, ref, watch } from "vue";
import {
	autoHideToolbar,
	setAutoHideToolbar,
} from "../../data/mediaPreferences";
import SettingsLayoutBase from "./SettingsLayoutBase.vue";

const autoHideToolbarLocal: Ref<boolean> = ref(autoHideToolbar.value);

watch(autoHideToolbarLocal, (newValue) => {
	setAutoHideToolbar(newValue);
});

watch(autoHideToolbar, (newValue) => {
	autoHideToolbarLocal.value = newValue;
});
</script>
