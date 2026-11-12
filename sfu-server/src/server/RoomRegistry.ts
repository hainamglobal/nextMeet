import type { Server, Socket } from 'socket.io';
import type {
	ClientToServerEvents,
	ServerToClientEvents,
	UserData,
} from '../types';

export class RoomRegistry {
	private io: Server<ClientToServerEvents, ServerToClientEvents>;
	private fullAccessSockets: Map<string, Set<string>> = new Map();
	private previewSockets: Map<string, Set<string>> = new Map();
	private raisedHands: Record<string, Record<string, string>> = {};
	private hostOnlyChat: Record<string, boolean> = {};
	private activeParticipants: Map<string, Set<string>> = new Map();
	private disconnectTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

	constructor(io: Server<ClientToServerEvents, ServerToClientEvents>) {
		this.io = io;
	}

	addFullAccessSocket(roomId: string, socketId: string): void {
		const set = this.fullAccessSockets.get(roomId) ?? new Set<string>();
		set.add(socketId);
		this.fullAccessSockets.set(roomId, set);
	}

	registerParticipant(roomId: string, participantId: string): boolean {
		this.cancelParticipantDisconnect(roomId, participantId);
		const participants = this.activeParticipants.get(roomId) ?? new Set<string>();
		const alreadyActive = participants.has(participantId);
		participants.add(participantId);
		this.activeParticipants.set(roomId, participants);
		return alreadyActive;
	}

	participantIsActive(roomId: string, participantId: string): boolean {
		return this.activeParticipants.get(roomId)?.has(participantId) ?? false;
	}

	cancelParticipantDisconnect(roomId: string, participantId: string): void {
		const key = `${roomId}:${participantId}`;
		const timer = this.disconnectTimers.get(key);
		if (timer) {
			clearTimeout(timer);
			this.disconnectTimers.delete(key);
		}
	}

	scheduleParticipantDisconnect(
		roomId: string,
		participantId: string,
		cleanup: () => Promise<void> | void,
	): void {
		this.cancelParticipantDisconnect(roomId, participantId);
		const key = `${roomId}:${participantId}`;
		const timer = setTimeout(async () => {
			this.disconnectTimers.delete(key);
			if (!this.participantIsActive(roomId, participantId)) return;
			await cleanup();
		}, 5000);
		this.disconnectTimers.set(key, timer);
	}

	removeParticipant(roomId: string, participantId: string): boolean {
		this.cancelParticipantDisconnect(roomId, participantId);
		const participants = this.activeParticipants.get(roomId);
		if (!participants?.delete(participantId)) return false;
		if (!participants.size) this.activeParticipants.delete(roomId);
		return true;
	}

	addPreviewSocket(roomId: string, socketId: string): void {
		const set = this.previewSockets.get(roomId) ?? new Set<string>();
		set.add(socketId);
		this.previewSockets.set(roomId, set);
	}

	removeSocket(roomId: string, socketId: string): void {
		this.fullAccessSockets.get(roomId)?.delete(socketId);
		this.previewSockets.get(roomId)?.delete(socketId);
	}

	setRaisedHand(roomId: string, peerId: string, isoTimestamp: string): void {
		if (!this.raisedHands[roomId]) this.raisedHands[roomId] = {};
		this.raisedHands[roomId][peerId] = isoTimestamp;
	}

	clearRaisedHand(roomId: string, peerId: string): void {
		delete this.raisedHands[roomId]?.[peerId];
	}

	getRaisedHands(roomId: string): Record<string, string> {
		return this.raisedHands[roomId] ?? {};
	}

	hasRaisedHand(roomId: string, peerId: string): boolean {
		return Boolean(this.raisedHands[roomId]?.[peerId]);
	}

	setHostOnlyChat(roomId: string, enabled: boolean): void {
		this.hostOnlyChat[roomId] = enabled;
	}

	isHostOnlyChat(roomId: string): boolean {
		return Boolean(this.hostOnlyChat[roomId]);
	}

	isEmpty(roomId: string): boolean {
		const fullAccessCount = this.fullAccessSockets.get(roomId)?.size ?? 0;
		const previewCount = this.previewSockets.get(roomId)?.size ?? 0;
		return fullAccessCount === 0 && previewCount === 0;
	}

	cleanupRoom(roomId: string): void {
		for (const participantId of this.activeParticipants.get(roomId) ?? []) {
			this.cancelParticipantDisconnect(roomId, participantId);
		}
		this.fullAccessSockets.delete(roomId);
		this.previewSockets.delete(roomId);
		this.activeParticipants.delete(roomId);
		delete this.raisedHands[roomId];
		delete this.hostOnlyChat[roomId];
	}

	emitToFullAccessParticipants(
		roomId: string,
		event: string,
		data: unknown,
	): void {
		this.emitToScope(this.fullAccessSockets.get(roomId), event, data);
	}

	emitToPreviewParticipants(
		roomId: string,
		event: string,
		data: unknown,
	): void {
		this.emitToScope(this.previewSockets.get(roomId), event, data);
	}

	emitParticipantEvent(
		roomId: string,
		event: 'participant_joined' | 'participant_left',
		participantId: string,
		userData?: UserData,
	): void {
		if (event === 'participant_joined' && userData) {
			this.emitToFullAccessParticipants(roomId, event, {
				roomId,
				participantId,
				userData,
			});
		} else if (event === 'participant_left') {
			this.emitToFullAccessParticipants(roomId, event, {
				roomId,
				participantId,
			});
		}

		if (!participantId.startsWith('preview-')) {
			if (event === 'participant_joined' && userData) {
				this.emitToPreviewParticipants(roomId, event, {
					roomId,
					participantId,
					userData: {
						name: userData.name,
						avatar: userData.avatar,
					} as UserData,
				});
			} else if (event === 'participant_left') {
				this.emitToPreviewParticipants(roomId, event, {
					roomId,
					participantId,
				});
			}
		}
	}

	private emitToScope(
		socketIds: Set<string> | undefined,
		event: string,
		data: unknown,
	): void {
		if (!socketIds) return;
		for (const socketId of socketIds) {
			const socket: Socket | undefined = this.io.sockets.sockets.get(socketId);
			if (socket) {
				// biome-ignore lint/suspicious/noExplicitAny: Internal utility method for type-safe event emission
				(socket as any).emit(event, data);
			}
		}
	}
}
