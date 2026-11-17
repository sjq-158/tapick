(function () {
    document.querySelectorAll("[data-autosubmit]").forEach(function (field) {
        field.addEventListener("change", function () { field.form.submit(); });
    });

    var bell = document.getElementById("notifBell");
    if (!bell) return;

    var badge = document.getElementById("notifBadge");
    var toasts = document.getElementById("liveToasts");
    var list = document.getElementById("notificationList");
    var livePill = document.getElementById("livePill");
    var liveText = document.getElementById("liveText");
    var unreadChip = document.getElementById("unreadCount");
    var baseTitle = document.title;
    var INTERVAL = 4000;
    var lastId = null;
    var timer = null;

    var ICONS = {
        out_of_stock: '<svg class="icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
        low_stock: '<svg class="icon" viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
        restocked: '<svg class="icon" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
        stock_request: '<svg class="icon" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>'
    };
    var TRASH = '<svg class="icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6M14 11v6"></path></svg>';

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function iconFor(type) {
        return ICONS[type] || ICONS.stock_request;
    }

    function setLive(on) {
        if (!livePill) return;
        livePill.classList.toggle("is-live", on);
        liveText.textContent = on ? "Live" : "Reconnecting";
    }

    function setUnread(count) {
        badge.textContent = count > 99 ? "99+" : String(count);
        badge.hidden = count === 0;
        document.title = count ? "(" + count + ") " + baseTitle : baseTitle;
        if (unreadChip) unreadChip.textContent = count;
    }

    function showToast(item) {
        if (!toasts) return;
        var toast = el("a", "live-toast live-toast--" + item.type);
        toast.href = bell.getAttribute("href");
        var icon = el("span", "live-toast-icon");
        icon.innerHTML = iconFor(item.type);
        var body = el("div", "live-toast-body");
        body.append(el("strong", "", item.title), el("p", "", item.message));
        toast.append(icon, body);
        toasts.prepend(toast);
        setTimeout(function () {
            toast.classList.add("is-leaving");
            setTimeout(function () { toast.remove(); }, 400);
        }, 8000);
    }

    function postForm(action, className, label, html) {
        var form = el("form");
        form.method = "post";
        form.action = action;
        var token = el("input");
        token.type = "hidden";
        token.name = "csrfmiddlewaretoken";
        token.value = list.dataset.csrf;
        var next = el("input");
        next.type = "hidden";
        next.name = "next";
        next.value = window.location.pathname + window.location.search;
        var button = el("button", className);
        button.type = "submit";
        if (html) { button.innerHTML = html; button.title = label; button.setAttribute("aria-label", label); }
        else { button.textContent = label; }
        form.append(token, next, button);
        return form;
    }

    function addToList(item) {
        if (!list || list.dataset.page !== "1") return;
        if (list.dataset.type && list.dataset.type !== item.type) return;
        var empty = document.getElementById("notificationEmpty");
        if (empty) empty.remove();

        var li = el("li", "notice notice--" + item.type + " is-unread is-new");
        li.dataset.id = item.id;
        var icon = el("span", "notice-icon");
        icon.innerHTML = iconFor(item.type);
        var body = el("div", "notice-body");
        body.append(
            el("strong", "", item.title),
            el("p", "", item.message),
            el("small", "", item.medicine + " \u00b7 " + item.branch + " \u00b7 just now")
        );
        var actions = el("div", "notice-actions");
        actions.append(
            postForm(list.dataset.readUrl.replace("/0/", "/" + item.id + "/"), "btn btn-ghost btn-sm", "Mark read"),
            postForm(list.dataset.deleteUrl.replace("/0/", "/" + item.id + "/"), "icon-btn icon-btn--danger", "Delete notification", TRASH)
        );
        li.append(icon, body, actions);
        list.prepend(li);
    }

    function ring() {
        bell.classList.remove("has-new");
        void bell.offsetWidth;
        bell.classList.add("has-new");
    }

    function schedule() {
        clearTimeout(timer);
        if (!document.hidden) timer = setTimeout(poll, INTERVAL);
    }

    async function poll() {
        try {
            var url = bell.dataset.pollUrl + (lastId === null ? "" : "?after=" + lastId);
            var response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
            if (!response.ok) throw new Error("poll failed");
            var data = await response.json();
            setLive(true);

            if (lastId === null) {
                lastId = data.latest_id;
            } else if (data.items.length) {
                data.items.forEach(function (item) { showToast(item); addToList(item); });
                lastId = data.items[data.items.length - 1].id;
                ring();
            }
            setUnread(data.unread);
        } catch (err) {
            setLive(false);
        }
        schedule();
    }

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) { clearTimeout(timer); poll(); }
    });
    poll();
})();