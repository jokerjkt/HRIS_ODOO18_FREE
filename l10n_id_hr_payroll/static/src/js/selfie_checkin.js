/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class SelfieCheckIn extends Component {
    setup() {
        this.state = useState({
            mode: "idle", // idle, camera, capturing, sending, done, error
            action: "check_in", // check_in or check_out
            latitude: null,
            longitude: null,
            accuracy: null,
            gpsReady: false,
            gpsError: null,
            photoData: null,
            result: null,
            errorMsg: null,
            countdown: 0,
            facingMode: "user", // front camera for selfie
        });

        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this.stream = null;
        this.countdownTimer = null;

        this.rpc = useService("rpc");
        this.notification = useService("notification");

        onMounted(() => {
            this._startGPS();
        });

        onWillUnmount(() => {
            this._stopCamera();
            if (this.countdownTimer) {
                clearInterval(this.countdownTimer);
            }
        });
    }

    // ── GPS ──────────────────────────────────────────────────────────────

    _startGPS() {
        if (!navigator.geolocation) {
            this.state.gpsError = "GPS tidak tersedia di browser ini";
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                this.state.latitude = pos.coords.latitude;
                this.state.longitude = pos.coords.longitude;
                this.state.accuracy = pos.coords.accuracy;
                this.state.gpsReady = true;
                this.state.gpsError = null;
            },
            (err) => {
                this.state.gpsError = `GPS Error: ${err.message}`;
                this.state.gpsReady = false;
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 30000,
            }
        );
    }

    // ── Camera ───────────────────────────────────────────────────────────

    async _startCamera() {
        try {
            this.state.mode = "camera";
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: this.state.facingMode,
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                },
                audio: false,
            });

            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                this.videoRef.el.play();
            }
        } catch (err) {
            this.state.mode = "idle";
            this.state.errorMsg = `Kamera error: ${err.message}`;
            this.notification.add(this.state.errorMsg, { type: "danger" });
        }
    }

    _stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
    }

    _capturePhoto() {
        const video = this.videoRef.el;
        const canvas = this.canvasRef.el;
        if (!video || !canvas) return null;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0);

        // Add timestamp overlay
        ctx.fillStyle = "rgba(0,0,0,0.6)";
        ctx.fillRect(0, canvas.height - 40, canvas.width, 40);
        ctx.fillStyle = "#ffffff";
        ctx.font = "14px monospace";
        const now = new Date().toLocaleString("id-ID");
        ctx.fillText(
            `${now} | Lat: ${this.state.latitude?.toFixed(6)} | Lng: ${this.state.longitude?.toFixed(6)}`,
            10,
            canvas.height - 15
        );

        return canvas.toDataURL("image/jpeg", 0.8);
    }

    // ── Actions ──────────────────────────────────────────────────────────

    async onStartCamera() {
        this.state.errorMsg = null;
        this.state.photoData = null;
        this.state.result = null;
        await this._startCamera();
    }

    onSwitchCamera() {
        this.state.facingMode =
            this.state.facingMode === "user" ? "environment" : "user";
        this._stopCamera();
        this._startCamera();
    }

    onCapture() {
        const photo = this._capturePhoto();
        if (photo) {
            this.state.photoData = photo;
            this._stopCamera();
            this.state.mode = "capturing";
        }
    }

    onRetake() {
        this.state.photoData = null;
        this.state.mode = "camera";
        this._startCamera();
    }

    async onSubmit() {
        if (!this.state.gpsReady) {
            this.state.errorMsg = "GPS belum siap. Tunggu beberapa saat.";
            return;
        }

        this.state.mode = "sending";
        this.state.errorMsg = null;

        try {
            // Get device info
            const deviceInfo = navigator.userAgent;

            // Prepare photo base64 (remove data:image/jpeg;base64, prefix)
            let photoB64 = "";
            if (this.state.photoData) {
                photoB64 = this.state.photoData.split(",")[1] || "";
            }

            const result = await this.rpc("/l10n_id_hr_payroll/selfie_checkin", {
                latitude: this.state.latitude,
                longitude: this.state.longitude,
                accuracy: this.state.accuracy,
                photo: photoB64,
                device_type: "mobile",
                device_info: deviceInfo,
            });

            if (result.success) {
                this.state.result = result;
                this.state.mode = "done";
                this.state.action =
                    result.action === "check_out" ? "check_out" : "check_in";

                this.notification.add(
                    `Absensi berhasil: ${result.action === "check_out" ? "Check Out" : "Check In"} — ${result.employee}`,
                    { type: "success" }
                );
            } else {
                this.state.errorMsg = result.error || "Gagal mengirim absensi";
                this.state.mode = "idle";
                this.notification.add(this.state.errorMsg, { type: "danger" });
            }
        } catch (err) {
            this.state.errorMsg = `Error: ${err.message || err}`;
            this.state.mode = "idle";
            this.notification.add(this.state.errorMsg, { type: "danger" });
        }
    }

    onReset() {
        this.state.mode = "idle";
        this.state.photoData = null;
        this.state.result = null;
        this.state.errorMsg = null;
        this._startGPS();
    }
}

SelfieCheckIn.template = "l10n_id_hr_payroll.SelfieCheckIn";

registry.category("actions").add("l10n_id_hr_payroll.selfie_checkin", SelfieCheckIn);
