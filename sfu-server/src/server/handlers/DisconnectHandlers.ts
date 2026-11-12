import type { Socket } from 'socket.io';
import { loggers } from '../../utils/logger';
import { publishPresence } from '../PresenceWebhook';
import type { HandlerDeps } from './Handler';
import { isRealParticipant } from './utils';

export function registerDisconnectHandlers(deps: HandlerDeps) {
	return (socket: Socket) => {
		socket.on('disconnect', async () => {
			deps.authManager.cleanupSocket(socket);

			loggers.socketHandler.info(
				'Disconnected: %s (User: %s, Scope: %s)',
				socket.id,
				socket.participantId,
				socket.scope,
			);

			const roomId = socket.roomId;
			const participantId = socket.participantId;

			if (roomId && participantId) {
				deps.registry.removeSocket(roomId, socket.id);
				if (socket.scope === 'full') {
					deps.registry.scheduleParticipantDisconnect(roomId, participantId, async () => {
						try {
							if (!deps.registry.removeParticipant(roomId, participantId)) return;
							await deps.mediasoup.removePeer(roomId, participantId);
							void publishPresence(
								deps.mediasoup,
								roomId,
								socket.meetingId,
								socket.site,
								socket.presenceHostName,
								socket.presenceCallbackUrl,
							);
							if (isRealParticipant(participantId)) {
								deps.registry.emitParticipantEvent(roomId, 'participant_left', participantId);
							}
							if (deps.registry.hasRaisedHand(roomId, participantId)) {
								deps.registry.clearRaisedHand(roomId, participantId);
								deps.registry.emitToFullAccessParticipants(roomId, 'hand_raised', {
									participantId, raised: false, timestamp: new Date().toISOString(),
								});
							}
							loggers.socketHandler.info('Cleaned up user %s from room %s', participantId, roomId);
							if (deps.registry.isEmpty(roomId)) {
								deps.registry.cleanupRoom(roomId);
								await deps.mediasoup.closeRoom(roomId);
							}
						} catch (error) {
							loggers.socketHandler.error('Error handling delayed disconnect: %s', error);
						}
					});
				}
			}
		});
	};
}
