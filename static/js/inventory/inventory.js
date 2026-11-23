document.addEventListener("DOMContentLoaded", () => {
    // ── Modal dialog triggers ─────────────────────────────────────────────────
    document.querySelectorAll("[data-open]").forEach((button) => {
        button.addEventListener("click", () => {
            const dlg = document.getElementById(button.dataset.open);
            if (dlg) dlg.showModal();
        });
    });

    document.querySelectorAll("dialog.modal").forEach((dialog) => {
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog || event.target.closest("[data-close]")) dialog.close();
        });
    });

    // ── Update Stock Modal population ─────────────────────────────────────────
    const adjust = document.getElementById("adjustDialog");
    if (adjust) {
        document.querySelectorAll("[data-adjust]").forEach((button) => {
            button.addEventListener("click", () => {
                const form = adjust.querySelector("form");
                form.action = button.dataset.url;
                form.reset();
                document.getElementById("adjustName").textContent =
                    button.dataset.name + (button.dataset.branch ? " \u00b7 " + button.dataset.branch : "");
                document.getElementById("adjustOnHand").textContent = button.dataset.qty + " " + button.dataset.unit;
                document.getElementById("adjust_threshold").value = button.dataset.threshold;
                adjust.showModal();
                document.getElementById("adjust_amount").focus();
            });
        });
    }

    // ── Branch Notification Modal & Confirmation Step ─────────────────────────
    const notifyDialog = document.getElementById("notifyBranchDialog");
    const notifyConfirmDialog = document.getElementById("notifyConfirmDialog");
    const notifyForm = document.getElementById("notifyBranchForm");
    const openConfirmBtn = document.getElementById("openNotifyConfirmBtn");
    const confirmBackBtn = document.getElementById("confirmBackBtn");
    const confirmSendFinalBtn = document.getElementById("confirmSendFinalBtn");

    const targetBranchSelect = document.getElementById("notify_target_branch");
    const medicineSelect = document.getElementById("notify_medicine");
    const quantityInput = document.getElementById("notify_quantity");
    const urgencySelect = document.getElementById("notify_urgency");
    const noteInput = document.getElementById("notify_note");

    // Confirmation elements
    const confirmBranchTitle = document.getElementById("confirmBranchTitle");
    const confirmBranchName = document.getElementById("confirmBranchName");
    const confirmMedRow = document.getElementById("confirmMedRow");
    const confirmMedName = document.getElementById("confirmMedName");
    const confirmQtyRow = document.getElementById("confirmQtyRow");
    const confirmQtyVal = document.getElementById("confirmQtyVal");
    const confirmUrgencyBadge = document.getElementById("confirmUrgencyBadge");
    const confirmNoteRow = document.getElementById("confirmNoteRow");
    const confirmNoteVal = document.getElementById("confirmNoteVal");

    function openNotifyDialog({ branchId, medId, qty, note } = {}) {
        if (!notifyDialog) return;
        if (targetBranchSelect && branchId) {
            targetBranchSelect.value = String(branchId);
        }
        if (medicineSelect && medId) {
            medicineSelect.value = String(medId);
        }
        if (quantityInput && qty) {
            quantityInput.value = qty;
        }
        if (noteInput && note) {
            noteInput.value = note;
        }
        notifyDialog.showModal();
    }

    // When user clicks "Continue to confirm" on the notification dialog
    if (openConfirmBtn && notifyForm) {
        openConfirmBtn.addEventListener("click", () => {
            if (!notifyForm.checkValidity()) {
                notifyForm.reportValidity();
                return;
            }

            const branchOpt = targetBranchSelect.selectedOptions[0];
            const branchText = branchOpt ? branchOpt.textContent.trim() : "Selected Branch";
            const medOpt = medicineSelect.selectedOptions[0];
            const medText = medOpt && medOpt.value ? medOpt.textContent.trim() : "";
            const qtyText = quantityInput.value.trim();
            const urgency = urgencySelect.value;
            const noteText = noteInput.value.trim();

            if (confirmBranchTitle) confirmBranchTitle.textContent = branchText;
            if (confirmBranchName) confirmBranchName.textContent = branchText;

            if (confirmMedRow) {
                if (medText) {
                    confirmMedRow.style.display = "flex";
                    if (confirmMedName) confirmMedName.textContent = medText;
                } else {
                    confirmMedRow.style.display = "none";
                }
            }

            if (confirmQtyRow) {
                if (qtyText) {
                    confirmQtyRow.style.display = "flex";
                    if (confirmQtyVal) confirmQtyVal.textContent = `${qtyText} units`;
                } else {
                    confirmQtyRow.style.display = "none";
                }
            }

            if (confirmUrgencyBadge) {
                confirmUrgencyBadge.textContent = urgency === "urgent" ? "Urgent" : "Normal";
                confirmUrgencyBadge.className = urgency === "urgent" ? "badge badge--danger" : "badge badge--ok";
            }

            if (confirmNoteRow) {
                if (noteText) {
                    confirmNoteRow.style.display = "flex";
                    if (confirmNoteVal) confirmNoteVal.textContent = `"${noteText}"`;
                } else {
                    confirmNoteRow.style.display = "none";
                }
            }

            notifyDialog.close();
            if (notifyConfirmDialog) notifyConfirmDialog.showModal();
        });
    }

    // "Back to edit" returns to the notification dialog
    if (confirmBackBtn) {
        confirmBackBtn.addEventListener("click", () => {
            if (notifyConfirmDialog) notifyConfirmDialog.close();
            if (notifyDialog) notifyDialog.showModal();
        });
    }

    // "Yes, send notification" submits the form
    if (confirmSendFinalBtn && notifyForm) {
        confirmSendFinalBtn.addEventListener("click", () => {
            confirmSendFinalBtn.disabled = true;
            confirmSendFinalBtn.textContent = "Sending...";
            notifyForm.submit();
        });
    }

    // ── Table "Request" Stock Transfer Confirmation ───────────────────────────
    const requestConfirmDialog = document.getElementById("requestConfirmDialog");
    const stockRequestForm = document.getElementById("stockRequestForm");
    const requestMedTitle = document.getElementById("requestMedTitle");

    document.querySelectorAll(".btn-request-stock").forEach((btn) => {
        btn.addEventListener("click", () => {
            const url = btn.dataset.url;
            const medName = btn.dataset.medName || "item";
            if (requestMedTitle) requestMedTitle.textContent = medName;
            if (stockRequestForm) stockRequestForm.action = url;
            if (requestConfirmDialog) requestConfirmDialog.showModal();
        });
    });

    // ── Connect Quick Notify Buttons ──────────────────────────────────────────
    document.querySelectorAll(".btn-quick-notify").forEach((btn) => {
        btn.addEventListener("click", () => {
            openNotifyDialog({
                branchId: btn.dataset.branchId,
                medId: btn.dataset.medId,
                qty: btn.dataset.qty,
                note: `Stock request for ${btn.dataset.medName || "item"}.`,
            });
        });
    });

    // ── Export Dropdown Toggle ────────────────────────────────────────────────
    const exportWrap = document.getElementById("exportDropdownWrap");
    const exportBtn = document.getElementById("exportDropdownBtn");
    const exportMenu = document.getElementById("exportDropdownMenu");

    if (exportBtn && exportMenu) {
        exportBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isHidden = exportMenu.hidden;
            exportMenu.hidden = !isHidden;
            exportBtn.setAttribute("aria-expanded", isHidden ? "true" : "false");
        });

        document.addEventListener("click", (e) => {
            if (!exportMenu.hidden && !exportWrap.contains(e.target)) {
                exportMenu.hidden = true;
                exportBtn.setAttribute("aria-expanded", "false");
            }
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !exportMenu.hidden) {
                exportMenu.hidden = true;
                exportBtn.setAttribute("aria-expanded", "false");
            }
        });
    }

    // ── Interactive MapLibre GL Map & Cross-Branch Stock Locator ─────────────
    const mapContainer = document.getElementById("locatorMap");
    let map = null;
    let markersOnMap = [];
    let routeLine = null;
    let branchData = [];
    let initialBounds = null;
    let is3D = false;

    // OpenFreeMap style URL (Bright style — free, open-source, no API key required)
    const OPENFREEMAP_STYLE = "https://tiles.openfreemap.org/styles/bright";

    if (mapContainer && typeof maplibregl !== "undefined") {
        try {
            branchData = JSON.parse(mapContainer.dataset.branches || "[]");
        } catch (e) {
            branchData = [];
        }

        const defaultCenter = [123.8854, 10.3157]; // Metro Cebu [lng, lat] for MapLibre
        map = new maplibregl.Map({
            container: "locatorMap",
            style: OPENFREEMAP_STYLE,
            center: defaultCenter,
            zoom: 11,
            minZoom: 8,
            maxZoom: 18,
            pitch: 0,
            bearing: 0,
        });

        // Add zoom + compass controls
        map.addControl(new maplibregl.NavigationControl(), "top-right");

        // Helper to add 3D building extrusions from OpenFreeMap vector tiles
        function setup3DBuildings() {
            if (map.getLayer("3d-buildings")) return;
            const layers = map.getStyle().layers;
            let labelLayerId;
            for (let i = 0; i < layers.length; i++) {
                if (layers[i].type === "symbol" && layers[i].layout && layers[i].layout["text-field"]) {
                    labelLayerId = layers[i].id;
                    break;
                }
            }
            try {
                map.addLayer({
                    id: "3d-buildings",
                    source: "openmaptiles",
                    "source-layer": "building",
                    type: "fill-extrusion",
                    minzoom: 13,
                    paint: {
                        "fill-extrusion-color": [
                            "interpolate",
                            ["linear"],
                            ["get", "render_height"],
                            0, "#cbd5e1",
                            50, "#94a3b8",
                            100, "#64748b"
                        ],
                        "fill-extrusion-height": [
                            "interpolate",
                            ["linear"],
                            ["zoom"],
                            13, 0,
                            15.05, ["get", "render_height"]
                        ],
                        "fill-extrusion-base": [
                            "interpolate",
                            ["linear"],
                            ["zoom"],
                            13, 0,
                            15.05, ["get", "render_min_height"]
                        ],
                        "fill-extrusion-opacity": 0.8
                    }
                }, labelLayerId);
            } catch (err) {}
        }

        map.on("load", () => {
            setup3DBuildings();
            if (map.getLayer("3d-buildings")) {
                map.setLayoutProperty("3d-buildings", "visibility", "none");
            }
        });

        // ── Default / 3D Mode Switchers ──────────────────────────────────────
        const btnMapDefault = document.getElementById("btnMapDefault");
        const btnMap3D      = document.getElementById("btnMap3D");

        function setMapMode(mode3d) {
            is3D = mode3d;
            if (is3D) {
                map.easeTo({ pitch: 60, bearing: -20, duration: 800 });
                setup3DBuildings();
                if (map.getLayer("3d-buildings")) {
                    map.setLayoutProperty("3d-buildings", "visibility", "visible");
                }
                if (btnMap3D) {
                    btnMap3D.classList.add("is-active", "btn-primary");
                    btnMap3D.classList.remove("btn-ghost");
                }
                if (btnMapDefault) {
                    btnMapDefault.classList.remove("is-active", "btn-primary");
                    btnMapDefault.classList.add("btn-ghost");
                }
            } else {
                map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
                if (map.getLayer("3d-buildings")) {
                    map.setLayoutProperty("3d-buildings", "visibility", "none");
                }
                if (btnMapDefault) {
                    btnMapDefault.classList.add("is-active", "btn-primary");
                    btnMapDefault.classList.remove("btn-ghost");
                }
                if (btnMap3D) {
                    btnMap3D.classList.remove("is-active", "btn-primary");
                    btnMap3D.classList.add("btn-ghost");
                }
            }
        }

        if (btnMapDefault) btnMapDefault.addEventListener("click", () => setMapMode(false));
        if (btnMap3D) btnMap3D.addEventListener("click", () => setMapMode(true));

        // ── Pin icon helper (SVG data URL) ───────────────────────────────────
        function makePinElement(colorHex, isMine) {
            const el = document.createElement("div");
            el.className = "custom-map-pin";
            el.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="30" height="40" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.25));">
                    <path fill="${colorHex}" stroke="#ffffff" stroke-width="1.6" d="M12 0C5.37 0 0 5.37 0 12c0 8.5 12 20 12 20s12-11.5 12-20C24 5.37 18.63 0 12 0z"/>
                    <circle cx="12" cy="11" r="5" fill="#ffffff"/>
                    ${isMine ? `<circle cx="12" cy="11" r="2.5" fill="${colorHex}"/>` : ""}
                </svg>`;
            el.style.cursor = "pointer";
            return el;
        }

        const PIN_MINE    = "#339989";
        const PIN_OTHER   = "#2B2C28";
        const PIN_NEAREST = "#E07A5F";

        // ── Plot all branch markers ───────────────────────────────────────────
        const lngLats = [];

        branchData.forEach((b) => {
            const isMine = b.is_user_branch;
            const el = makePinElement(isMine ? PIN_MINE : PIN_OTHER, isMine);
            el.dataset.branchId = b.id;

            const popupHtml = `
                <div class="map-popup-card">
                    <strong class="map-popup-title">${b.name}</strong>
                    ${isMine
                        ? '<span class="map-popup-badge">Your Branch</span>'
                        : `<span class="map-popup-dist">${b.distance_km} km away</span>`}
                    <p class="map-popup-addr">${b.address}</p>
                    <p class="map-popup-phone">📞 <a href="tel:${b.phone}">${b.phone || "No phone listed"}</a></p>
                    ${!isMine ? `
                    <div style="margin-top: 8px;">
                        <button type="button" class="btn btn-primary btn-sm btn-popup-notify"
                                data-branch-id="${b.id}" data-branch-name="${b.name}">
                            Notify this branch
                        </button>
                    </div>` : ""}
                </div>`;

            const popup = new maplibregl.Popup({ offset: [0, -38], closeButton: false })
                .setHTML(popupHtml);

            popup.on("open", () => {
                const btn = popup.getElement()?.querySelector(".btn-popup-notify");
                if (btn) {
                    btn.addEventListener("click", () => {
                        openNotifyDialog({ branchId: btn.dataset.branchId });
                    });
                }
            });

            const marker = new maplibregl.Marker({ element: el })
                .setLngLat([b.lng, b.lat])
                .setPopup(popup)
                .addTo(map);

            b._marker = marker;
            b._el = el;
            lngLats.push([b.lng, b.lat]);
        });

        // Fit map to show all branches after style loads
        if (lngLats.length > 0) {
            if (lngLats.length === 1) {
                map.setCenter(lngLats[0]);
                map.setZoom(13);
            } else {
                const bounds = lngLats.reduce(
                    (b, c) => b.extend(c),
                    new maplibregl.LngLatBounds(lngLats[0], lngLats[0])
                );
                initialBounds = bounds;
                map.fitBounds(bounds, { padding: 60, maxZoom: 14 });
            }
        }

        // ── Locator helpers ───────────────────────────────────────────────────
        const searchInput = document.getElementById("mapSearchInput");
        const searchBtn   = document.getElementById("mapSearchBtn");
        const resetBtn    = document.getElementById("mapResetBtn");
        const resultCard  = document.getElementById("locatorResultCard");
        const statusText  = document.getElementById("mapStatusText");
        const locateUrl   = mapContainer.dataset.locateUrl;

        function resetMarkerColors() {
            branchData.forEach((b) => {
                if (b._el) {
                    const isMine = b.is_user_branch;
                    b._el.innerHTML = makePinElement(isMine ? PIN_MINE : PIN_OTHER, isMine).innerHTML;
                }
            });
        }

        function resetMapView() {
            if (searchInput) searchInput.value = "";
            if (resultCard) { resultCard.hidden = true; resultCard.innerHTML = ""; }
            resetMarkerColors();
            if (initialBounds) {
                map.fitBounds(initialBounds, { padding: 60, maxZoom: 14, duration: 800 });
            }
            if (statusText) statusText.textContent = `Showing all ${branchData.length} branch locations`;
        }

        if (resetBtn) resetBtn.addEventListener("click", resetMapView);

        async function performSearch(query) {
            query = (query || "").trim();
            if (!query) return;
            if (statusText) statusText.textContent = `Locating nearest branch with "${query}" in stock...`;

            try {
                const resp = await fetch(`${locateUrl}?q=${encodeURIComponent(query)}`, {
                    headers: { Accept: "application/json" },
                });
                if (!resp.ok) throw new Error("Search failed");
                const data = await resp.json();

                resetMarkerColors();

                if (!data.results || data.results.length === 0) {
                    if (statusText) statusText.textContent = `No branches currently have "${query}" in stock.`;
                    if (resultCard) {
                        resultCard.hidden = false;
                        resultCard.innerHTML = `
                            <div class="locator-empty-msg">
                                <strong>No stock found across branches for "${query}"</strong>
                                <p>Use "Notify branch" to send a stock inquiry to other branches.</p>
                            </div>`;
                    }
                    return;
                }

                const nearest = data.results[0];
                if (statusText) {
                    statusText.textContent = `Found at ${data.results.length} branch(es). Nearest: ${nearest.branch_name} (${nearest.distance_km} km away).`;
                }

                // Highlight nearest marker
                const targetBranch = branchData.find((b) => b.id === nearest.branch_id);
                if (targetBranch && targetBranch._el) {
                    targetBranch._el.innerHTML = makePinElement(PIN_NEAREST, false).innerHTML;
                    targetBranch._marker.togglePopup();
                }

                // Draw route line using MapLibre source/layer
                const routeCoords = [];
                if (data.user_branch) routeCoords.push([data.user_branch.lng, data.user_branch.lat]);
                routeCoords.push([nearest.lng, nearest.lat]);

                if (map.getLayer("route-line")) map.removeLayer("route-line");
                if (map.getSource("route")) map.removeSource("route");

                if (routeCoords.length > 1) {
                    map.addSource("route", {
                        type: "geojson",
                        data: { type: "Feature", geometry: { type: "LineString", coordinates: routeCoords } },
                    });
                    map.addLayer({
                        id: "route-line",
                        type: "line",
                        source: "route",
                        paint: { "line-color": "#339989", "line-width": 3, "line-dasharray": [4, 6], "line-opacity": 0.85 },
                    });
                }

                // Fly to cover nearest + user branch
                const flyBounds = routeCoords.reduce(
                    (b, c) => b.extend(c),
                    new maplibregl.LngLatBounds(routeCoords[0], routeCoords[0])
                );
                map.fitBounds(flyBounds, { padding: 80, maxZoom: 15, duration: 1000 });

                // Results card
                if (resultCard) {
                    resultCard.hidden = false;
                    resultCard.innerHTML = `
                        <div class="locator-found-box">
                            <div class="locator-found-head">
                                <div>
                                    <span class="badge badge--ok">In Stock</span>
                                    <h3>${nearest.medicine_name}</h3>
                                    <p class="muted">Nearest: <strong>${nearest.branch_name}</strong> &middot; <strong>${nearest.distance_km} km away</strong></p>
                                </div>
                                <div class="locator-stock-count">
                                    <strong>${nearest.quantity}</strong>
                                    <small>${nearest.unit}</small>
                                </div>
                            </div>
                            <div class="locator-found-details">
                                <p>📍 ${nearest.branch_address} &nbsp;|&nbsp; 📞 <a href="tel:${nearest.branch_phone}">${nearest.branch_phone}</a></p>
                                <div class="locator-action-row">
                                    <button type="button" class="btn btn-primary btn-sm btn-notify-match"
                                            data-branch-id="${nearest.branch_id}"
                                            data-branch-name="${nearest.branch_name}"
                                            data-med-id="${nearest.medicine_id}"
                                            data-med-name="${nearest.medicine_name}">
                                        <svg class="icon-sm" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                                        Send notification to ${nearest.branch_name}
                                    </button>
                                    ${data.results.length > 1 ? `<span class="muted"><small>Also in stock at ${data.results.length - 1} other branch(es).</small></span>` : ""}
                                </div>
                            </div>
                        </div>`;

                    const matchBtn = resultCard.querySelector(".btn-notify-match");
                    if (matchBtn) {
                        matchBtn.addEventListener("click", () => {
                            openNotifyDialog({
                                branchId: matchBtn.dataset.branchId,
                                medId: matchBtn.dataset.medId,
                                note: `Stock request for ${matchBtn.dataset.medName}.`,
                            });
                        });
                    }
                }
            } catch (err) {
                if (statusText) statusText.textContent = "Error locating stock across branches.";
            }
        }

        if (searchBtn && searchInput) {
            searchBtn.addEventListener("click", () => performSearch(searchInput.value));
            searchInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") { e.preventDefault(); performSearch(searchInput.value); }
            });
        }

        // Table "Show on map" buttons
        document.querySelectorAll("[data-focus-branch]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const lat = parseFloat(btn.dataset.lat);
                const lng = parseFloat(btn.dataset.lng);
                const branchName = btn.dataset.focusBranch;
                const medName = btn.dataset.med;
                const qty = btn.dataset.qty;
                const dist = btn.dataset.dist;

                mapContainer.scrollIntoView({ behavior: "smooth", block: "center" });

                if (lat && lng) {
                    map.flyTo({ center: [lng, lat], zoom: 14, duration: 1000 });
                    const bObj = branchData.find((b) => b.name === branchName);
                    if (bObj && bObj._marker) bObj._marker.togglePopup();
                    if (statusText) {
                        statusText.textContent = `Located "${medName}" at ${branchName}: ${qty} on hand (${dist} km away).`;
                    }
                }
            });
        });
    }

    // ── 5-Second Real-Time Live Sync Indicator ────────────────────────────────
    const livePill = document.getElementById("invLivePill");
    const liveText = document.getElementById("invLiveText");
    const SYNC_INTERVAL = 5000;
    let syncTimer = null;

    async function pollLiveInventory() {
        try {
            const resp = await fetch("/inventory/live-status/", {
                headers: { Accept: "application/json" },
            });
            if (!resp.ok) throw new Error("Sync failed");
            const data = await resp.json();

            if (livePill) livePill.classList.add("is-live");
            if (liveText) liveText.textContent = `Live Sync (${data.timestamp})`;
        } catch (e) {
            if (livePill) livePill.classList.remove("is-live");
            if (liveText) liveText.textContent = "Sync reconnecting...";
        }

        if (!document.hidden) {
            syncTimer = setTimeout(pollLiveInventory, SYNC_INTERVAL);
        }
    }

    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            clearTimeout(syncTimer);
            pollLiveInventory();
        }
    });

    syncTimer = setTimeout(pollLiveInventory, SYNC_INTERVAL);
});
