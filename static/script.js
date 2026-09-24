// ============================================================
// GA-04 RESUME-JD FIT ANALYZER
// FRONTEND ENGINE
// ============================================================

const form = document.getElementById("analyzeForm");
const results = document.getElementById("results");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");


// ============================================================
// FORM SUBMIT
// ============================================================

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
            throw new Error(
                result.error || "Analysis failed."
            );
        }


        // ====================================================
        // FILE NAMES + CURRENT SCORE
        // ====================================================

        document.getElementById("files").textContent =
            `${result.resume} → ${result.job}`;

        document.getElementById("score").textContent =
            `${result.score}%`;


        // ====================================================
        // REQUIREMENT-LEVEL EVIDENCE
        // ====================================================

        const table =
            document.getElementById("requirementTable");


        // Remove duplicate requirements
        const uniqueResults = [];

        const seen = new Set();

        (result.results || []).forEach(r => {

            const key =
                `${r.requirement}|${r.category || ""}`;

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
                            r.evidence_type ||
                            "NONE";

                        const status =
                            String(
                                r.status || "MISSING"
                            ).toLowerCase();


                        return `

                            <tr>

                                <td>
                                    ${escapeHtml(
                                        r.requirement
                                    )}
                                </td>


                                <td>
                                    ${escapeHtml(
                                        r.category ||
                                        "General"
                                    )}
                                </td>


                                <td
                                    class="status ${status}"
                                >
                                    ${escapeHtml(
                                        r.status ||
                                        "MISSING"
                                    )}
                                </td>


                                <td>
                                    ${escapeHtml(
                                        resumeEvidence
                                    )}
                                </td>


                                <td>
                                    ${escapeHtml(page)}
                                </td>


                                <td>
                                    <strong>
                                        ${escapeHtml(
                                            evidenceType
                                        )}
                                    </strong>
                                </td>


                                <td>
                                    ${escapeHtml(
                                        jdEvidence
                                    )}
                                </td>

                            </tr>

                        `;

                    }).join("")}

                </tbody>

            </table>

        `;


        // ====================================================
        // AI SUMMARY
        // ====================================================

        document.getElementById("summary").textContent =
            result.explanation?.summary || "";


        // ====================================================
        // SKILL GAPS
        // ====================================================

        const gaps =
            document.getElementById("gaps");

        gaps.innerHTML = "";


        (result.explanation?.gaps || [])
            .forEach(g => {

                const li =
                    document.createElement("li");

                li.textContent = g;

                gaps.appendChild(li);

            });


        // ====================================================
        // INTERVIEW QUESTIONS
        // ====================================================

        const questions =
            document.getElementById("questions");

        questions.innerHTML = "";


        (result.explanation?.questions || [])
            .forEach(q => {

                const li =
                    document.createElement("li");

                li.textContent = q;

                questions.appendChild(li);

            });


        // ====================================================
        // BIAS SAFEGUARD
        // ====================================================

        document.getElementById("biasNote").textContent =
            result.bias_note || "";


        // ====================================================
        // SKILL DEVELOPMENT + PROJECTED FIT
        // ====================================================

        renderDevelopmentPlan(
            result.development_plan
        );


        // ====================================================
        // SHOW RESULTS
        // ====================================================

        results.classList.remove("hidden");


        // Smoothly move user toward the result
        setTimeout(() => {

            results.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }, 150);


    } catch (err) {

        errorBox.textContent =
            err.message;

        errorBox.classList.remove(
            "hidden"
        );

    } finally {

        loading.classList.add(
            "hidden"
        );

    }

});


// ============================================================
// DEVELOPMENT PLAN RENDERER
// ============================================================

function renderDevelopmentPlan(plan) {

    // --------------------------------------------------------
    // Find existing container
    // --------------------------------------------------------

    let container =
        document.getElementById(
            "developmentPlan"
        );


    // --------------------------------------------------------
    // If HTML does not contain the container,
    // create it automatically.
    // --------------------------------------------------------

    if (!container) {

        container =
            document.createElement("section");

        container.id =
            "developmentPlan";

        container.className =
            "development-plan-wrapper";


        // Put it before the AI explanation
        const summarySection =
            document.querySelector(
                "#summary"
            );

        if (
            summarySection &&
            summarySection.parentElement
        ) {

            summarySection.parentElement
                .before(container);

        } else {

            results.appendChild(
                container
            );

        }

    }


    // --------------------------------------------------------
    // Empty / unavailable plan
    // --------------------------------------------------------

    if (!plan) {

        container.innerHTML = "";

        return;

    }


    const developmentItems =
        plan.development_items || [];

    const remainingGaps =
        plan.remaining_gaps || [];


    const currentScore =
        Number(
            plan.current_score || 0
        );


    const projectedScore =
        Number(
            plan.projected_score || 0
        );


    const improvement =
        Number(
            plan.improvement || 0
        );


    // --------------------------------------------------------
    // Development skill cards
    // --------------------------------------------------------

    let skillsHTML = "";


    if (developmentItems.length > 0) {

        skillsHTML =
            developmentItems.map(
                (item, index) => {

                    const icon =
                        getSkillIcon(
                            item.requirement
                        );


                    return `

                        <div
                            class="development-skill"
                        >

                            <div
                                class="skill-orbit"
                                style="
                                    --skill-progress:
                                    ${Math.min(
                                        100,
                                        35 + index * 8
                                    )}%;
                                "
                            >

                                <span>
                                    ${icon}
                                </span>

                            </div>


                            <div
                                class="
                                    development-skill-content
                                "
                            >

                                <div
                                    class="
                                        development-skill-top
                                    "
                                >

                                    <h3>
                                        ${escapeHtml(
                                            item.title ||
                                            item.requirement
                                        )}
                                    </h3>

                                    <span
                                        class="
                                            development-status
                                        "
                                    >
                                        ${escapeHtml(
                                            item.current_status ||
                                            "MISSING"
                                        )}
                                    </span>

                                </div>


                                <div
                                    class="
                                        development-meta
                                    "
                                >
                                    ${escapeHtml(
                                        item.category ||
                                        "Skill"
                                    )}
                                </div>


                                <p>
                                    <strong>
                                        Develop:
                                    </strong>

                                    ${escapeHtml(
                                        item.develop ||
                                        "Develop this requirement."
                                    )}
                                </p>


                                <p
                                    class="
                                        development-reason
                                    "
                                >
                                    ${escapeHtml(
                                        item.reason ||
                                        "This requirement is not fully evidenced."
                                    )}
                                </p>


                                <div
                                    class="
                                        projected-status
                                    "
                                >

                                    <span>
                                        Current:
                                        <b>
                                            ${escapeHtml(
                                                item.current_status ||
                                                "MISSING"
                                            )}
                                        </b>
                                    </span>

                                    <span>
                                        After development:
                                        <b>
                                            MATCH
                                        </b>
                                    </span>

                                </div>

                            </div>

                        </div>

                    `;

                }
            ).join("");

    } else {

        skillsHTML = `

            <div
                class="
                    development-empty
                "
            >

                <div class="empty-icon">
                    ✓
                </div>

                <h3>
                    No additional learnable gaps detected
                </h3>

                <p>
                    The current analysis did not identify
                    a missing skill with available
                    development guidance.
                </p>

            </div>

        `;

    }


    // --------------------------------------------------------
    // Remaining gaps
    // --------------------------------------------------------

    let remainingHTML = "";


    if (remainingGaps.length > 0) {

        remainingHTML = `

            <div
                class="
                    remaining-gap
                "
            >

                <div
                    class="
                        remaining-gap-header
                    "
                >

                    <span
                        class="
                            remaining-icon
                        "
                    >
                        ⚠
                    </span>

                    <div>

                        <h3>
                            Requirements Beyond Skill Development
                        </h3>

                        <p>
                            These requirements cannot
                            honestly be treated as
                            completed just by learning
                            a technical skill.
                        </p>

                    </div>

                </div>


                <div
                    class="
                        remaining-gap-list
                    "
                >

                    ${remainingGaps.map(
                        gap => `

                            <div
                                class="
                                    remaining-gap-item
                                "
                            >

                                <strong>
                                    ${escapeHtml(
                                        formatRequirement(
                                            gap.requirement
                                        )
                                    )}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        gap.category ||
                                        "Requirement"
                                    )}
                                </span>

                                <p>
                                    ${escapeHtml(
                                        gap.reason ||
                                        "Additional evidence is required."
                                    )}
                                </p>

                            </div>

                        `
                    ).join("")}

                </div>

            </div>

        `;

    }


    // --------------------------------------------------------
    // Complete development section
    // --------------------------------------------------------

    container.innerHTML = `

        <div
            class="
                development-plan-card
            "
        >

            <div
                class="
                    development-header
                "
            >

                <div>

                    <span
                        class="
                            tech-label
                        "
                    >
                        CAREER DEVELOPMENT ENGINE
                    </span>

                    <h2>
                        Skills You Should Develop
                    </h2>

                    <p
                        class="
                            development-subtitle
                        "
                    >
                        Based on the requirements that
                        are currently missing or only
                        partially evidenced in your resume.
                    </p>

                </div>


                <div
                    class="
                        development-count
                    "
                >

                    <span>
                        ${developmentItems.length}
                    </span>

                    <small>
                        DEVELOPMENT
                        ${developmentItems.length === 1
                            ? "AREA"
                            : "AREAS"}
                    </small>

                </div>

            </div>


            <div
                class="
                    projection-box
                "
            >

                <div
                    class="
                        projection-score
                    "
                >

                    <span
                        class="
                            projection-label
                        "
                    >
                        PROJECTED FIT
                    </span>

                    <strong>
                        ${formatScore(
                            projectedScore
                        )}%
                    </strong>

                    <span
                        class="
                            projection-improvement
                        "
                    >
                        +${formatScore(
                            improvement
                        )} points
                    </span>

                </div>


                <div
                    class="
                        projection-current
                    "
                >

                    <span>
                        CURRENT FIT
                    </span>

                    <strong>
                        ${formatScore(
                            currentScore
                        )}%
                    </strong>

                </div>


                <div
                    class="
                        projection-explanation
                    "
                >

                    <div
                        class="
                            projection-line
                        "
                    >
                        <span>
                            Current
                        </span>

                        <div
                            class="
                                progress-track
                            "
                        >

                            <div
                                class="
                                    progress-fill
                                "
                                style="
                                    width:
                                    ${clamp(
                                        currentScore
                                    )}%;
                                "
                            ></div>

                        </div>

                        <strong>
                            ${formatScore(
                                currentScore
                            )}%
                        </strong>

                    </div>


                    <div
                        class="
                            projection-line
                        "
                    >

                        <span>
                            Projected
                        </span>

                        <div
                            class="
                                progress-track
                            "
                        >

                            <div
                                class="
                                    progress-fill projected
                                "
                                style="
                                    width:
                                    ${clamp(
                                        projectedScore
                                    )}%;
                                "
                            ></div>

                        </div>

                        <strong>
                            ${formatScore(
                                projectedScore
                            )}%
                        </strong>

                    </div>

                </div>

            </div>


            <div
                class="
                    development-grid
                "
            >

                ${skillsHTML}

            </div>


            ${remainingHTML}


            <div
                class="
                    projection-note
                "
            >

                <span>
                    ⓘ
                </span>

                <p>
                    ${
                        escapeHtml(
                            plan.projection_note ||
                            "Projected Fit is a scenario-based calculation, not a guarantee of employment or selection."
                        )
                    }
                </p>

            </div>

        </div>

    `;

}


// ============================================================
// SKILL ICONS
// ============================================================

function getSkillIcon(requirement) {

    const icons = {

        "sql": "▣",

        "pyspark": "✦",

        "aws": "☁",

        "airflow": "↯",

        "etl": "⇄",

        "aws s3": "◈",

        "certification": "◆"

    };


    return (
        icons[
            String(
                requirement || ""
            ).toLowerCase()
        ]
        || "◇"
    );

}


// ============================================================
// FORMAT REQUIREMENT
// ============================================================

function formatRequirement(value) {

    if (!value) {
        return "Requirement";
    }


    const replacements = {

        "aws s3": "AWS S3",

        "pyspark": "PySpark",

        "airflow": "Apache Airflow",

        "etl": "ETL / Data Pipelines",

        "bachelor's degree": "Bachelor's Degree",

        "sql": "SQL",

        "aws": "AWS",

        "git": "Git"

    };


    const lower =
        String(value)
            .toLowerCase();


    if (
        replacements[lower]
    ) {

        return replacements[lower];

    }


    return String(value)
        .replace(/\b\w/g, char =>
            char.toUpperCase()
        );

}


// ============================================================
// SCORE FORMAT
// ============================================================

function formatScore(value) {

    const number =
        Number(value);


    if (
        Number.isNaN(number)
    ) {

        return "0";

    }


    if (
        Number.isInteger(number)
    ) {

        return String(number);

    }


    return number.toFixed(1);

}


// ============================================================
// LIMIT VALUE TO 0–100
// ============================================================

function clamp(value) {

    const number =
        Number(value);


    if (
        Number.isNaN(number)
    ) {

        return 0;

    }


    return Math.max(
        0,
        Math.min(
            100,
            number
        )
    );

}


// ============================================================
// HTML SAFETY
// ============================================================

function escapeHtml(value) {

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );

}