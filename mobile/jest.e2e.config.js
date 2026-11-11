// End-to-end: the app's real API client against a running backend.
//   E2E_API_URL=http://localhost:8000 npm run test:e2e
module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/e2e/**/*.e2e.test.ts'],
  transform: { '^.+\\.tsx?$': ['babel-jest', { presets: ['@react-native/babel-preset'] }] },
  testTimeout: 30000,
};
