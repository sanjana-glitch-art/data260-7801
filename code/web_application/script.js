
"use strict";

// Get the form from the HTML page.
const clinicalTrialForm = document.getElementById("clinicalTrialForm");

// Arrow function that validates the description and checkbox.
const validateForm = () => {
    const trialDescription = document
        .getElementById("trialDescription")
        .value
        .trim();

    const termsAccepted =
        document.getElementById("termsAccepted").checked;

    // The description must contain more than 25 characters.
    if (trialDescription.length <= 25) {
        alert("The trial description must contain more than 25 characters.");
        return false;
    }

    // The terms and conditions checkbox must be selected.
    if (!termsAccepted) {
        alert("You must agree to the terms and conditions.");
        return false;
    }

    return true;
};

// Closure that remembers the number of successful submissions.
const createSubmissionCounter = () => {
    let submissionCount = 0;

    return () => {
        submissionCount += 1;
        return submissionCount;
    };
};

const countSuccessfulSubmission = createSubmissionCounter();

// Handle the form submission.
clinicalTrialForm.addEventListener("submit", (event) => {
    // Prevent the page from reloading.
    event.preventDefault();

    // Stop if JavaScript validation fails.
    if (!validateForm()) {
        return;
    }

    // Collect the form values in an object.
    const formData = {
        trialTitle: document.getElementById("trialTitle").value.trim(),
        sponsorName: document.getElementById("sponsorName").value.trim(),
        submitterEmail: document
            .getElementById("submitterEmail")
            .value
            .trim(),
        trialDescription: document
            .getElementById("trialDescription")
            .value
            .trim(),
        trialPhase: document.getElementById("trialPhase").value,
        termsAccepted: document.getElementById("termsAccepted").checked
    };

    // Convert the form object into a JSON string.
    const jsonString = JSON.stringify(formData);

    console.log("Form data as a JSON string:");
    console.log(jsonString);

    // Convert the JSON string back into a JavaScript object.
    const parsedObject = JSON.parse(jsonString);

    // Use object destructuring to extract the primary field and email.
    const { trialTitle, submitterEmail } = parsedObject;

    console.log("Primary field - Trial title:", trialTitle);
    console.log("Submitter email:", submitterEmail);

    // Use the spread operator to add the current date and time.
    const updatedParsedObject = {
        ...parsedObject,
        submissionDate: new Date().toISOString()
    };

    console.log("Updated parsed object:");
    console.log(updatedParsedObject);

    // Increase the closure counter only after successful validation.
    const submissionCount = countSuccessfulSubmission();

    console.log("Successful submission count:", submissionCount);

    alert("Clinical trial listing submitted successfully!");

    // Clear the form after a successful submission.
    clinicalTrialForm.reset();

    // Return focus to the primary field.
    document.getElementById("trialTitle").focus();
});