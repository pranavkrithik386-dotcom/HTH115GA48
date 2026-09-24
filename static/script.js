const form = document.getElementById("analyzeForm");
const results = document.getElementById("results");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    results.classList.add("hidden");
    errorBox.classList.add("hidden");
    loading.classList.remove("hidden");

    const data = new FormData(form);

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: data
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Analysis failed.");
        }

        document.getElementById("files").textContent =
            `${result.resume} → ${result.job}`;
        document.getElementById("score").textContent = `${result.score}%`;

        const table = document.getElementById("requirementTable");
        table.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Requirement</th>
                        <th>Status</th>
                        <th>Resume Evidence</th>
                    </tr>
                </thead>
                <tbody>
                    ${result.results.map(r => `
                        <tr>
                            <td>${escapeHtml(r.requirement)}</td>
                            <td class="status ${r.status.toLowerCase()}">${r.status}</td>
                            <td>${escapeHtml(r.evidence)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;

        document.getElementById("summary").textContent =
            result.explanation.summary || "";

        const gaps = document.getElementById("gaps");
        gaps.innerHTML = "";
        (result.explanation.gaps || []).forEach(g => {
            const li = document.createElement("li");
            li.textContent = g;
            gaps.appendChild(li);
        });

        const questions = document.getElementById("questions");
        questions.innerHTML = "";
        (result.explanation.questions || []).forEach(q => {
            const li = document.createElement("li");
            li.textContent = q;
            questions.appendChild(li);
        });

        document.getElementById("biasNote").textContent = result.bias_note;

        results.classList.remove("hidden");
    } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove("hidden");
    } finally {
        loading.classList.add("hidden");
    }
});

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
