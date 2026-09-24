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

        // -----------------------------
        // FILE NAMES + SCORE
        // -----------------------------
        document.getElementById("files").textContent =
            `${result.resume} → ${result.job}`;

        document.getElementById("score").textContent =
            `${result.score}%`;

        // -----------------------------
        // REQUIREMENT-LEVEL EVIDENCE
        // -----------------------------
        const table = document.getElementById("requirementTable");

        // Remove duplicate requirements
        const uniqueResults = [];
        const seen = new Set();

        (result.results || []).forEach(r => {
            const key = `${r.requirement}|${r.category || ""}`;

            if (!seen.has(key)) {
                seen.add(key);
                uniqueResults.push(r);
            }
        });

        table.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Requirement</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Resume Evidence</th>
                        <th>Page</th>
                        <th>Evidence Type</th>
                        <th>JD Evidence</th>
                    </tr>
                </thead>

                <tbody>
                    ${uniqueResults.map(r => {

                        const resumeEvidence =
                            r.resume_evidence ||
                            "No evidence found in resume.";

                        const jdEvidence =
                            r.jd_evidence ||
                            "No JD evidence available.";

                        const page =
                            r.resume_page
                                ? `Page ${r.resume_page}`
                                : "—";

                        const evidenceType =
                            r.evidence_type || "NONE";

                        return `
                            <tr>
                                <td>
                                    ${escapeHtml(r.requirement)}
                                </td>

                                <td>
                                    ${escapeHtml(
                                        r.category || "General"
                                    )}
                                </td>

                                <td class="status ${String(r.status).toLowerCase()}">
                                    ${escapeHtml(r.status)}
                                </td>

                                <td>
                                    ${escapeHtml(resumeEvidence)}
                                </td>

                                <td>
                                    ${escapeHtml(page)}
                                </td>

                                <td>
                                    <strong>
                                        ${escapeHtml(evidenceType)}
                                    </strong>
                                </td>

                                <td>
                                    ${escapeHtml(jdEvidence)}
                                </td>
                            </tr>
                        `;

                    }).join("")}
                </tbody>
            </table>
        `;

        // -----------------------------
        // AI SUMMARY
        // -----------------------------
        document.getElementById("summary").textContent =
            result.explanation?.summary || "";

        // -----------------------------
        // SKILL GAPS
        // -----------------------------
        const gaps = document.getElementById("gaps");
        gaps.innerHTML = "";

        (result.explanation?.gaps || []).forEach(g => {
            const li = document.createElement("li");
            li.textContent = g;
            gaps.appendChild(li);
        });

        // -----------------------------
        // INTERVIEW QUESTIONS
        // -----------------------------
        const questions = document.getElementById("questions");
        questions.innerHTML = "";

        (result.explanation?.questions || []).forEach(q => {
            const li = document.createElement("li");
            li.textContent = q;
            questions.appendChild(li);
        });

        // -----------------------------
        // BIAS SAFEGUARD
        // -----------------------------
        document.getElementById("biasNote").textContent =
            result.bias_note || "";

        // -----------------------------
        // SHOW RESULTS
        // -----------------------------
        results.classList.remove("hidden");

    } catch (err) {

        errorBox.textContent = err.message;
        errorBox.classList.remove("hidden");

    } finally {

        loading.classList.add("hidden");
    }
});


// -----------------------------------
// HTML SAFETY
// -----------------------------------
function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}