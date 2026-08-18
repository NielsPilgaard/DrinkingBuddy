// Requests a magic link via the test-mode echo endpoint and stashes the
// debug token on `output`, for signup-and-reach-match-screen.yaml. Uses
// runScript + http.post (rather than a top-level `http:` command) so the
// response body can be parsed and assigned in one script step.
const response = http.post(API_BASE_URL + '/auth/request-link', {
  headers: {
    'Content-Type': 'application/json',
    'X-Test-Mode': '1',
  },
  body: JSON.stringify({
    email: 'maestro-' + USER_LABEL + '-' + output.timestamp + '@e2e.drinkingbuddy.local',
    birthdate: '2000-01-01',
  }),
});

output.debugToken = json(response.body).debug_token;
