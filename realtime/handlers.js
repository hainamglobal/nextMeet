const guest_room = (guest_id) => `guest:${guest_id}`;

const meet_handlers = (socket) => {
	socket.on("ping", () => {
		socket.emit("pong");
	});

	// guest specific rooms
	socket.on("guest_subscribe", async (guest_id) => {
		if (!guest_id || typeof guest_id !== "string") {
			return;
		}

		if (!guest_id.startsWith("guest_") || guest_id.length < 10) {
			return;
		}

		// session validation for guest
		socket
			.frappe_request("/api/method/meet.api.meeting.validate_guest_session", {
				guest_id: guest_id,
			})
			.then((res) => res.json())
			.then(({ message }) => {
				if (!message?.valid) {
					return;
				}
				const room = guest_room(guest_id);
				socket.join(room);
			})
			.catch(() => {});
	});

	socket.on("guest_unsubscribe", (guest_id) => {
		if (!guest_id) return;

		const room = guest_room(guest_id);
		socket.leave(room);
	});

	// meeting rooms (general meeting room and host-only room)
	socket.on("meeting_subscribe", async (data) => {
		if (!data) return;
		const meeting_id = typeof data === "string" ? data : data.meeting_id;
		const guest_id = typeof data === "object" ? data.guest_id : null;
		if (!meeting_id) return;

		socket.join(`meeting:${meeting_id}`);

		const checkParams = { meeting_id };
		if (guest_id) {
			checkParams.guest_id = guest_id;
		}

		socket
			.frappe_request("/api/method/meet.api.meeting.check_is_host", checkParams)
			.then((res) => res.json())
			.then(({ message }) => {
				if (message === true || message?.is_host === true) {
					socket.join(`meeting:${meeting_id}:hosts`);
				}
			})
			.catch(() => {});
	});

	socket.on("meeting_unsubscribe", (data) => {
		if (!data) return;
		const meeting_id = typeof data === "string" ? data : data.meeting_id;
		if (!meeting_id) return;

		socket.leave(`meeting:${meeting_id}`);
		socket.leave(`meeting:${meeting_id}:hosts`);
	});
};

module.exports = meet_handlers;