# frigate-face-unlock.yaml

2 helpers needed: `input_text.frigate_face_id` and `input_text.frigate_zone_id`

  How it works now:

  | Scenario                          | Triggers                                                       |
  |-----------------------------------|----------------------------------------------------------------|
  | Face first → then enters zone     | Face stores ID. Zone entry stores ID. Match → unlock           |
  | Zone entry → then face            | Zone entry stores ID. Face stores ID. Match → unlock           |
  | Already in zone → face recognized | Zone ID already set from entry. Face stores ID. Match → unlock |

  Zone event triggers once (entry only), face event handles the "recognized while already in zone" case. No duplicate 
  unlocks.