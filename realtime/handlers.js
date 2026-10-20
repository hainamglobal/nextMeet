const { frappe_request } = require("../../frappe/realtime/utils");

const guest_room = (guest_id) => `guest:${guest_id}`;

const meet_handlers = (socket) => {
	// guest specific rooms
	socket.on("guest_subscribe", async (guest_id, acknowledge) => {
		const respond = (result) => {
			if (typeof acknowledge === "function") acknowledge(result);
		};
		if (!guest_id || typeof guest_id !== "string") {
			respond({ joined: false });
			return;
		}

		if (!guest_id.startsWith("guest_") || guest_id.length < 10) {
			respond({ joined: false });
			return;
		}

		// session validation for guest
		frappe_request("/api/method/meet.api.meeting.validate_guest_session", socket)
			.type("form")
			.query({ guest_id })
			.then((res) => {
				const message = res.body?.message;
				if (!message?.valid) {
					respond({ joined: false });
					return;
				}
				const room = guest_room(guest_id);
				return Promise.resolve(socket.join(room)).then(() =>
					respond({ joined: true }),
				);
			})
			.catch(() => respond({ joined: false }));
	});

	socket.on("guest_unsubscribe", (guest_id) => {
		if (!guest_id) return;

		const room = guest_room(guest_id);
		socket.leave(room);
	});

	// meeting rooms (general meeting room and host-only room)
	socket.on("meeting_subscribe", async (data, acknowledge) => {
		const respond = (result) => {
			if (typeof acknowledge === "function") acknowledge(result);
		};
		if (!data) {
			respond({ joined: false, is_host: false });
			return;
		}
		const meeting_id = typeof data === "string" ? data : data.meeting_id;
		const guest_id = typeof data === "object" ? data.guest_id : null;
		if (!meeting_id) {
			respond({ joined: false, is_host: false });
			return;
		}

		const checkParams = { meeting_id };
		if (guest_id) {
			checkParams.guest_id = guest_id;
		}

		Promise.resolve(socket.join(`meeting:${meeting_id}`))
			.then(() => {
				return frappe_request(
					"/api/method/meet.api.meeting.check_is_host",
					socket,
				)
					.type("form")
					.query(checkParams)
					.then((res) => {
						return res.body?.message;
					})
					.then(async (message) => {
						const is_host = message === true || message?.is_host === true;
						if (is_host) {
							await socket.join(`meeting:${meeting_id}:hosts`);
						}
						respond({ joined: true, is_host });
					});
			})
			.catch(() => respond({ joined: false, is_host: false }));
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
