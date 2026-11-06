<template>
	<div class="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
		<div class="bg-surface-white rounded-xl shadow-2xl p-8 max-w-md mx-4 text-center space-y-4">
			<div class="w-12 h-12 mx-auto rounded-full flex items-center justify-center mb-4 bg-gradient-to-br from-amber-100 to-yellow-100">
				<lucide-clock class="w-6 h-6 text-amber-600 animate-pulse" />
			</div>

			<h2 class="text-xl font-semibold text-ink-gray-9">
				Đang chờ được duyệt
			</h2>

			<p class="text-ink-gray-6 text-base">
				Chủ phòng sẽ cho bạn vào cuộc họp trong ít phút nữa.
			</p>

			<div class="flex flex-col gap-3">
				<Button
					variant="outline"
					@click="$emit('leave')"
					class="w-full"
				>
					<template #prefix>
						<lucide-x class="w-4 h-4" />
					</template>
					Rời cuộc họp
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui";

defineEmits<{
	leave: [];
}>();
</script>
