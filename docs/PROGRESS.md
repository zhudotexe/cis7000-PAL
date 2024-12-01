# Progress Report

## Accomplishments

### Updated Landing Page Navigation
- Disabled the option to start a new session, aligning with the intended design.
- Redesigned the interface to guide clinicians toward selecting one of the three available interactive patient sessions.
- Improved clarity by providing concise instructions for navigating existing sessions.
![Updated Landing Page Navigation](docs/_static/ux_improvements/updated_navigation.png)
### Added Instructions for Interactive Sessions
- Implemented a popup that provides instructions when a user clicks on an interactive session.
- **Design Decision:** To avoid annoying users by showing the popup repeatedly, used `sessionStorage` to display the popup only on the first interaction per browser tab session.
- Ensured that users who are already familiar with the content can proceed seamlessly without redundant interruptions.

### Matched Emoji to Patient Profiles
- Updated patient profiles to feature consistent emojis in both the profile description and text conversations.
- Ensured the emoji does not jump across different assistant states (e.g., `AssistantStream.vue`, `AssistantThinking.vue`, and `AssistantMessage.vue`) by passing the image across all states.
- Added a fallback emoji for scenarios where the user initiates a new session without a saved image, ensuring a consistent user experience.

### Fixed a Bug in `Interactive.vue`
- Found and resolved an issue where the default fallback image was not displaying due to an incorrect path.
- Updated the path to ensure the fallback image loads correctly.

---

## Challenges and Approaches

### Managing Popups for Interactive Sessions
- **Challenge:** Avoid overwhelming users with repetitive instructions while maintaining accessibility for new users.
- **Solution:** Utilized `sessionStorage` to track popup visibility, ensuring it appears only once per browser tab session.

### Ensuring Emoji Consistency Across Assistant States
- **Challenge:** The assistant transitions through multiple states (`AssistantStream.vue`, `AssistantThinking.vue`, `AssistantMessage.vue`), making it difficult to maintain a consistent emoji display.
- **Solution:** Passed the emoji as a prop across all states, streamlining its display throughout the interaction process.

### Handling Missing Images
- **Challenge:** Some new sessions lacked an assigned emoji, leading to inconsistency in the interface.
- **Solution:** Added a default fallback image to ensure a cohesive experience even when no custom image is available.

---

## Unaddressed Features/Bugs
- There were no significant unaddressed features or bugs as all tasks were completed. However, further user feedback may reveal opportunities for improvement in popup timing or emoji customization.

