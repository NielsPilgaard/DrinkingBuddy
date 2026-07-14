import { defineConfig } from '@hey-api/openapi-ts';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export default defineConfig({
  input: `${API_URL}/openapi.json`,
  output: 'src/api/generated',
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/typescript',
    '@hey-api/sdk',
    '@tanstack/react-query',
  ],
});
