# G.R.A.C.E. UI refactor

## Goal

Make the dashboard feel like a private, account-based application: a visitor sees only authentication, then a signed-in user sees a clear home screen containing only the features their role can use.

## Recommended experience

### 1. Use an authentication-first entry screen

- On startup, check `/api/auth/me` before rendering dashboard content.
- While that check runs, show a neutral loading screen so private information does not flash briefly.
- If there is no valid session, show a dedicated welcome screen with **Sign in** and **Create account** tabs. Do not show the dashboard, status, navigation, camera information, memories, or other app data behind it.
- After authentication, return the user to their originally requested page when permitted; otherwise open their home page.
- Keep setup distinct from ordinary signup. If no administrator exists yet, offer a one-time **Set up G.R.A.C.E.** flow. After setup, decide deliberately whether anyone may create an account or whether an administrator must invite/approve them.

### 2. Make sessions durable and intentionally long-lived

The current cookie lasts 24 hours, but the server stores its token only in process memory, so every restart signs everyone out. A longer cookie alone will not solve that.

- Store only a hash of each session token in durable local storage, with the user ID, creation time, last-used time, expiration time, and optional device label.
- Use a 30-day sliding session for normal local use, with a **Keep me signed in on this device** option. Without it, use a browser-session cookie.
- Refresh the expiration after valid activity, but enforce a maximum lifetime (for example, 90 days) before requiring the password again.
- Keep cookies `HttpOnly`, `SameSite=Lax` or stricter, and `Secure` whenever HTTPS is used.
- Revoke the current session on logout and provide a **Signed-in devices** page for revoking other sessions. Password changes should revoke all existing sessions.
- Require recent password confirmation or a second factor for sensitive actions even during a long session.
- Periodically remove expired sessions. Never store raw bearer tokens in the data file or browser storage.

### 3. Build one role-aware app shell

After login, use a consistent header and navigation instead of separate page-specific home buttons:

- Header: G.R.A.C.E. identity, connection/server state, notifications, and account menu.
- Primary navigation: Home, Chat, Images, Music, and other capabilities actually available to that user.
- Account menu: profile, privacy, signed-in devices, and logout.
- Admin-only area: users, permissions, integrations, system settings, and audit activity.
- Keep GRACE's personality, humor, formality, and response-style controls in the admin-only area. Ordinary users experience the configured personality but cannot change it.
- Hide inaccessible destinations from normal navigation, but also enforce every permission on the API. A hidden button is not authorization.
- Give permission failures a useful next step, such as **Ask an administrator for access**, rather than exposing a broken control.

### 4. Turn the home page into a useful overview

- Lead with a prominent **Ask G.R.A.C.E.** action and a few recent or pinned tasks.
- Show compact cards for service health, camera/watch state, music, weather, and recent activity according to the user's permissions.
- Separate live state from actions visually so users can tell what is informational and what changes the home.
- Show unavailable integrations as clearly disabled with a short reason and setup link; do not make them look active.
- Let users pin or reorder frequently used features later, after the basic information hierarchy is validated.

### 5. Improve interaction quality throughout

- Use descriptive labels instead of icon-only controls and keep one vocabulary: **Sign in**, **Create account**, and **Log out**.
- Keep GRACE composed, capable, concise, and occasionally dry or teasing during low-stakes interactions. Humor must never obscure instructions, errors, security events, confirmations, or other important information.
- Do not force every result into a factual status followed by a joke. Choose the line that best fits the moment: usually a direct confirmation, sometimes a characterful confirmation, and only rarely both when the extra detail is genuinely useful.
- Avoid repetitive templates and catchphrases. For example, a successful action might say either **Kitchen lights turned off** or **The kitchen has officially concluded business for the evening.**
- Provide loading, success, empty, offline, permission-denied, and recoverable error states for every data panel.
- Preserve draft input when a session expires, then restore it after sign-in.
- Confirm destructive or physically consequential commands and show their result in an activity log.
- Make forms one-column on narrow screens, keep touch targets at least 44 px, maintain visible keyboard focus, and announce asynchronous status changes to assistive technology.
- Avoid relying on color alone for connection, recording, warning, or success states.

## Suggested screen flow

```text
Open app
  -> checking session
     -> signed out: Sign in / Create account
     -> signed in: role-aware Home
        -> permitted feature
        -> account and session controls
        -> admin area (admin only)
```

## Delivery order and acceptance checks

### Phase 1: Privacy and navigation foundation

- Add the blocking session check and signed-out authentication screen.
- Protect all private API routes, not only chat and settings.
- Add the role-aware app shell and reliable post-login redirect.
- Verify that no private content or requests appear before authentication, direct links behave correctly, and logout returns to the sign-in screen.

### Phase 2: Durable sessions

- Persist hashed, expiring sessions and add the keep-signed-in choice.
- Add session rotation, cleanup, logout revocation, and signed-in device management.
- Verify login survives a server restart, expired/revoked tokens fail, cookie flags are correct, and password changes invalidate sessions.

### Phase 3: Dashboard usability

- Reorganize the home page, standardize component states and wording, and improve responsive/accessibility behavior.
- Test all affected routes with keyboard navigation and at desktop and mobile widths. Confirm text wraps, controls remain reachable, and focus moves sensibly after navigation and errors.

## Decisions to make before implementation

- Whether signup stays open, requires an admin invitation, or becomes approval-based.
- The exact permissions for ordinary users versus administrators.
- The default humor level and the admin-only controls for personality, formality, response length, and proactive comments.
- Whether 30-day persistent sessions are appropriate for every device or only explicitly trusted devices.
- Which status information, if any, is safe to expose before login (the safest default is none beyond app availability).
