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

    // ── Interactive Leaflet Map & Cross-Branch Stock Locator ──────────────────
    const mapContainer = document.getElementById("locatorMap");
    let map = null;
    let markersLayer = null;
    let routeLine = null;
    let branchData = [];
    let initialBounds = [];

    if (mapContainer && typeof L !== "undefined") {
        try {
            branchData = JSON.parse(mapContainer.dataset.branches || "[]");
        } catch (e) {
            branchData = [];
        }

        // Initialize Map with responsive zooming
        const defaultCenter = [10.3157, 123.8854]; // Metro Cebu
        map = L.map("locatorMap", {
            center: defaultCenter,
            zoom: 12,
            minZoom: 9,
            maxZoom: 18,
            zoomControl: true,
            scrollWheelZoom: true,
            wheelDebounceTime: 40,
            wheelPxPerZoomLevel: 60,
            zoomAnimation: true,
            fadeAnimation: true,
            markerZoomAnimation: true,
        });

        // OpenStreetMap Tile Layer
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        }).addTo(map);

        markersLayer = L.layerGroup().addTo(map);

        // SVG Pin Icon Generator
        const createPinIcon = (colorHex, isMine) => {
            const svgPin = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="30" height="40" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.25));">
                    <path fill="${colorHex}" stroke="#ffffff" stroke-width="1.6" d="M12 0C5.37 0 0 5.37 0 12c0 8.5 12 20 12 20s12-11.5 12-20c0-6.63-5.37-12-12-12z"/>
                    <circle cx="12" cy="11" r="5" fill="#ffffff"/>
                    ${isMine ? '<circle cx="12" cy="11" r="2.5" fill="' + colorHex + '"/>' : ''}
                </svg>
            `;
            return L.divIcon({
                className: "custom-map-pin",
                html: svgPin,
                iconSize: [30, 40],
                iconAnchor: [15, 40],
                popupAnchor: [0, -36],
            });
        };

        const myPinIcon = createPinIcon("#339989", true);     // Tapick Teal (Your Branch)
        const otherPinIcon = createPinIcon("#2B2C28", false); // Charcoal (Other Branches)
        const nearestPinIcon = createPinIcon("#E07A5F", false); // Coral (Nearest In-Stock)

        // Plot All Branches
        branchData.forEach((b) => {
            const isMine = b.is_user_branch;
            const icon = isMine ? myPinIcon : otherPinIcon;
            const marker = L.marker([b.lat, b.lng], { icon: icon }).addTo(markersLayer);

            const popupContent = `
                <div class="map-popup-card">
                    <strong class="map-popup-title">${b.name}</strong>
                    ${isMine ? '<span class="map-popup-badge">Your Branch</span>' : '<span class="map-popup-dist">' + b.distance_km + ' km away</span>'}
                    <p class="map-popup-addr">${b.address}</p>
                    <p class="map-popup-phone">📞 <a href="tel:${b.phone}">${b.phone || "No phone listed"}</a></p>
                    ${!isMine ? `
                    <div style="margin-top: 8px;">
                        <button type="button" class="btn btn-primary btn-sm btn-popup-notify" data-branch-id="${b.id}" data-branch-name="${b.name}">
                            Notify this branch
                        </button>
                    </div>` : ''}
                </div>
            `;
            marker.bindPopup(popupContent);
            b._marker = marker;
            initialBounds.push([b.lat, b.lng]);
        });

        // Fit map initially to cover all branches
        if (initialBounds.length > 0) {
            map.fitBounds(initialBounds, { padding: [40, 40], maxZoom: 14 });
        }

        // Delegate popup "Notify this branch" clicks
        map.on("popupopen", (e) => {
            const popupEl = e.popup.getElement();
            if (!popupEl) return;
            const btn = popupEl.querySelector(".btn-popup-notify");
            if (btn) {
                btn.addEventListener("click", () => {
                    openNotifyDialog({
                        branchId: btn.dataset.branchId,
                    });
                });
            }
        });

        // Locator Search Elements
        const searchInput = document.getElementById("mapSearchInput");
        const searchBtn = document.getElementById("mapSearchBtn");
        const resetBtn = document.getElementById("mapResetBtn");
        const resultCard = document.getElementById("locatorResultCard");
        const statusText = document.getElementById("mapStatusText");
        const locateUrl = mapContainer.dataset.locateUrl;

        // Reset View Handler
        function resetMapView() {
            if (searchInput) searchInput.value = "";
            if (routeLine) {
                map.removeLayer(routeLine);
                routeLine = null;
            }
            if (resultCard) {
                resultCard.hidden = true;
                resultCard.innerHTML = "";
            }
            // Reset marker icons back to default
            branchData.forEach((b) => {
                if (b._marker) {
                    b._marker.setIcon(b.is_user_branch ? myPinIcon : otherPinIcon);
                }
            });
            if (initialBounds.length > 0) {
                map.flyToBounds(initialBounds, { padding: [40, 40], maxZoom: 14, duration: 0.8 });
            }
            if (statusText) {
                statusText.textContent = `Showing all ${branchData.length} branch locations`;
            }
        }

        if (resetBtn) {
            resetBtn.addEventListener("click", resetMapView);
        }

        // Search and locate nearest branch
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

                // Clear previous route line
                if (routeLine) {
                    map.removeLayer(routeLine);
                    routeLine = null;
                }

                // Reset markers
                branchData.forEach((b) => {
                    if (b._marker) {
                        b._marker.setIcon(b.is_user_branch ? myPinIcon : otherPinIcon);
                    }
                });

                if (!data.results || data.results.length === 0) {
                    if (statusText) statusText.textContent = `No branches currently have "${query}" in stock.`;
                    resultCard.hidden = false;
                    resultCard.innerHTML = `
                        <div class="locator-empty-msg">
                            <strong>No stock found across branches for "${query}"</strong>
                            <p>You can use "Notify branch" above to send a stock inquiry to other branches or head pharmacists.</p>
                        </div>
                    `;
                    return;
                }

                const nearest = data.results[0]; // Nearest branch with stock
                if (statusText) {
                    statusText.textContent = `Found at ${data.results.length} branch(es). Nearest: ${nearest.branch_name} (${nearest.distance_km} km away).`;
                }

                // Draw connector line if user branch is known and different
                const highlightBounds = [[nearest.lat, nearest.lng]];
                if (data.user_branch && (data.user_branch.lat !== nearest.lat || data.user_branch.lng !== nearest.lng)) {
                    routeLine = L.polyline(
                        [[data.user_branch.lat, data.user_branch.lng], [nearest.lat, nearest.lng]],
                        { color: "#339989", weight: 3.5, dashArray: "6, 8", opacity: 0.85 }
                    ).addTo(map);
                    highlightBounds.push([data.user_branch.lat, data.user_branch.lng]);
                }

                // Smoothly frame both user branch and nearest branch
                if (highlightBounds.length > 1) {
                    map.flyToBounds(highlightBounds, { padding: [60, 60], maxZoom: 15, duration: 1 });
                } else {
                    map.flyTo([nearest.lat, nearest.lng], 14, { duration: 1 });
                }

                // Highlight nearest branch marker
                const targetBranchObj = branchData.find((b) => b.id === nearest.branch_id);
                if (targetBranchObj && targetBranchObj._marker) {
                    targetBranchObj._marker.setIcon(nearestPinIcon);
                    targetBranchObj._marker.openPopup();
                }

                // Render Results Card with action to notify
                resultCard.hidden = false;
                resultCard.innerHTML = `
                    <div class="locator-found-box">
                        <div class="locator-found-head">
                            <div>
                                <span class="badge badge--ok">In Stock</span>
                                <h3>${nearest.medicine_name}</h3>
                                <p class="muted">Nearest location: <strong>${nearest.branch_name}</strong> &middot; <strong>${nearest.distance_km} km away</strong></p>
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
                                ${data.results.length > 1 ? '<span class="muted"><small>Also in stock at ' + (data.results.length - 1) + ' other branch(es).</small></span>' : ''}
                            </div>
                        </div>
                    </div>
                `;

                // Connect the action button in the results card
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
            } catch (err) {
                if (statusText) statusText.textContent = "Error locating stock across branches.";
            }
        }

        if (searchBtn && searchInput) {
            searchBtn.addEventListener("click", () => performSearch(searchInput.value));
            searchInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    performSearch(searchInput.value);
                }
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
                    map.flyTo([lat, lng], 14, { duration: 1 });
                    const bObj = branchData.find((b) => b.name === branchName);
                    if (bObj && bObj._marker) {
                        bObj._marker.openPopup();
                    }
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
