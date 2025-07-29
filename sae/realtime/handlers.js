/**
 * Real-time Socket.IO handlers for Sae Video Conferencing
 * This file is automatically loaded by Frappe's real-time system
 */

function sae_handlers(socket) {
    console.log(`🎥 Sae real-time handler connected for user: ${socket.user}`);

    // WebRTC signaling - relay between clients
    socket.on('webrtc_signal', function(data) {
        try {
            console.log(`📡 WebRTC signal ${data.type} from ${socket.user} for meeting ${data.meeting_id}`);

            // Relay the signal to other participants in the meeting room
            const roomName = `meeting:${data.meeting_id}`;
            socket.to(roomName).emit('webrtc_signal', {
                ...data,
                from_user: socket.user,
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            console.error('Error handling WebRTC signal:', error);
            socket.emit('webrtc_signal_error', { error: error.message });
        }
    });

    // Meeting management
    socket.on('join_meeting', function(data) {
        try {
            console.log(`👥 User ${socket.user} joining meeting ${data.meeting_id}`);

            // Join socket room for real-time communication
            const roomName = `meeting:${data.meeting_id}`;
            socket.join(roomName);

            // Notify other participants immediately
            socket.to(roomName).emit('participant_joined', {
                userId: socket.user,
                userData: data.user_data,
                meetingId: data.meeting_id,
                timestamp: new Date().toISOString()
            });

            // The actual meeting join logic will be handled through API calls
            // Client should call the API endpoint after socket room join

        } catch (error) {
            console.error('Error joining meeting:', error);
            socket.emit('meeting_join_error', { error: error.message });
        }
    });

    socket.on('leave_meeting', function(data) {
        try {
            console.log(`👋 User ${socket.user} leaving meeting ${data.meeting_id}`);

            // Leave socket room
            const roomName = `meeting:${data.meeting_id}`;
            socket.leave(roomName);

            // Notify other participants immediately
            socket.to(roomName).emit('participant_left', {
                userId: socket.user,
                meetingId: data.meeting_id,
                timestamp: new Date().toISOString()
            });

            // The actual meeting leave logic will be handled through API calls

        } catch (error) {
            console.error('Error leaving meeting:', error);
            socket.emit('meeting_leave_error', { error: error.message });
        }
    });

    // Media control
    socket.on('media_control', function(data) {
        try {
            console.log(`🎛️ Media control ${data.action} from ${socket.user}`);

            // Broadcast to meeting participants
            const roomName = `meeting:${data.meeting_id}`;
            socket.to(roomName).emit('media_control_update', {
                userId: socket.user,
                action: data.action,
                meetingId: data.meeting_id,
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            console.error('Error handling media control:', error);
            socket.emit('media_control_error', { error: error.message });
        }
    });

    // Screen sharing
    socket.on('screen_share', function(data) {
        try {
            console.log(`🖥️ Screen share ${data.action} from ${socket.user}`);

            // Broadcast to meeting participants
            const roomName = `meeting:${data.meeting_id}`;
            const eventName = data.action === 'start_share' ? 'screen_share_started' : 'screen_share_stopped';

            socket.to(roomName).emit(eventName, {
                userId: socket.user,
                shareData: data.share_data,
                meetingId: data.meeting_id,
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            console.error('Error handling screen share:', error);
            socket.emit('screen_share_error', { error: error.message });
        }
    });

    // Chat messages
    socket.on('chat_message', function(data) {
        try {
            console.log(`💬 Chat message from ${socket.user}`);

            // Broadcast chat message to all participants in the meeting
            const roomName = `meeting:${data.meeting_id}`;
            const chatData = {
                userId: socket.user,
                message: data.message,
                meetingId: data.meeting_id,
                timestamp: new Date().toISOString()
            };

            // Send to all participants including sender
            socket.to(roomName).emit('meeting_chat_message', chatData);
            socket.emit('meeting_chat_message', chatData);

        } catch (error) {
            console.error('Error handling chat message:', error);
            socket.emit('chat_message_error', { error: error.message });
        }
    });

    // SFU-specific events - these should be handled through API calls
    // The socket handlers just provide immediate feedback and room management
    const sfuEvents = [
        'get_router_capabilities',
        'create_transport',
        'connect_transport',
        'produce_media',
        'consume_media',
        'pause_resume_producer',
        'pause_resume_consumer'
    ];

    sfuEvents.forEach(event => {
        socket.on(event, function(data) {
            try {
                console.log(`🔄 SFU event ${event} from ${socket.user}`);

                // For SFU events, we relay to room participants for coordination
                // but the actual SFU communication happens through API calls
                const roomName = `meeting:${data.meeting_id}`;
                socket.to(roomName).emit(`sfu_${event}`, {
                    ...data,
                    from_user: socket.user,
                    timestamp: new Date().toISOString()
                });

            } catch (error) {
                console.error(`Error handling ${event}:`, error);
                socket.emit(`${event}_error`, { error: error.message });
            }
        });
    });

    // Handle disconnection
    socket.on('disconnect', function() {
        console.log(`🔌 Sae user ${socket.user} disconnected`);

        // Leave all meeting rooms - the socket.io server will handle this automatically
        // Cleanup of meeting state should be handled through API calls or session cleanup
    });

    // Error handling
    socket.on('error', function(error) {
        console.error(`❌ Sae socket error for user ${socket.user}:`, error);

        socket.emit('sae_error', {
            error: error.message,
            timestamp: new Date().toISOString()
        });
    });

    // Ping/pong for connection monitoring
    socket.on('sae_ping', function() {
        socket.emit('sae_pong', {
            timestamp: new Date().toISOString(),
            user: socket.user
        });
    });
}

module.exports = sae_handlers;
