// ============================================================
// GA-04 RESUME-JD FIT ANALYZER
// FRONTEND ENGINE + CAREER AI ASSISTANT
// ============================================================


const form = document.getElementById("analyzeForm");
const results = document.getElementById("results");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const careerPathway = document.getElementById("careerPathway");
const careerLocation = document.getElementById("careerLocation");
const customCareerLocation = document.getElementById("customCareerLocation");


// ============================================================
// CAREER AI STATE
// ============================================================

let currentCareerContext = null;
let careerChatHistory = [];


// ============================================================
// FORM SUBMIT
// ============================================================

form.addEventListener("submit", async (e) => {

    e.preventDefault();

    results.classList.add("hidden");
    careerPathway.classList.add("hidden");
    currentCareerContext = null;
    careerChatHistory = [];
    errorBox.classList.add("hidden");
    loading.classList.remove("hidden");

    const resumeFile = document.getElementById("resume").files[0];
    const jobFile = document.getElementById("job").files[0];

    if (
        !resumeFile
        ||
        !jobFile
        ||
        !resumeFile.name.toLowerCase().endsWith(".pdf")
        ||
        !jobFile.name.toLowerCase().endsWith(".pdf")
    ) {

        errorBox.textContent =
            "INVALID FILE TYPE — Please upload a supported document.";

        errorBox.classList.remove("hidden");
        loading.classList.add("hidden");

        return;
    }

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
                                    class="status ${escapeHtml(status)}"
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
        // BUILD CAREER AI CONTEXT
        // ====================================================

        currentCareerContext =
            buildCareerContext(result);

        await loadCareerPathway(result.results || []);


        // Reset previous conversation
        careerChatHistory = [];

        resetCareerChat();


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
// CAREER PATHWAY
// ============================================================

function selectedCareerLocation() {

    if (
        careerLocation &&
        careerLocation.value === "custom"
    ) {
        return String(
            customCareerLocation?.value || "India"
        ).trim() || "India";
    }

    return careerLocation?.value || "India";
}


async function loadCareerPathway(resultsData) {

    if (!careerPathway) {
        return;
    }

    const loadingBox = document.getElementById("careerPathwayLoading");
    const pathwayError = document.getElementById("careerPathwayError");
    const content = document.getElementById("careerPathwayContent");

    careerPathway.classList.remove("hidden");
    loadingBox?.classList.remove("hidden");
    pathwayError?.classList.add("hidden");
    content.innerHTML = "";

    try {
        const response = await fetch("/career-pathway", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                results: resultsData,
                location: selectedCareerLocation()
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Career pathway request failed.");
        }

        renderCareerPathway(data);
    } catch (err) {
        pathwayError.textContent = err.message;
        pathwayError.classList.remove("hidden");
    } finally {
        loadingBox?.classList.add("hidden");
    }
}


function renderCareerPathway(data) {

    const content = document.getElementById("careerPathwayContent");
    const skills = data.skills || [];
    const liveJobs = data.live_jobs || {};

    if (!skills.length) {
        content.innerHTML = `
            <div class="career-pathway-empty">
                <h3>No missing or partial technical skills were identified.</h3>
                <p>Live job searches remain available for the selected location.</p>
            </div>
        `;
    } else {
        content.innerHTML = `
            <div class="pathway-stage-label">SKILL GAP</div>
            <div class="pathway-skill-grid">
                ${skills.map(renderPathwaySkill).join("")}
            </div>
        `;
    }

    content.insertAdjacentHTML("beforeend", renderLiveJobs(liveJobs));
}


function renderPathwaySkill(skill) {

    const certifications = skill.certifications || [];
    const roles = skill.roles || [];

    return `
        <article class="pathway-skill-card">
            <div class="pathway-card-heading">
                <div>
                    <span class="pathway-kicker">SKILL GAP</span>
                    <h3>${escapeHtml(formatRequirement(skill.name))}</h3>
                </div>
                <span class="pathway-status">${escapeHtml(skill.status || "MISSING")}</span>
            </div>
            <p>${escapeHtml(skill.explanation || "This skill is not fully evidenced in the resume.")}</p>

            <div class="pathway-subsection">
                <span class="pathway-kicker">CERTIFICATION / COURSE</span>
                ${certifications.length
                    ? certifications.map(cert => `
                        <div class="pathway-certification-card">
                            <strong>${escapeHtml(cert.name)}</strong>
                            <span>${escapeHtml(cert.provider)} · ${escapeHtml(cert.type)}</span>
                            <a class="pathway-button" href="${escapeHtml(cert.url)}" target="_blank" rel="noopener noreferrer">
                                VIEW CERTIFICATION
                            </a>
                        </div>
                    `).join("")
                    : `<p class="pathway-muted">No curated provider option is configured for this skill yet.</p>`}
            </div>

            <div class="pathway-subsection">
                <span class="pathway-kicker">FUTURE SCOPE</span>
                <h4>Possible career roles</h4>
                <p class="pathway-muted">These roles commonly use this skill.</p>
                <div class="pathway-role-list">
                    ${roles.map(role => `<span>${escapeHtml(role)}</span>`).join("")}
                </div>
            </div>
        </article>
    `;
}


function renderLiveJobs(liveJobs) {

    const jobs = liveJobs.jobs || [];
    const links = liveJobs.search_links || [];
    const jobContent = liveJobs.mode === "api"
        ? (jobs.length
            ? jobs.map(job => `
                <article class="live-job-card">
                    <div>
                        <h4>${escapeHtml(job.title || "Job listing")}</h4>
                        <p>${escapeHtml(job.company || "Company not provided")}</p>
                        <span>${escapeHtml(job.location || liveJobs.location || "Location not provided")}</span>
                    </div>
                    <a class="pathway-button" href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer">VIEW JOB</a>
                </article>
            `).join("")
            : `<p class="pathway-muted">No current API results were returned for this query and location.</p>`)
        : links.map(link => `
            <article class="live-job-card search-link-card">
                <div>
                    <h4>${escapeHtml(link.platform)}</h4>
                    <p>Open a current search for ${escapeHtml(liveJobs.query)} in ${escapeHtml(liveJobs.location)}.</p>
                </div>
                <a class="pathway-button" href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer">SEARCH LIVE JOBS</a>
            </article>
        `).join("");

    return `
        <div class="pathway-stage-label live-jobs-label">LIVE JOBS</div>
        <div class="pathway-live-jobs">
            <div class="live-jobs-header">
                <div>
                    <h3>${escapeHtml(liveJobs.label || "LIVE JOB SEARCH")}</h3>
                    <p>${escapeHtml(liveJobs.query || "Related roles")} · ${escapeHtml(liveJobs.location || "India")}</p>
                </div>
                <span class="live-jobs-mode">${liveJobs.mode === "api" ? "API RESULTS" : "SEARCH LINKS"}</span>
            </div>
            <div class="live-job-grid">${jobContent}</div>
        </div>
    `;
}


careerLocation?.addEventListener("change", () => {
    customCareerLocation?.classList.toggle(
        "hidden",
        careerLocation.value !== "custom"
    );
});


document.getElementById("careerPathwayRefresh")?.addEventListener("click", () => {
    if (currentCareerContext) {
        loadCareerPathway(currentCareerContext.results || []);
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
// CAREER AI CONTEXT
// ============================================================

function buildCareerContext(result) {

    return {

        resume: result.resume || "",
        job: result.job || "",

        current_score:
            Number(result.score || 0),

        results:
            result.results || [],

        explanation:
            result.explanation || {},

        development_plan:
            result.development_plan || null,

        bias_note:
            result.bias_note || ""

    };

}


// ============================================================
// RESET CAREER CHAT
// ============================================================

function resetCareerChat() {

    const messages =
        document.getElementById(
            "careerChatMessages"
        );


    if (!messages) {
        return;
    }


    messages.innerHTML = `

        <div class="career-message bot">

            <div class="message-avatar">
                ✦
            </div>


            <div class="message-content">

                <div class="message-name">
                    Career AI
                </div>


                <div class="message-text">

                    Hi! I've analyzed your current
                    resume-to-job fit. Ask me anything
                    about your skills, gaps or
                    development plan.

                </div>

            </div>

        </div>

    `;


    const input =
        document.getElementById(
            "careerChatInput"
        );


    if (input) {

        input.value = "";

    }

}


// ============================================================
// ADD CAREER CHAT MESSAGE
// ============================================================

function addCareerMessage(
    role,
    message
) {

    const messages =
        document.getElementById(
            "careerChatMessages"
        );


    if (!messages) {
        return;
    }


    const wrapper =
        document.createElement("div");


    wrapper.className =
        `career-message ${role}`;


    const avatar =
        document.createElement("div");


    avatar.className =
        "message-avatar";


    avatar.textContent =
        role === "user"
            ? "YOU"
            : "✦";


    const content =
        document.createElement("div");


    content.className =
        "message-content";


    const name =
        document.createElement("div");


    name.className =
        "message-name";


    name.textContent =
        role === "user"
            ? "You"
            : "Career AI";


    const text =
        document.createElement("div");


    text.className =
        "message-text";


    // textContent prevents AI/user content
    // from injecting HTML into the page.
    text.textContent =
        message;


    content.appendChild(name);
    content.appendChild(text);

    wrapper.appendChild(avatar);
    wrapper.appendChild(content);

    messages.appendChild(wrapper);


    messages.scrollTop =
        messages.scrollHeight;

}


// ============================================================
// SEND CAREER QUESTION
// ============================================================

async function sendCareerQuestion(question) {

    const cleanQuestion =
        String(question || "").trim();


    if (!cleanQuestion) {
        return;
    }


    if (!currentCareerContext) {

        addCareerMessage(
            "bot",
            "Please analyze a resume and job description first."
        );

        return;

    }


    const input =
        document.getElementById(
            "careerChatInput"
        );


    const sendButton =
        document.getElementById(
            "careerChatSend"
        );


    const loadingBox =
        document.getElementById(
            "careerChatLoading"
        );


    // --------------------------------------------------------
    // Add user message
    // --------------------------------------------------------

    addCareerMessage(
        "user",
        cleanQuestion
    );


    careerChatHistory.push({

        role: "user",

        content:
            cleanQuestion

    });


    // Keep only recent conversation
    careerChatHistory =
        careerChatHistory.slice(-6);


    // --------------------------------------------------------
    // UI loading state
    // --------------------------------------------------------

    if (input) {

        input.disabled = true;

    }


    if (sendButton) {

        sendButton.disabled = true;

    }


    if (loadingBox) {

        loadingBox.classList.remove(
            "hidden"
        );

    }


    try {

        // ----------------------------------------------------
        // Send to Flask backend
        // ----------------------------------------------------

        const response =
            await fetch(
                "/career-chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        question:
                            cleanQuestion,

                        context:
                            currentCareerContext,

                        history:
                            careerChatHistory.slice(-6)

                    })

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Career AI request failed."
            );

        }


        const answer =
            data.answer ||
            "I could not generate an answer for this question.";


        // ----------------------------------------------------
        // Add AI response
        // ----------------------------------------------------

        addCareerMessage(
            "bot",
            answer
        );


        careerChatHistory.push({

            role: "assistant",

            content:
                answer

        });


        careerChatHistory =
            careerChatHistory.slice(-6);


    } catch (err) {

        addCareerMessage(
            "bot",
            `Sorry, I couldn't answer that right now. ${err.message}`
        );

    } finally {

        // ----------------------------------------------------
        // Restore UI
        // ----------------------------------------------------

        if (input) {

            input.disabled = false;

        }


        if (sendButton) {

            sendButton.disabled = false;

        }


        if (loadingBox) {

            loadingBox.classList.add(
                "hidden"
            );

        }


        if (input) {

            input.focus();

        }

    }

}


// ============================================================
// CAREER AI SEND BUTTON
// ============================================================

const careerSendButton =
    document.getElementById(
        "careerChatSend"
    );


if (careerSendButton) {

    careerSendButton.addEventListener(
        "click",
        () => {

            const input =
                document.getElementById(
                    "careerChatInput"
                );


            if (!input) {
                return;
            }


            sendCareerQuestion(
                input.value
            );


            input.value = "";

        }
    );

}


// ============================================================
// CAREER AI ENTER KEY
// ============================================================

const careerInput =
    document.getElementById(
        "careerChatInput"
    );


if (careerInput) {

    careerInput.addEventListener(
        "keydown",
        (e) => {

            if (
                e.key === "Enter" &&
                !e.shiftKey
            ) {

                e.preventDefault();


                if (
                    careerSendButton &&
                    !careerSendButton.disabled
                ) {

                    careerSendButton.click();

                }

            }

        }
    );

}


// ============================================================
// SUGGESTED QUESTIONS
// ============================================================

document
    .querySelectorAll(
        ".suggestion-btn"
    )
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                const question =
                    button.dataset.question;


                const input =
                    document.getElementById(
                        "careerChatInput"
                    );


                if (input) {

                    input.value =
                        question;

                }


                sendCareerQuestion(
                    question
                );


                if (input) {

                    input.value = "";

                }

            }
        );

    });


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

        "aws s3":
            "AWS S3",

        "pyspark":
            "PySpark",

        "airflow":
            "Apache Airflow",

        "etl":
            "ETL / Data Pipelines",

        "bachelor's degree":
            "Bachelor's Degree",

        "sql":
            "SQL",

        "aws":
            "AWS",

        "git":
            "Git"

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
        .replace(
            /\b\w/g,
            char =>
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