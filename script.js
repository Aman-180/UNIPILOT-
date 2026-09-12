const API_URL = "http://localhost:5000/api";
const GEMINI_API_KEY = "AIzaSyBA7csQr8zsnTFS3Ro5PLQ_TDS0LwmeVQQ";

document.addEventListener("DOMContentLoaded", () => {

    // ── ELEMENTS ──
    const loginSection = document.getElementById("loginSection");
    const mainApp = document.getElementById("mainApp");
    const loginBtn = document.getElementById("loginBtn");
    const nameInput = document.getElementById("nameInput");
    const welcomeText = document.getElementById("welcomeText");
    const streakText = document.getElementById("streakText");
    const taskInput = document.getElementById("taskInput");
    const addTaskBtn = document.getElementById("addTaskBtn");
    const tasksContainer = document.getElementById("tasksContainer");
    const progressBar = document.getElementById("progressBar");
    const progressPercent = document.getElementById("progressPercent");
    const completedCount = document.getElementById("completedCount");
    const totalCount = document.getElementById("totalCount");
    const syncBtn = document.getElementById("syncBtn");
    const resetBtn = document.getElementById("resetBtn");
    const themeToggle = document.getElementById("themeToggle");
    const chatInput = document.getElementById("chatInput");
    const sendChatBtn = document.getElementById("sendChatBtn");
    const chatMessages = document.getElementById("chatMessages");
    const profileAvatar = document.getElementById("profileAvatar");

    // ── NAV ──
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener("click", () => {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove("active"));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove("active"));
            item.classList.add("active");
            document.getElementById(item.getAttribute("data-tab")).classList.add("active");
            if (item.getAttribute("data-tab") === "statsTab") loadStats();
        });
    });

    // ── THEME ──
    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light");
        themeToggle.innerText = "☀️";
    }
    themeToggle.addEventListener("click", () => {
        document.body.classList.toggle("light");
        themeToggle.innerText = document.body.classList.contains("light") ? "☀️" : "🌙";
        localStorage.setItem("theme", document.body.classList.contains("light") ? "light" : "dark");
    });

    // ── LOGIN ──
    const savedName = localStorage.getItem("username");
    if (savedName) {
        showApp(savedName);
    }

    loginBtn.addEventListener("click", () => {
        const name = nameInput.value.trim();
        if (!name) { alert("Please enter your name"); return; }
        localStorage.setItem("username", name);
        showApp(name);
    });

    nameInput.addEventListener("keypress", e => {
        if (e.key === "Enter") loginBtn.click();
    });

    function showApp(name) {
        loginSection.style.display = "none";
        mainApp.style.display = "flex";
        welcomeText.innerText = `Welcome Back, ${name} 👋`;
        profileAvatar.innerText = name[0].toUpperCase();
        loadCustomTasks();
        loadStreakFromStorage();
        loadServerData();
    }

    // ── STREAK ──
    function loadStreakFromStorage() {
        const streak = localStorage.getItem("streak") || 0;
        streakText.innerText = `🔥 ${streak} Day Streak — Keep going!`;
        document.getElementById("analyticsStreak").innerText = streak + " Days";
    }

    // ── CUSTOM TASKS ──
    function loadCustomTasks() {
        const tasks = JSON.parse(localStorage.getItem("customTasks")) || [];
        tasksContainer.innerHTML = "";

        if (tasks.length === 0) {
            tasksContainer.innerHTML = '<p class="empty-msg">No tasks yet. Add one above! 🚀</p>';
            updateProgress([]);
            return;
        }

        tasks.forEach((task, index) => {
            const div = document.createElement("div");
            div.className = "task-item";

            const taskInfo = document.createElement("div");
            taskInfo.className = "task-info";

            const cb = document.createElement("input");
            cb.type = "checkbox";
            cb.checked = localStorage.getItem("task_" + index) === "true";

            const span = document.createElement("span");
            span.className = "task-name";
            span.textContent = task.name;

            const del = document.createElement("button");
            del.className = "task-delete";
            del.textContent = "✕";

            taskInfo.appendChild(cb);
            taskInfo.appendChild(span);
            div.appendChild(taskInfo);
            div.appendChild(del);
            tasksContainer.appendChild(div);

            cb.addEventListener("change", () => {
                localStorage.setItem("task_" + index, cb.checked);
                updateProgress(getAllCheckboxes());
            });

            del.addEventListener("click", () => {
                if (confirm("Delete this task?")) {
                    tasks.splice(index, 1);
                    localStorage.setItem("customTasks", JSON.stringify(tasks));
                    loadCustomTasks();
                }
            });
        });

        updateProgress(getAllCheckboxes());
    }

    function getAllCheckboxes() {
        return [...document.querySelectorAll('.task-info input[type="checkbox"]')];
    }

    addTaskBtn.addEventListener("click", addTask);
    taskInput.addEventListener("keypress", e => {
        if (e.key === "Enter") addTask();
    });

    function addTask() {
        const name = taskInput.value.trim();
        if (!name) return;
        const tasks = JSON.parse(localStorage.getItem("customTasks")) || [];
        tasks.push({ name });
        localStorage.setItem("customTasks", JSON.stringify(tasks));
        taskInput.value = "";
        loadCustomTasks();
    }

    // ── PROGRESS ──
    function updateProgress(checkboxes) {
        const total = checkboxes.length;
        const done = checkboxes.filter(cb => cb.checked).length;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;

        progressBar.style.width = pct + "%";
        progressPercent.innerText = pct + "%";
        completedCount.innerText = done;
        totalCount.innerText = `of ${total} done`;

        if (pct === 100 && total > 0) {
            const today = new Date().toLocaleDateString();
            const last = localStorage.getItem("lastCompletedDate");
            let streak = parseInt(localStorage.getItem("streak")) || 0;
            if (last !== today) {
                streak++;
                localStorage.setItem("streak", streak);
                localStorage.setItem("lastCompletedDate", today);
            }
            streakText.innerText = `🔥 ${streak} Day Streak — Amazing!`;
            document.getElementById("analyticsStreak").innerText = streak + " Days";
        }
    }

    // ── RESET ──
    resetBtn.addEventListener("click", () => {
        if (!confirm("Reset all tasks for today?")) return;
        const tasks = JSON.parse(localStorage.getItem("customTasks")) || [];
        tasks.forEach((_, i) => localStorage.removeItem("task_" + i));
        loadCustomTasks();
    });

    // ── SERVER DATA ──
    async function loadServerData() {
        try {
            const [logsRes, statsRes] = await Promise.all([
                fetch(API_URL + "/logs"),
                fetch(API_URL + "/progress-report")
            ]);
            if (logsRes.ok) {
                const logs = await logsRes.json();
                displayLogs(logs);
            }
            if (statsRes.ok) {
                const stats = await statsRes.json();
                if (stats.avg_score) {
                    document.getElementById("analyticsScore").innerText = Math.round(stats.avg_score);
                }
                document.getElementById("analyticsDays").innerText = stats.total_days || 0;
            }
        } catch (e) {
            console.log("Server offline - running locally");
        }
    }

    async function loadStats() {
        try {
            const [logsRes, statsRes] = await Promise.all([
                fetch(API_URL + "/logs"),
                fetch(API_URL + "/progress-report")
            ]);
            if (logsRes.ok) {
                const logs = await logsRes.json();
                displayLogs(logs);
            }
            if (statsRes.ok) {
                const stats = await statsRes.json();
                document.getElementById("stat-days").innerText = stats.total_days || 0;
                document.getElementById("stat-study").innerText = (stats.avg_study || 0).toFixed(1) + "h";
                document.getElementById("stat-score").innerText = Math.round(stats.avg_score || 0);
                document.getElementById("stat-streak").innerText = (stats.best_streak || 0) + "🔥";
            }
        } catch (e) {
            console.log("Stats offline");
        }
    }

    function displayLogs(logs) {
        const container = document.getElementById("logsContainer");
        container.innerHTML = "";
        if (!logs.length) {
            container.innerHTML = '<p class="empty-msg">No logs yet. Sync your data!</p>';
            return;
        }
        logs.slice(0, 7).forEach(log => {
            const div = document.createElement("div");
            div.className = "log-item";
            const score = log.score >= 80 ? "🟢" : log.score >= 60 ? "🟡" : "🔴";
            div.innerHTML = `<strong>${log.date}</strong><span class="log-score">${score} ${log.score}/100 | 🔥${log.streak}</span>`;
            container.appendChild(div);
        });
    }

    // ── SYNC ──
    syncBtn.addEventListener("click", async () => {
        const cbs = getAllCheckboxes();
        const total = cbs.length;
        const done = cbs.filter(cb => cb.checked).length;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;

        try {
            syncBtn.disabled = true;
            syncBtn.innerText = "Syncing...";
            const res = await fetch(API_URL + "/logs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    date: new Date().toISOString().split('T')[0],
                    study: done * 0.5,
                    workout: 0,
                    water: 0,
                    sleep: 8,
                    completion_pct: pct
                })
            });
            if (res.ok) {
                const result = await res.json();
                alert(`✅ Synced! Score: ${result.score}/100 | Streak: 🔥${result.streak}`);
                loadServerData();
            }
        } catch (e) {
            alert("Server offline. Tasks saved locally ✅");
        } finally {
            syncBtn.disabled = false;
            syncBtn.innerText = "Sync Data";
        }
    });

    // ── AI CHAT ──
    sendChatBtn.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", e => {
        if (e.key === "Enter") sendMessage();
    });

    async function sendMessage() {
        const msg = chatInput.value.trim();
        if (!msg) return;

        addBubble(msg, "user");
        chatInput.value = "";
        sendChatBtn.disabled = true;
        sendChatBtn.innerText = "...";

        const response = await callGemini(msg);
        addBubble(response, "bot");
        sendChatBtn.disabled = false;
        sendChatBtn.innerText = "Send";
    }

    function addBubble(text, type) {
        const div = document.createElement("div");
        div.className = `chat-bubble ${type}`;
        div.innerHTML = `<p>${text}</p>`;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function callGemini(message) {
        try {
            const tasks = JSON.parse(localStorage.getItem("customTasks")) || [];
            const name = localStorage.getItem("username") || "Student";
            const streak = localStorage.getItem("streak") || 0;

            const prompt = `You are an AI coach for a student named ${name}.
Their streak: ${streak} days.
Their daily tasks: ${tasks.map(t => t.name).join(", ") || "None yet"}.
Be encouraging, short (2-3 sentences), and use emojis.
User: "${message}"`;

            const res = await fetch(
                `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key=${GEMINI_API_KEY}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
                }
            );

            if (!res.ok) { const err = await res.json(); console.log("Gemini error:", err); return "❌ API Error: " + (err.error?.message || "Check console"); }
            const data = await res.json();
            return data.candidates[0].content.parts[0].text;
        } catch (e) {
            return "❌ Could not connect to AI. Check your API key in script.js!";
        }
    }
});