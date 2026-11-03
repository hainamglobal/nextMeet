<!-- Vibe coded file meant only for testing audio notifications -->

<template>
	<div class="min-h-screen bg-gray-50 flex items-center justify-center p-8">
		<div class="max-w-2xl mx-auto">
			<div class="bg-white rounded-lg shadow-lg p-8">
				<div class="text-center mb-8">
					<h1 class="text-3xl font-bold text-gray-900 mb-2">Kiểm tra âm báo</h1>
					<p class="text-gray-600">Kiểm tra và điều chỉnh âm thanh thông báo cuộc họp</p>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
					<!-- Join Notification -->
					<div class="bg-green-50 border border-green-200 rounded-lg p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mr-3">
								<lucide-user-plus class="w-5 h-5 text-green-600" />
							</div>
							<div>
								<h3 class="font-semibold text-green-900">Người tham gia vào</h3>
								<p class="text-sm text-green-700">Có người tham gia cuộc họp</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="green"
							class="w-full"
							@click="playJoinNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							Phát âm báo có người tham gia
						</Button>
						<div class="mt-3 text-xs text-green-600">
							<strong>Hiện tại:</strong> C4 → G4 → E5 → C5 (0.5s, âm lượng 20%)
						</div>
					</div>

					<!-- Leave Notification -->
					<div class="bg-red-50 border border-red-200 rounded-lg p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center mr-3">
								<lucide-user-minus class="w-5 h-5 text-red-600" />
							</div>
							<div>
								<h3 class="font-semibold text-red-900">Người rời đi</h3>
								<p class="text-sm text-red-700">Có người rời cuộc họp</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="red"
							class="w-full"
							@click="playLeaveNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							Phát âm báo có người rời đi
						</Button>
						<div class="mt-3 text-xs text-red-600">
							<strong>Hiện tại:</strong> G4 → E4 → C4 (0.4s, âm lượng 20%)
						</div>
					</div>

					<!-- Join Request Notification -->
					<div class="bg-blue-50 border border-blue-200 rounded-lg p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
								<lucide-user-check class="w-5 h-5 text-blue-600" />
							</div>
							<div>
								<h3 class="font-semibold text-blue-900">Yêu cầu tham gia</h3>
								<p class="text-sm text-blue-700">Có người yêu cầu tham gia</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="blue"
							class="w-full"
							@click="playJoinRequestNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							Phát âm báo yêu cầu tham gia
						</Button>
						<div class="mt-3 text-xs text-blue-600">
							<strong>Hiện tại:</strong> F4 → A4 → F4 → C5 (0.6s, âm lượng 25%)
						</div>
					</div>

					<!-- Chat Notification -->
					<div class="bg-purple-50 border border-purple-200 rounded-lg p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-3">
								<lucide-message-circle class="w-5 h-5 text-purple-600" />
							</div>
							<div>
								<h3 class="font-semibold text-purple-900">Tin nhắn trò chuyện</h3>
								<p class="text-sm text-purple-700">Nhận được tin nhắn mới</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="purple"
							class="w-full"
							@click="playChatNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							Phát âm báo tin nhắn
						</Button>
						<div class="mt-3 text-xs text-purple-600">
							<strong>Hiện tại:</strong> E4 → G4 (0.25s, âm lượng 20%)
						</div>
					</div>

					<!-- Hand Raise Notification -->
					<div class="bg-orange-50 border border-orange-200 rounded-lg p-6">
						<div class="flex items-center mb-4">
							<div class="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center mr-3">
								<lucide-hand class="w-5 h-5 text-orange-600" />
							</div>
							<div>
								<h3 class="font-semibold text-orange-900">Giơ tay</h3>
								<p class="text-sm text-orange-700">Có người giơ tay</p>
							</div>
						</div>
						<Button
							variant="solid"
							theme="orange"
							class="w-full"
							@click="playRaiseHandNotification"
							:disabled="isPlaying"
						>
							<template #prefix>
								<lucide-play class="w-4 h-4" />
							</template>
							Phát âm báo giơ tay
						</Button>
						<div class="mt-3 text-xs text-orange-600">
							<strong>Hiện tại:</strong> C5 → E5 → G5 (0.5s, âm lượng 20%)
						</div>
					</div>
				</div>

				<!-- Test All Button -->
				<div class="mt-8 pt-6 border-t border-gray-200">
					<div class="text-center">
						<Button
							variant="outline"
							size="lg"
							@click="playAllNotifications"
							:disabled="isPlaying"
							class="mb-4"
						>
							<template #prefix>
								<lucide-play-circle class="w-5 h-5" />
							</template>
							Phát lần lượt tất cả âm báo
						</Button>
						<p class="text-sm text-gray-500">
							Phát lần lượt từng âm thanh, cách nhau 1 giây
						</p>
					</div>
				</div>

				<!-- Instructions -->
				<div class="mt-6 p-4 bg-gray-50 rounded-lg">
					<h4 class="font-semibold text-gray-900 mb-2">Hướng dẫn kiểm tra:</h4>
					<ul class="text-sm text-gray-600 space-y-1">
						<li>• Nhấn từng nút để kiểm tra từng âm báo</li>
						<li>• Chọn "Phát tất cả" để so sánh lần lượt các âm thanh</li>
						<li>• Chỉnh tần số/thời lượng trong <code class="bg-gray-200 px-1 rounded">audioNotifications.ts</code></li>
						<li>• Tải lại trang sau khi sửa mã để kiểm tra thay đổi</li>
						<li>• Kiểm tra bảng điều khiển trình duyệt nếu có lỗi AudioContext</li>
					</ul>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui";
import { ref } from "vue";
import audioNotificationManager from "../utils/audioNotifications";

const isPlaying = ref(false);

// Play individual notifications
const playJoinNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playJoinNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playLeaveNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playLeaveNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playJoinRequestNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playJoinRequestNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playChatNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playChatNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

const playRaiseHandNotification = async () => {
	isPlaying.value = true;
	try {
		await audioNotificationManager.playRaiseHandNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};

// Play all notifications in sequence
const playAllNotifications = async () => {
	isPlaying.value = true;

	try {
		await audioNotificationManager.playJoinNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playLeaveNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playJoinRequestNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playChatNotification();
		await new Promise((resolve) => setTimeout(resolve, 1000));

		await audioNotificationManager.playRaiseHandNotification();
	} finally {
		setTimeout(() => {
			isPlaying.value = false;
		}, 100);
	}
};
</script>
