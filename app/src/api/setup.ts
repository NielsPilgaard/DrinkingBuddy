import { getStoredSessionToken } from '../auth/storage';
import { client } from './generated/client.gen';

export function configureApiClient(baseUrl: string) {
  client.setConfig({ baseUrl });

  client.interceptors.request.use(async (request) => {
    const token = await getStoredSessionToken();
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`);
    }
    return request;
  });
}
