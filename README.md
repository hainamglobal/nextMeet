<div align="center">

<a href="https://github.com/frappe/meet">
    <img src="https://frappe.io/files/meet_logo.png" height="80" alt="Frappe Meet Logo">
</a>

<h1>Frappe Meet</h1>

**Simple, High Quality Video Conferencing**

</div>

<img width="2560" height="1457" alt="Frappe Meet screenshot" src="https://github.com/user-attachments/assets/aa124052-dc35-4f0d-b974-d47d2d813e70" />

<br>

> [!IMPORTANT]  
> Frappe Meet is archived and is now part of [Frappe Suite](https://github.com/frappe/suite).

## Frappe Meet

Frappe Meet is a video conferencing app built with simplicity, quality, and reliability in mind.

### Key Features

- **High-quality meetings:** Low-latency, scalable multi-party video with adaptive streaming.
- **Meeting Management:** Create meetings and control meeting access for guests, participants, or hosts.
- **Multimedia features:** Features like background effects, noise suppression, and push-to-talk elevate the meeting experience. 

### Under the Hood

- [Mediasoup](https://github.com/versatica/mediasoup): Cutting Edge WebRTC Video Conferencing.
- [Frappe Framework](https://github.com/frappe/frappe): A full-stack web application framework.
- [Frappe UI](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface.

### Self-Hosting

Deploying Frappe Meet on your own server is quick and easy using our automated Docker Compose setup. For complete instructions, check out the [Self-Hosting Guide](deploy/README.md).

### Local Development

#### Prerequisites

- Frappe-bench set up locally ([installation guide](https://docs.frappe.io/framework/user/en/installation))
- Node.js and yarn

#### Step 1: Set up the Backend

1. In your frappe-bench directory, run the following commands in separate terminal sessions:

   ```sh
   # Terminal 1 - Start the Frappe server
   cd frappe-bench
   bench start
   ```

2. Open a new terminal session for the remaining setup:
   ```sh
   cd frappe-bench
   bench new-site meet.localhost
   bench get-app meet
   bench --site meet.localhost install-app meet
   bench --site meet.localhost add-to-hosts
   bench --site meet.localhost browse --user Administrator
   ```

#### Step 2: Set up the Frontend

1. Open a new terminal session and navigate to the meet app:

   ```sh
   cd frappe-bench/apps/meet
   ```

2. Install frontend dependencies and start the dev server:
   ```sh
   cd frontend
   yarn install
   yarn dev
   ```

#### Step 3: Set up the SFU Server

1. Open a new terminal session and navigate to the SFU server:

   ```sh
   cd frappe-bench/apps/meet/sfu-server
   ```

2. Copy the example environment file and configure it:

   ```sh
   cp .env.example .env
   ```

   Edit `.env` and set:
   - `JWT_SECRET` — must match `sfu_secret` in your Frappe site config

3. Set the matching secret in Frappe site config:

   ```sh
   cd frappe-bench
   bench --site meet.localhost set-config sfu_secret "your_secret"
   ```

4. Install dependencies and start the SFU server:
   ```sh
   cd frappe-bench/apps/meet/sfu-server
   yarn install
   yarn dev
   ```

### License

AGPL-3.0

## NextGRP Meet integration

The integration implementation is organized into API, service, client, and config layers. The MTP app exposes a thin local route that forwards to `meet.api.integration`; this avoids installing the full standalone Meet app on the NextGRP site. Configure the remote backend credentials in the NextGRP site's `site_config.json`:

```json
{
  "meet_backend_url": "https://meet.nextgrp.vn",
  "meet_api_key": "<api-key>",
  "meet_api_secret": "<api-secret>"
}
```

The API key and secret are used only by the server-side client over HTTPS. The credential owner needs the `Meet User` role and access to `Sae Meeting`; remote calls execute as that account.

This integration adds the optional `meeting_title` field to `Sae Meeting`. After deploying the Meet app update to `meet.nextgrp.vn`, run `bench --site <meet-site> migrate` there before using MTP's meeting list and create form.

<br>
<br>
<div align="center">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>
