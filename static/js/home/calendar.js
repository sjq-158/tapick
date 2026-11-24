/**
 * Notion-style Calendar Component for Tapick Dashboard
 * Renders monthly calendar view, recent transactions, and activity metrics.
 * Strictly scopes transactions to branch for Pharmacists & Head Pharmacists.
 * Provides read-only oversight for Administrators (cannot edit).
 */

document.addEventListener("DOMContentLoaded", () => {
    const calendarCard = document.getElementById("notionCalendar");
    if (!calendarCard) return;

    // Endpoints and configuration
    const eventsUrl = calendarCard.dataset.eventsUrl;
    const detailUrlTemplate = calendarCard.dataset.detailUrlTemplate; // e.g. /calendar/transaction/0/
    const initialDataEl = document.getElementById("calendarInitialData");

    let initialData = {};
    if (initialDataEl) {
        try {
            initialData = JSON.parse(initialDataEl.textContent || "{}");
        } catch (e) {
            initialData = {};
        }
    }

    const today = new Date();
    let currentYear = initialData.year || today.getFullYear();
    let currentMonth = initialData.month || (today.getMonth() + 1); // 1-indexed
    let events = initialData.events || [];
    let isOverseer = initialData.overseer_mode || false;
    let selectedBranchId = initialData.selected_branch_id || "";

    // DOM Elements
    const monthTitle = document.getElementById("notionCurrentMonth");
    const prevMonthBtn = document.getElementById("notionPrevMonth");
    const nextMonthBtn = document.getElementById("notionNextMonth");
    const todayBtn = document.getElementById("notionTodayBtn");
    const daysGrid = document.getElementById("notionDaysGrid");
    const branchSelect = document.getElementById("notionBranchSelect");
    const tabBtns = document.querySelectorAll(".notion-tab-btn");
    const tabContents = document.querySelectorAll(".notion-tab-content");
    const tableBody = document.getElementById("notionTxTableBody");
    const modal = document.getElementById("notionTxModal");

    // Metrics elements
    const metricTotalSales = document.getElementById("metricTotalSales");
    const metricRevenue = document.getElementById("metricRevenue");
    const metricAvgTicket = document.getElementById("metricAvgTicket");

    const MONTH_NAMES = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    const SHORT_MONTHS = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    // Helper: format currency
    function formatPHP(amount) {
        return "₱" + Number(amount || 0).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // ── Render Monthly Calendar Grid ──────────────────────────────────────────
    function renderCalendar() {
        if (!daysGrid) return;
        daysGrid.innerHTML = "";

        if (monthTitle) {
            monthTitle.textContent = `${MONTH_NAMES[currentMonth - 1]} ${currentYear}`;
        }

        // Calculate calendar bounds
        const firstDayIndex = new Date(currentYear, currentMonth - 1, 1).getDay(); // 0 = Sun
        const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
        const daysInPrevMonth = new Date(currentYear, currentMonth - 1, 0).getDate();

        // Group events by day of current month
        const eventsByDay = {};
        events.forEach((ev) => {
            const evDate = new Date(ev.sold_at_iso);
            if (evDate.getFullYear() === currentYear && (evDate.getMonth() + 1) === currentMonth) {
                const dayNum = evDate.getDate();
                if (!eventsByDay[dayNum]) eventsByDay[dayNum] = [];
                eventsByDay[dayNum].push(ev);
            }
        });

        // 1. Preceding days from previous month
        for (let i = firstDayIndex - 1; i >= 0; i--) {
            const dayNum = daysInPrevMonth - i;
            const cell = document.createElement("div");
            cell.className = "notion-day-cell is-other-month";
            cell.innerHTML = `
                <div class="notion-day-cell-head">
                    <span class="notion-day-num">${dayNum}</span>
                </div>`;
            daysGrid.appendChild(cell);
        }

        // 2. Days of current month
        const isCurrentRealMonth = (today.getFullYear() === currentYear && (today.getMonth() + 1) === currentMonth);
        const realTodayDate = today.getDate();

        for (let d = 1; d <= daysInMonth; d++) {
            const cell = document.createElement("div");
            cell.className = "notion-day-cell";
            if (isCurrentRealMonth && d === realTodayDate) {
                cell.classList.add("is-today");
            }

            // Cell head: show "Month 1" on first day like Notion screenshot
            const dayLabel = (d === 1) ? `${SHORT_MONTHS[currentMonth - 1]} 1` : `${d}`;
            const headEl = document.createElement("div");
            headEl.className = "notion-day-cell-head";
            headEl.innerHTML = `<span class="notion-day-num">${dayLabel}</span>`;
            cell.appendChild(headEl);

            // Render Notion Event Cards
            const dayEvents = eventsByDay[d] || [];
            const displayLimit = 2;
            const visibleEvents = dayEvents.slice(0, displayLimit);
            const remainingCount = dayEvents.length - displayLimit;

            visibleEvents.forEach((ev) => {
                const card = document.createElement("div");
                card.className = "notion-event-card";
                card.title = `Sale #${ev.sale_id} (${ev.branch_name}) - Click to inspect receipt details`;

                const subtext = isOverseer
                    ? `${ev.branch_name} &middot; ${ev.items_count} item${ev.items_count > 1 ? "s" : ""}`
                    : `${ev.cashier_name} &middot; ${ev.items_count} item${ev.items_count > 1 ? "s" : ""}`;

                card.innerHTML = `
                    <div class="notion-event-title">
                        <span>🧾</span>
                        <span>Sale #${ev.sale_id} &middot; ${formatPHP(ev.total_amount)}</span>
                    </div>
                    <div class="notion-event-sub">${subtext}</div>`;

                card.addEventListener("click", () => openTransactionModal(ev.sale_id));
                cell.appendChild(card);
            });

            if (remainingCount > 0) {
                const moreChip = document.createElement("div");
                moreChip.className = "notion-more-chip";
                moreChip.textContent = `+ ${remainingCount} more`;
                moreChip.addEventListener("click", () => openDaySummaryModal(d, dayEvents));
                cell.appendChild(moreChip);
            }

            daysGrid.appendChild(cell);
        }

        // 3. Trailing days to fill the 7-column grid
        const totalCellsSoFar = firstDayIndex + daysInMonth;
        const remainingCells = (7 - (totalCellsSoFar % 7)) % 7;
        for (let d = 1; d <= remainingCells; d++) {
            const cell = document.createElement("div");
            cell.className = "notion-day-cell is-other-month";
            cell.innerHTML = `
                <div class="notion-day-cell-head">
                    <span class="notion-day-num">${d}</span>
                </div>`;
            daysGrid.appendChild(cell);
        }

        // Also update recent transactions table and metrics
        renderTable();
        renderMetrics();
    }

    // ── Render Recent Transactions Table (Tab 2) ──────────────────────────────
    function renderTable() {
        if (!tableBody) return;
        tableBody.innerHTML = "";

        if (events.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 24px; color: var(--muted);">
                        No sales transactions recorded for this period.
                    </td>
                </tr>`;
            return;
        }

        // Sort descending by date
        const sorted = [...events].sort((a, b) => new Date(b.sold_at_iso) - new Date(a.sold_at_iso));

        sorted.forEach((ev) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>#${ev.sale_id}</strong></td>
                <td>${ev.branch_name}</td>
                <td><small>${ev.cashier_email}</small></td>
                <td><strong>${formatPHP(ev.total_amount)}</strong></td>
                <td><small class="muted">${ev.formatted_date} ${ev.time_str}</small></td>
                <td>
                    <button type="button" class="btn btn-ghost btn-sm btn-inspect-tx" data-sale-id="${ev.sale_id}">
                        Inspect Receipt
                    </button>
                </td>`;

            tr.querySelector(".btn-inspect-tx")?.addEventListener("click", () => openTransactionModal(ev.sale_id));
            tableBody.appendChild(tr);
        });
    }

    // ── Render Metrics Overview (Tab 3) ───────────────────────────────────────
    function renderMetrics() {
        const count = events.length;
        const total = events.reduce((sum, ev) => sum + (ev.total_amount || 0), 0);
        const avg = count > 0 ? (total / count) : 0;

        if (metricTotalSales) metricTotalSales.textContent = count;
        if (metricRevenue) metricRevenue.textContent = formatPHP(total);
        if (metricAvgTicket) metricAvgTicket.textContent = formatPHP(avg);
    }

    // ── Fetch Events for Selected Month / Branch ──────────────────────────────
    async function fetchCalendarEvents() {
        if (!eventsUrl) return;

        let url = `${eventsUrl}?year=${currentYear}&month=${currentMonth}`;
        if (selectedBranchId) {
            url += `&branch=${selectedBranchId}`;
        }

        try {
            const resp = await fetch(url, { headers: { Accept: "application/json" } });
            if (!resp.ok) throw new Error("Failed to load events");
            const data = await resp.json();

            events = data.events || [];
            isOverseer = data.overseer_mode || false;
            renderCalendar();
        } catch (err) {
            console.error("Calendar fetch error:", err);
        }
    }

    // ── Open Notion Transaction Details Modal ─────────────────────────────────
    async function openTransactionModal(saleId) {
        if (!modal) return;

        // Find existing event or fetch detail
        let ev = events.find((e) => e.sale_id === saleId);
        let items = ev ? ev.items : null;

        // If items are not fully loaded, fetch from detail endpoint
        if (!items && detailUrlTemplate) {
            try {
                const url = detailUrlTemplate.replace("/0/", `/${saleId}/`);
                const resp = await fetch(url);
                if (resp.ok) {
                    ev = await resp.json();
                    items = ev.items;
                }
            } catch (err) {}
        }

        if (!ev) return;

        // Populate Notion modal fields
        document.getElementById("modalSaleId").textContent = `#${ev.sale_id}`;
        document.getElementById("modalDateTime").textContent = `${ev.formatted_date || ev.sold_at_date || ""} ${ev.time_str || ev.sold_at_time || ""}`;
        document.getElementById("modalBranch").textContent = ev.branch_name;
        document.getElementById("modalCashier").textContent = ev.cashier_email || ev.cashier_name;
        document.getElementById("modalTotalAmount").textContent = formatPHP(ev.total_amount);

        // Role & Overseer notice
        const noticeEl = document.getElementById("modalOverseerNotice");
        const badgeEl = document.getElementById("modalRoleBadge");

        if (isOverseer) {
            badgeEl.className = "badge badge--muted";
            badgeEl.textContent = "Admin Overseer Mode \u00b7 Read Only";
            noticeEl.textContent = "Admin Overseer Notice: You have full oversight to audit branch transactions. Records are permanent and cannot be modified.";
        } else {
            badgeEl.className = "badge badge--ok";
            badgeEl.textContent = `Branch Scope \u00b7 ${ev.branch_name}`;
            noticeEl.textContent = "Branch Dispensing Record: Transactions are verified and strictly bound to your branch.";
        }

        // Render dispensed items table
        const itemsBody = document.getElementById("modalItemsBody");
        if (itemsBody) {
            itemsBody.innerHTML = "";
            (items || []).forEach((item) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>
                        <strong>${item.medicine_name}</strong>
                        <small class="muted" style="display:block;">${item.generic_name || ""}</small>
                    </td>
                    <td><span class="chip">${item.category || "General"}</span></td>
                    <td class="num">${item.quantity} ${item.unit || "unit"}</td>
                    <td class="num">${formatPHP(item.unit_price)}</td>
                    <td class="num"><strong>${formatPHP(item.subtotal)}</strong></td>`;
                itemsBody.appendChild(tr);
            });
        }

        modal.showModal();
    }

    // ── Open Day Summary Modal (when +X more is clicked) ──────────────────────
    function openDaySummaryModal(dayNum, dayEvents) {
        if (!modal) return;
        // Open the first event of the day or display summary
        if (dayEvents && dayEvents.length > 0) {
            openTransactionModal(dayEvents[0].sale_id);
        }
    }

    // ── Navigation Event Listeners ────────────────────────────────────────────
    if (prevMonthBtn) {
        prevMonthBtn.addEventListener("click", () => {
            currentMonth--;
            if (currentMonth < 1) {
                currentMonth = 12;
                currentYear--;
            }
            fetchCalendarEvents();
        });
    }

    if (nextMonthBtn) {
        nextMonthBtn.addEventListener("click", () => {
            currentMonth++;
            if (currentMonth > 12) {
                currentMonth = 1;
                currentYear++;
            }
            fetchCalendarEvents();
        });
    }

    if (todayBtn) {
        todayBtn.addEventListener("click", () => {
            const now = new Date();
            currentYear = now.getFullYear();
            currentMonth = now.getMonth() + 1;
            fetchCalendarEvents();
        });
    }

    // Admin branch selector change
    if (branchSelect) {
        branchSelect.addEventListener("change", (e) => {
            selectedBranchId = e.target.value;
            fetchCalendarEvents();
        });
    }

    // Database tab switching (Notion tabs)
    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            tabBtns.forEach((b) => b.classList.remove("is-active"));
            tabContents.forEach((c) => c.classList.remove("is-active"));

            btn.classList.add("is-active");
            const targetId = btn.dataset.tab;
            const targetContent = document.getElementById(targetId);
            if (targetContent) targetContent.classList.add("is-active");
        });
    });

    // Close modal on click outside or close button
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal || e.target.closest("[data-close]")) {
                modal.close();
            }
        });
    }

    // Initial render
    renderCalendar();
});
