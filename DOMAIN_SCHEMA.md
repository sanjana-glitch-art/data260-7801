# Clinical Trial Listing Domain Schema

## Entity

Clinical Trial Listing

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `trialTitle` | Text | Yes | Official or descriptive title of the clinical trial |
| `sponsorName` | Text | Yes | Organization or institution sponsoring the trial |
| `submitterEmail` | Email | Yes | Email address of the person submitting the listing |
| `trialDescription` | Text area | Yes | Detailed description of the trial, including its purpose |
| `trialPhase` | Category | Yes | Current phase or classification of the clinical trial |
| `termsAccepted` | Boolean | Yes | Whether the submitter accepts the terms and conditions |
| `submissionDate` | Date and time | Generated | Date and time when the form was successfully submitted |

## Category Values

The `trialPhase` field supports these four values:

1. Phase I
2. Phase II
3. Phase III
4. Phase IV

## Primary Field

`trialTitle`

## Secondary Field

`sponsorName`

## Content Field

`trialDescription`