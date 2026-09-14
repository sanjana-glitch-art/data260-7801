"use strict";

const API_URL = "/api/trials";

const loadingState = document.getElementById("loadingState");
const emptyState = document.getElementById("emptyState");
const errorState = document.getElementById("errorState");
const tableContainer = document.getElementById("tableContainer");
const trialTableBody = document.getElementById("trialTableBody");
const recordCount = document.getElementById("recordCount");
const searchForm = document.getElementById("searchForm");
const searchInput = document.getElementById("searchInput");
const clearSearchButton = document.getElementById(
    "clearSearchButton"
);
const createTrialForm = document.getElementById(
    "createTrialForm"
);
const deleteHighestForm = document.getElementById(
    "deleteHighestForm"
);


const showOnlyState = (stateName) => {
    loadingState.hidden = stateName !== "loading";
    emptyState.hidden = stateName !== "empty";
    errorState.hidden = stateName !== "error";
    tableContainer.hidden = stateName !== "table";
};


const addCell = (row, label, value) => {
    const cell = document.createElement("td");
    cell.dataset.label = label;
    cell.textContent = value;
    row.appendChild(cell);
};


const displayTrials = (trials) => {
    trialTableBody.replaceChildren();

    recordCount.textContent = (
        `${trials.length} ${
            trials.length === 1 ? "record" : "records"
        }`
    );

    if (trials.length === 0) {
        showOnlyState("empty");
        return;
    }

    for (const trial of trials) {
        const row = document.createElement("tr");

        addCell(row, "ID", String(trial.id));
        addCell(row, "Trial title", trial.trial_title);
        addCell(row, "Sponsor", trial.sponsor_name);
        addCell(row, "Phase", trial.trial_phase);

        trialTableBody.appendChild(row);
    }

    showOnlyState("table");
};


const loadTrials = async (search = "") => {
    showOnlyState("loading");

    const query = new URLSearchParams();

    if (search.trim()) {
        query.set("search", search.trim());
    }

    const requestUrl = query.size
        ? `${API_URL}?${query.toString()}`
        : API_URL;

    try {
        const response = await fetch(requestUrl, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(
                `Request failed with status ${response.status}`
            );
        }

        const trials = await response.json();
        displayTrials(trials);
    } catch (error) {
        console.error("Unable to load trials:", error);
        recordCount.textContent = "Unavailable";
        showOnlyState("error");
    }
};


const validateCreateForm = () => {
    const description = document
        .getElementById("trialDescription")
        .value
        .trim();

    const termsAccepted = document
        .getElementById("termsAccepted")
        .checked;

    if (description.length <= 25) {
        alert(
            "The trial description must contain more than " +
            "25 characters."
        );

        return false;
    }

    if (!termsAccepted) {
        alert(
            "You must agree to the terms and conditions."
        );

        return false;
    }

    return true;
};


searchForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const search = searchInput.value.trim();
    const url = new URL(window.location.href);

    if (search) {
        url.searchParams.set("search", search);
    } else {
        url.searchParams.delete("search");
    }

    window.history.replaceState({}, "", url);
    loadTrials(search);
});


clearSearchButton.addEventListener("click", () => {
    searchInput.value = "";

    const url = new URL(window.location.href);
    url.searchParams.delete("search");
    window.history.replaceState({}, "", url);

    loadTrials();
    searchInput.focus();
});


createTrialForm.addEventListener("submit", (event) => {
    if (!validateCreateForm()) {
        event.preventDefault();
    }
});


deleteHighestForm.addEventListener("submit", (event) => {
    const confirmed = window.confirm(
        "Delete the clinical-trial record with the highest ID?"
    );

    if (!confirmed) {
        event.preventDefault();
    }
});


document.addEventListener("DOMContentLoaded", () => {
    const search = new URLSearchParams(
        window.location.search
    ).get("search") || "";

    searchInput.value = search;
    loadTrials(search);
});