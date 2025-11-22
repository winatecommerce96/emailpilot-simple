Calendar App Integration Guide: "Push Back" Workflow
To enable the Human-in-the-Loop workflow where users can edit the calendar before briefs are generated, the Calendar App needs to integrate with the following EmailPilot Simple APIs.

Overview
Edit: User edits the generated calendar in the Calendar App UI.
Save: App pushes the modified calendar back to EmailPilot.
Approve: App signals that the review is complete.
Resume: App triggers the next stage (Brief Generation).
API Endpoints
1. Save Modified Calendar
Endpoint: PUT /api/reviews/{workflow_id}/calendar Purpose: Update the stored calendar data with user edits.

Request Body:

{
  "detailed_calendar": {
    // The full, modified calendar JSON object
    "campaigns": [ ... ]
  },
  "simplified_calendar": {
    // Optional: The modified simplified view if available
    // If omitted, it can be re-generated or ignored depending on backend logic
  }
}
2. Approve Review
Endpoint: POST /api/reviews/{workflow_id}/approve Purpose: Mark the workflow as approved by the user.

Request Body:

{
  "reviewer_id": "user_123" // Optional identifier
}
3. Resume Workflow
Endpoint: POST /api/workflows/resume/{workflow_id} Purpose: Trigger Stage 3 (Brief Generation) using the approved (and potentially modified) calendar data.

Request Body:

{} // Empty body
UI Implementation Checklist
 "Save Changes" Button:

Should collect the current state of the calendar from the UI.
Should call PUT /api/reviews/{workflow_id}/calendar.
Show a "Saved" confirmation.
 "Approve & Generate Briefs" Button:

Should first ensure all changes are saved (optionally auto-save).
Call POST /api/reviews/{workflow_id}/approve.
Upon success, call POST /api/workflows/resume/{workflow_id}.
Show a "Generating Briefs..." loading state.
Poll for completion or wait for websocket/webhook (if applicable).
Data Structure Notes
The detailed_calendar object must maintain the original structure (campaigns list, fields like 

date
, theme, 

type
, 

goal
).
Critical: The 

type
 field must be one of the valid campaign types:
promotional, educational, seasonal, product_launch, product_spotlight, engagement, win_back, nurture, lifecycle.