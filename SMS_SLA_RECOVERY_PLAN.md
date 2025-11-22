# SMS SLA Recovery Plan - Update

## Status
- **v4 Run**: Failed (Server restart killed it).
- **Targeted Test 1 (Stage 1)**: Failed. Generated 0 SMS campaigns, 4 SMS variants.
- **Root Cause**: LLM ignored "Negative Constraint" and preferred `sms_variant` inside email campaigns.

## Actions Taken
1. **Schema Change**: Removed `sms_variant` from the Email Campaign schema in `prompts/planning_v5_1_0.yaml`. This physically prevents the LLM from using the "variant" approach for emails.
2. **Prompt Engineering**: Moved Few-Shot Examples from System Prompt to User Prompt (Recency Bias) and placed them immediately after the SLA requirement.
3. **Example Update**: Updated examples to explicitly show "NO sms_variant here!" for email campaigns.

## Next Steps
1. **Verify Stage 1**: Running `debug_stage_1.py` with new prompt. Expecting 3 SMS campaigns.
2. **Verify Stage 2**: If Stage 1 passes, run `debug_stage_2.py` to ensure Structuring preserves the SMS campaigns.
3. **Final Full Run**: Once both stages pass in isolation, run the full workflow to confirm end-to-end success.
